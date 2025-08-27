"""
Requirements Synthesizer Lambda - Processes documents to extract user stories and requirements.
Creates prioritized user stories with acceptance criteria and effort estimates.
"""

import json
import os
from typing import Dict, Any, List, Optional
import boto3
from datetime import datetime

# Import shared components - avoiding pydantic to prevent dependency issues
import sys
sys.path.append('/opt/python')

# Avoid importing pydantic models to prevent dependency issues
# from shared.models.pipeline_models import (
#     DocumentMetadata, UserStory, StoryStatus, PipelineContext, LambdaResponse
# )
# from shared.utils.logger import setup_logger, log_lambda_start, log_lambda_end, log_error, get_logger

# Configure logging directly to avoid pydantic dependencies
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Import Anthropic service for AI-powered requirements analysis
try:
    from shared.services.anthropic_service import AnthropicService
    AnthropicService_available = True
    logger.info("AnthropicService imported successfully")
except ImportError as e:
    AnthropicService = None
    AnthropicService_available = False
    logger.error(f"Failed to import AnthropicService: {e}")
    
# Alternative: Import anthropic directly if service not available
anthropic = None
anthropic_available = False

if not AnthropicService_available:
    try:
        import anthropic
        anthropic_available = True
        logger.info("Direct anthropic client imported as fallback")
    except ImportError as e:
        anthropic = None
        anthropic_available = False
        logger.error(f"Failed to import direct anthropic client: {e}")

# Final status check
logger.info(f"Final import status - AnthropicService: {AnthropicService_available}, anthropic: {anthropic_available}")
if not AnthropicService_available and not anthropic_available:
    logger.error("CRITICAL: No Anthropic client available - AI analysis will fail")


# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
PROCESSED_BUCKET = os.environ.get('PROCESSED_BUCKET_NAME')
STORIES_TABLE = os.environ.get('USER_STORIES_TABLE', 'ai-pipeline-v2-user-stories')


class RequirementsSynthesizer:
    """Synthesizes requirements from multiple documents into user stories."""
    
    def __init__(self):
        """Initialize the requirements synthesizer."""
        self.logger = logger
        self.stories_table = dynamodb.Table(STORIES_TABLE)
        
        # Initialize Anthropic service or direct client
        self.logger.info(f"Initializing synthesizer - AnthropicService available: {AnthropicService_available}")
        self.logger.info(f"Direct anthropic available: {anthropic_available}")
        
        if AnthropicService_available and AnthropicService:
            try:
                self.anthropic_service = AnthropicService()
                self.use_service = True
                self.logger.info("AnthropicService initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize AnthropicService: {e}")
                self.anthropic_service = None
                self.use_service = False
        elif anthropic_available and anthropic:
            # Use direct anthropic client - get API key from Secrets Manager
            api_key = self._get_anthropic_api_key()
            self.logger.info(f"ANTHROPIC_API_KEY retrieved: {api_key is not None}")
            if not api_key:
                self.logger.error("Failed to retrieve ANTHROPIC_API_KEY from Secrets Manager")
                self.anthropic_client = None
                self.use_service = False
            else:
                try:
                    self.anthropic_client = anthropic.Anthropic(api_key=api_key)
                    self.use_service = False
                    self.logger.info("Direct Anthropic client initialized successfully")
                except Exception as e:
                    self.logger.error(f"Failed to initialize Anthropic client: {e}")
                    self.anthropic_client = None
                    self.use_service = False
        else:
            # Fallback: Use direct HTTP requests to Anthropic API if both imports failed
            api_key = self._get_anthropic_api_key()
            self.logger.info(f"Using direct HTTP fallback - API key available: {api_key is not None}")
            if api_key:
                self.anthropic_api_key = api_key
                self.anthropic_client = None
                self.anthropic_service = None
                self.use_service = False
                self.use_http_fallback = True
                self.logger.info("Direct HTTP fallback initialized successfully")
            else:
                self.anthropic_service = None
                self.anthropic_client = None
                self.use_service = False
                self.use_http_fallback = False
                self.logger.error("HTTP fallback failed - no API key available")
                
        # Set default values for any uninitialized attributes
        if not hasattr(self, 'use_http_fallback'):
            self.use_http_fallback = False
    
    def _get_anthropic_api_key(self) -> Optional[str]:
        """Retrieve Anthropic API key from AWS Secrets Manager."""
        try:
            from botocore.exceptions import ClientError
            
            secret_arn = os.environ.get('ANTHROPIC_API_KEY_SECRET_ARN')
            if not secret_arn:
                self.logger.error("ANTHROPIC_API_KEY_SECRET_ARN environment variable not set")
                return None
            
            secrets_client = boto3.client('secretsmanager')
            response = secrets_client.get_secret_value(SecretId=secret_arn)
            
            secret_value = response['SecretString']
            if secret_value.startswith('{'):
                # JSON format
                import json
                secret_data = json.loads(secret_value)
                # Try different key names that might be used
                return (secret_data.get('ANTHROPIC_API_KEY') or 
                        secret_data.get('apiKey') or
                        secret_data.get('api_key'))
            else:
                # Plain text format
                return secret_value
                
        except ClientError as e:
            self.logger.error(f"Failed to retrieve Anthropic API key from Secrets Manager: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving Anthropic API key: {e}")
            return None
    
    def _make_anthropic_http_request(self, prompt: str) -> str:
        """Make direct HTTP request to Anthropic API as fallback."""
        try:
            import requests
            import json
            
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.anthropic_api_key,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 4000,
                "temperature": 0.3,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            self.logger.info("Making direct HTTP request to Anthropic API")
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result["content"][0]["text"]
            
        except Exception as e:
            self.logger.error(f"HTTP request to Anthropic API failed: {e}")
            raise RuntimeError(f"Direct HTTP request to Anthropic failed: {e}")
    
    def synthesize_requirements(
        self, 
        documents: List[Dict[str, Any]], 
        execution_id: str
    ) -> List[Dict[str, Any]]:
        """
        Synthesize requirements from processed documents into user stories.
        
        Args:
            documents: List of processed document metadata
            execution_id: Unique execution identifier
            
        Returns:
            List of extracted user stories
        """
        # Read all document contents
        document_contents = []
        for doc in documents:
            content = self._read_document_content(doc)
            document_contents.append({
                'type': doc['document_type'],
                'content': content,
                'source': doc['source_path']
            })
        
        # Use AI-powered analysis to create comprehensive user stories
        has_anthropic_access = (
            (self.use_service and self.anthropic_service) or
            (not self.use_service and self.anthropic_client) or
            (hasattr(self, 'use_http_fallback') and self.use_http_fallback and hasattr(self, 'anthropic_api_key'))
        )
        
        if not has_anthropic_access:
            raise RuntimeError("Anthropic service not available - cannot perform AI-powered requirements analysis")
        
        user_stories = self._create_ai_powered_user_stories(document_contents, execution_id)
        
        # Store user stories
        for story in user_stories:
            self._store_user_story(story)
        
        self.logger.info(f"Synthesized {len(user_stories)} user stories from {len(documents)} documents")
        return user_stories
    
    def _read_document_content(self, doc: Dict[str, Any]) -> str:
        """Read processed document content from S3 or direct content."""
        try:
            # First try to get content directly from the document (Step Functions format)
            if 'content' in doc:
                return doc['content']
            elif 'processed_content' in doc:
                return doc['processed_content']
            elif 'content_path' in doc:
                # New format: content stored in S3, path provided
                content_path = doc['content_path']
                if content_path.startswith('s3://'):
                    # Parse S3 path
                    path_parts = content_path.replace('s3://', '').split('/', 1)
                    bucket = path_parts[0]
                    key = path_parts[1] if len(path_parts) > 1 else ''
                    self.logger.info(f"Reading document from S3 path: {content_path}")
                    response = s3_client.get_object(Bucket=bucket, Key=key)
                    return response['Body'].read().decode('utf-8')
            
            # Fallback: try to read from S3 (original format)
            doc_id = doc.get('document_id')
            if not doc_id:
                self.logger.error("Document missing document_id field")
                return ""
                
            # Extract execution ID from document_id (everything except the last hash part)
            last_underscore = doc_id.rfind('_')
            execution_id = doc_id[:last_underscore]
            key = f"processed/{execution_id}/{doc_id}.txt"
            
            self.logger.info(f"Reading document from S3: {key}")
            response = s3_client.get_object(Bucket=PROCESSED_BUCKET, Key=key)
            return response['Body'].read().decode('utf-8')
        except Exception as e:
            doc_id = doc.get('document_id', 'unknown')
            self.logger.error(f"Failed to read document {doc_id}: {e}")
            return ""
    
    def _create_ai_powered_user_stories(self, document_contents: List[Dict[str, Any]], execution_id: str) -> List[Dict[str, Any]]:
        """
        Create comprehensive user stories using AI analysis of document contents.
        
        Args:
            document_contents: List of document contents with metadata
            execution_id: Execution identifier
            
        Returns:
            List of AI-generated user stories
        """
        user_stories = []
        
        try:
            # Combine all document content
            combined_content = ""
            for doc in document_contents:
                combined_content += f"\n--- Document ({doc['type']}): {doc['source']} ---\n"
                combined_content += doc['content']
                combined_content += "\n\n"
            
            # Create comprehensive prompt for user story extraction
            prompt = f"""
            Analyze the following requirements document(s) and extract comprehensive user stories for the application described.

            {combined_content}

            Please extract user stories that:
            1. Cover ALL major functional requirements mentioned in the document(s)
            2. Are specific to the application domain (not generic)
            3. Follow proper user story format: "As a [user type], I want [goal] so that [benefit]"
            4. Include realistic effort estimates (story points 1-13)
            5. Have specific, testable acceptance criteria
            6. Are properly prioritized (1=highest)

            For each user story, provide:
            - Title: Brief descriptive title
            - Description: Full user story in proper format
            - Acceptance Criteria: 2-4 specific, testable criteria
            - Priority: 1-10 (1=highest)
            - Estimated Effort: Story points (1, 2, 3, 5, 8, 13)
            - User Type: The specific type of user (coach, admin, director, etc.)

            Please extract 8-15 user stories to comprehensively cover the requirements.
            Return your response as a JSON array of user story objects.
            """
            
            # Get AI response
            self.logger.info("Requesting AI analysis for user story extraction")
            if self.use_service and self.anthropic_service:
                response = self.anthropic_service.generate_response(
                    prompt=prompt,
                    max_tokens=4000,
                    temperature=0.3
                )
            elif hasattr(self, 'use_http_fallback') and self.use_http_fallback:
                # Use direct HTTP requests as fallback
                response = self._make_anthropic_http_request(prompt)
            else:
                # Use direct anthropic client
                message = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    temperature=0.3,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                response = message.content[0].text
            
            # Parse the AI response
            try:
                import re
                # Try to extract JSON from the response
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    stories_data = json.loads(json_match.group(0))
                else:
                    # Fallback: try to parse the whole response as JSON
                    stories_data = json.loads(response)
                
                # Convert AI response to our user story format
                for i, story_data in enumerate(stories_data, 1):
                    story = {
                        'story_id': f"{execution_id}_story_{i:03d}",
                        'title': story_data.get('title', f'Story {i}'),
                        'description': story_data.get('description', ''),
                        'acceptance_criteria': story_data.get('acceptance_criteria', []),
                        'priority': story_data.get('priority', i),
                        'estimated_effort': story_data.get('estimated_effort', 5),
                        'dependencies': [],
                        'status': 'pending',
                        'assigned_components': [],
                        'created_at': datetime.utcnow().isoformat(),
                        'user_type': story_data.get('user_type', 'user')
                    }
                    user_stories.append(story)
                
                self.logger.info(f"AI-powered analysis generated {len(user_stories)} user stories")
                
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.error(f"Failed to parse AI response as JSON: {e}")
                self.logger.error(f"AI response: {response[:500]}...")
                raise RuntimeError(f"AI response parsing failed: {e}")
                
        except Exception as e:
            self.logger.error(f"AI-powered story generation failed: {e}")
            raise RuntimeError(f"AI-powered requirements analysis failed: {e}")
        
        return user_stories

    def _create_basic_user_stories(self, document_contents: List[Dict[str, Any]], execution_id: str) -> List[Dict[str, Any]]:
        """
        Create basic user stories from document contents.
        
        Args:
            document_contents: List of document contents with metadata
            execution_id: Execution identifier
            
        Returns:
            List of basic user stories
        """
        # For now, create simple user stories based on keywords in content
        user_stories = []
        
        # Extract some basic features from content
        all_content = " ".join([doc['content'].lower() for doc in document_contents])
        
        # Define common user story patterns
        story_templates = [
            {
                'title': 'User Authentication',
                'description': 'As a user, I want to authenticate securely so that I can access the system',
                'keywords': ['login', 'auth', 'user', 'password', 'signin'],
                'effort': 5
            },
            {
                'title': 'Task Management',
                'description': 'As a user, I want to manage tasks so that I can track my work',
                'keywords': ['task', 'todo', 'manage', 'create', 'edit'],
                'effort': 8
            },
            {
                'title': 'Dashboard View',
                'description': 'As a user, I want to see a dashboard so that I can get an overview',
                'keywords': ['dashboard', 'overview', 'view', 'display'],
                'effort': 5
            }
        ]
        
        story_count = 1
        for template in story_templates:
            # Check if any keywords appear in content
            if any(keyword in all_content for keyword in template['keywords']):
                story = {
                    'story_id': f"{execution_id}_story_{story_count:03d}",
                    'title': template['title'],
                    'description': template['description'],
                    'acceptance_criteria': [f"System implements {template['title'].lower()}"],
                    'priority': story_count,
                    'estimated_effort': template['effort'],
                    'dependencies': [],
                    'status': 'pending',
                    'assigned_components': [],
                    'created_at': datetime.utcnow().isoformat()
                }
                user_stories.append(story)
                story_count += 1
        
        # Always include at least one basic story if none match
        if not user_stories:
            user_stories.append({
                'story_id': f"{execution_id}_story_001",
                'title': 'Basic Application Setup',
                'description': 'As a developer, I want to set up the basic application structure',
                'acceptance_criteria': ['Application can be built and deployed'],
                'priority': 1,
                'estimated_effort': 3,
                'dependencies': [],
                'status': 'pending',
                'assigned_components': [],
                'created_at': datetime.utcnow().isoformat()
            })
        
        return user_stories
    
    
    def _store_user_story(self, story: Dict[str, Any]) -> None:
        """Store user story in DynamoDB."""
        try:
            self.stories_table.put_item(Item=story)
        except Exception as e:
            self.logger.error(f"Failed to store user story {story['story_id']}: {e}")
            raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for requirements synthesis.
    
    Args:
        event: Lambda event containing pipeline context
        context: Lambda context
        
    Returns:
        Synthesis results with user stories
    """
    # Generate execution ID
    execution_id = f"req_synth_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{context.aws_request_id[:8] if context else 'local'}"
    
    logger.info(f"Starting requirements synthesis with execution_id: {execution_id}")
    logger.info(f"Received event: {json.dumps(event, default=str)}")
    
    try:
        # Handle both Step Functions input and direct lambda input
        if 'documentProcessorResult' in event:
            # Step Functions format - extract from document processor result
            doc_result = event.get('documentProcessorResult', {}).get('Payload', {})
            pipeline_data = doc_result.get('data', {})
            processed_documents = pipeline_data.get('processed_documents', [])
        else:
            # Direct lambda input format
            pipeline_data = event.get('data', {}).get('pipeline_context', {})
            if not pipeline_data:
                raise ValueError("No pipeline context provided")
            processed_documents = pipeline_data.get('processed_documents', [])
        
        if not processed_documents:
            raise ValueError("No processed documents to analyze")
        
        # Get project_id from multiple possible locations
        project_id = (
            pipeline_data.get('project_id') or 
            event.get('project_id') or 
            event.get('documentProcessorResult', {}).get('Payload', {}).get('project_id') or
            'unknown'
        )
        
        # Synthesize requirements
        synthesizer = RequirementsSynthesizer()
        user_stories = synthesizer.synthesize_requirements(processed_documents, execution_id)
        
        # Create pipeline context as plain dictionary
        updated_context = {
            "execution_id": execution_id,
            "project_id": project_id,
            "stage": "requirements_synthesis",
            "processed_documents": processed_documents,
            "user_stories": user_stories,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {
                'total_stories': len(user_stories),
                'total_effort': sum(story['estimated_effort'] for story in user_stories)
            }
        }
        
        # Prepare response as plain dictionary
        response = {
            "status": "success",
            "message": f"Synthesized {len(user_stories)} user stories successfully",
            "execution_id": execution_id,
            "stage": "requirements_synthesis",
            "project_id": project_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "user_stories": user_stories,
                "pipeline_context": updated_context
            },
            "next_stage": "architecture_planning"
        }
        
        logger.info(f"Requirements synthesis completed successfully for execution_id: {execution_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error in requirements synthesis: {str(e)}", exc_info=True)
        
        # Return proper error status - raise exception for Step Functions to handle
        error_msg = f"Requirements synthesis failed: {str(e)}"
        raise RuntimeError(error_msg)