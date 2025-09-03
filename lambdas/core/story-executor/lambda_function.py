"""
Story Executor Lambda (Refactored for Sequential Processing)

Executes stories one at a time with validation and commit after each story
rather than processing all stories at once. This enables immediate feedback
and rollback capability.

Author: AI Pipeline Orchestrator v2
Version: 2.0.0 (Sequential Story Processing)
"""

import json
import os
import sys
from typing import Dict, Any, List, Optional, Tuple
import boto3
from datetime import datetime
import hashlib
import time

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

# Import shared services
sys.path.append('/opt/python')
from shared.services.llm_service import LLMService
from shared.utils.logger import setup_logger, log_lambda_start, log_lambda_end, log_error

logger = setup_logger("story-executor")


class SequentialStoryExecutor:
    """
    Executes stories sequentially with validation and commit after each.
    Maintains execution state and enables rollback if issues are detected.
    """
    
    def __init__(self):
        self.s3_client = s3_client
        self.dynamodb = dynamodb
        self.lambda_client = lambda_client
        self.llm_service = LLMService()
        
        # Get configuration from environment
        self.code_artifacts_bucket = os.environ.get('CODE_ARTIFACTS_BUCKET', 'ai-pipeline-v2-code-artifacts')
        self.processed_bucket = os.environ.get('PROCESSED_BUCKET_NAME')
        self.story_table = os.environ.get('USER_STORIES_TABLE', 'ai-pipeline-v2-user-stories-dev')
        
        # Lambda function names for sequential pipeline
        self.validator_lambda = os.environ.get('VALIDATOR_LAMBDA', 'ai-pipeline-v2-story-validator-dev')
        self.github_lambda = os.environ.get('GITHUB_LAMBDA', 'ai-pipeline-v2-github-orchestrator-dev')
        self.build_lambda = os.environ.get('BUILD_LAMBDA', 'ai-pipeline-v2-build-orchestrator-dev')
        
        # Load execution configuration
        self.config = self._load_execution_config()
    
    def _load_execution_config(self) -> Dict[str, Any]:
        """Load execution configuration."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.processed_bucket,
                Key='config/validation-config.json'
            )
            config = json.loads(response['Body'].read().decode('utf-8'))
            return config.get('sequential_processing', {})
        except Exception as e:
            logger.warning(f"Could not load config: {e}, using defaults")
            return {
                "process_stories_sequentially": True,
                "validate_after_each_story": True,
                "commit_after_validation": True,
                "max_retries_per_story": 2,
                "checkpoint_after_each_story": True,
                "enable_rollback": True,
                "max_stories_per_execution": 20
            }
    
    def execute_story_sequence(
        self,
        user_stories: List[Dict[str, Any]],
        architecture: Dict[str, Any],
        project_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute stories sequentially with validation and commit after each.
        
        Args:
            user_stories: List of user stories to execute
            architecture: Project architecture specification
            project_context: Overall project context
            
        Returns:
            Execution result with all generated files and execution history
        """
        execution_id = f"seq_exec_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        project_id = project_context.get('project_id')
        
        logger.info(f"Starting sequential execution for {len(user_stories)} stories")
        
        # Initialize execution state
        execution_state = {
            'execution_id': execution_id,
            'project_id': project_id,
            'total_stories': len(user_stories),
            'completed_stories': [],
            'failed_stories': [],
            'generated_files': [],
            'commit_history': [],
            'repository_info': None,
            'checkpoints': [],
            'current_story_index': 0,
            'start_time': datetime.utcnow().isoformat()
        }
        
        # Setup GitHub repository and deployment infrastructure once
        if self.config.get('commit_after_validation'):
            logger.info("Setting up GitHub repository and deployment infrastructure")
            setup_result = self._setup_github_infrastructure(
                project_id,
                architecture.get('tech_stack'),
                architecture
            )
            execution_state['repository_info'] = setup_result.get('repository_info')
            execution_state['deployment_info'] = setup_result.get('deployment_info')
        
        # Process stories sequentially
        for index, story in enumerate(user_stories):
            story_id = story.get('story_id', f"story_{index}")
            logger.info(f"Processing story {index + 1}/{len(user_stories)}: {story.get('title')}")
            
            execution_state['current_story_index'] = index
            
            # Add story metadata
            story_metadata = {
                'story_id': story_id,
                'title': story.get('title'),
                'index': index,
                'is_first_story': index == 0,
                'is_last_story': index == len(user_stories) - 1,
                'acceptance_criteria': story.get('acceptance_criteria', [])
            }
            
            try:
                # 1. Generate code for the story
                story_result = self._execute_single_story(
                    story,
                    architecture,
                    execution_state['generated_files'],
                    project_context
                )
                
                if not story_result.get('success'):
                    raise RuntimeError(f"Story generation failed: {story_result.get('error')}")
                
                story_files = story_result.get('generated_files', [])
                logger.info(f"Generated {len(story_files)} files for story: {story.get('title')}")
                
                # 2. Validate the generated code if enabled
                validation_passed = True
                if self.config.get('validate_after_each_story'):
                    validation_result = self._validate_story(
                        story_files,
                        execution_state['generated_files'],
                        story_metadata,
                        architecture,
                        project_context
                    )
                    
                    validation_passed = validation_result.get('validation_passed', False)
                    
                    if validation_passed:
                        logger.info(f"✅ Validation passed for story: {story.get('title')}")
                        # Use fixed files if auto-fix was applied
                        if validation_result.get('auto_fix_applied'):
                            story_files = validation_result.get('fixed_files', story_files)
                            logger.info(f"Auto-fix applied, using {len(story_files)} fixed files")
                    else:
                        # Retry story generation if validation failed
                        retry_count = 0
                        max_retries = self.config.get('max_retries_per_story', 2)
                        
                        while not validation_passed and retry_count < max_retries:
                            retry_count += 1
                            logger.warning(f"Validation failed, retrying story (attempt {retry_count}/{max_retries})")
                            
                            # Regenerate with validation feedback
                            retry_result = self._execute_single_story(
                                story,
                                architecture,
                                execution_state['generated_files'],
                                project_context,
                                validation_feedback=validation_result.get('issues', [])
                            )
                            
                            if retry_result.get('success'):
                                story_files = retry_result.get('generated_files', [])
                                
                                # Re-validate
                                validation_result = self._validate_story(
                                    story_files,
                                    execution_state['generated_files'],
                                    story_metadata,
                                    architecture,
                                    project_context
                                )
                                validation_passed = validation_result.get('validation_passed', False)
                        
                        if not validation_passed:
                            raise RuntimeError(f"Validation failed after {max_retries} retries")
                
                # 3. Build validation if enabled
                if validation_passed and self.config.get('build_after_validation'):
                    build_result = self._execute_build(
                        story_files,
                        execution_state['generated_files'],
                        story_metadata,
                        architecture,
                        project_context
                    )
                    
                    if not build_result.get('build_passed'):
                        logger.warning(f"Build failed for story: {story.get('title')}")
                        # Apply auto-fixes if available
                        if build_result.get('auto_fix_applied'):
                            story_files = build_result.get('fixed_files', story_files)
                            logger.info("Build fixes applied")
                
                # 4. Commit to GitHub if enabled and validation passed
                if validation_passed and self.config.get('commit_after_validation'):
                    commit_result = self._commit_story(
                        story_files,
                        story_metadata,
                        project_context,
                        architecture,
                        execution_state['repository_info'],
                        execution_state['commit_history']
                    )
                    
                    if commit_result.get('success'):
                        execution_state['commit_history'] = commit_result.get('commit_history', [])
                        logger.info(f"✅ Committed story to GitHub: {commit_result.get('commit_id', 'unknown')[:8]}")
                
                # 5. Add files to cumulative list
                execution_state['generated_files'].extend(story_files)
                
                # 6. Create checkpoint
                if self.config.get('checkpoint_after_each_story'):
                    checkpoint = self._create_checkpoint(
                        execution_state,
                        story_metadata
                    )
                    execution_state['checkpoints'].append(checkpoint)
                    logger.info(f"Created checkpoint: {checkpoint['checkpoint_id']}")
                
                # 7. Mark story as completed
                execution_state['completed_stories'].append({
                    'story_id': story_id,
                    'title': story.get('title'),
                    'files_generated': len(story_files),
                    'validation_passed': validation_passed,
                    'commit_id': execution_state['commit_history'][-1]['commit_id'] if execution_state['commit_history'] else None
                })
                
                logger.info(f"✅ Story completed successfully: {story.get('title')}")
                
            except Exception as e:
                logger.error(f"Failed to execute story {story.get('title')}: {e}")
                
                # Mark story as failed
                execution_state['failed_stories'].append({
                    'story_id': story_id,
                    'title': story.get('title'),
                    'error': str(e),
                    'index': index
                })
                
                # Decide whether to continue or stop
                if self.config.get('stop_on_failure', False):
                    logger.error("Stopping execution due to story failure")
                    break
                else:
                    logger.warning("Continuing with next story despite failure")
        
        # Create final PR if all stories are complete
        if (execution_state['completed_stories'] and 
            self.config.get('commit_after_validation') and 
            execution_state['commit_history']):
            
            # Check if this is the last story
            if execution_state['current_story_index'] == len(user_stories) - 1:
                logger.info("Creating final pull request")
                # The last commit should have created the PR
                # Extract PR info from the last commit result
                if execution_state['commit_history']:
                    last_commit = execution_state['commit_history'][-1]
                    execution_state['pull_request'] = last_commit.get('pr_info')
        
        # Calculate execution summary
        execution_summary = {
            'execution_id': execution_id,
            'project_id': project_id,
            'total_stories': len(user_stories),
            'completed_stories': len(execution_state['completed_stories']),
            'failed_stories': len(execution_state['failed_stories']),
            'total_files_generated': len(execution_state['generated_files']),
            'total_commits': len(execution_state['commit_history']),
            'execution_time': self._calculate_execution_time(execution_state['start_time']),
            'repository_url': execution_state['repository_info']['html_url'] if execution_state.get('repository_info') else None,
            'pull_request_url': execution_state.get('pull_request', {}).get('html_url')
        }
        
        # Store execution state for recovery
        self._store_execution_state(execution_state)
        
        return {
            'execution_summary': execution_summary,
            'execution_state': execution_state,
            'generated_files': execution_state['generated_files'],
            'completed_stories': execution_state['completed_stories'],
            'failed_stories': execution_state['failed_stories']
        }
    
    def _execute_single_story(
        self,
        story: Dict[str, Any],
        architecture: Dict[str, Any],
        existing_files: List[Dict[str, Any]],
        project_context: Dict[str, Any],
        validation_feedback: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute a single story and generate code."""
        try:
            # Prepare context with existing files
            generation_context = {
                'story': story,
                'architecture': architecture,
                'existing_files': [
                    {'file_path': f['file_path'], 'purpose': f.get('purpose', '')}
                    for f in existing_files
                ],
                'project_context': project_context,
                'validation_feedback': validation_feedback
            }
            
            # Generate code using LLM service
            prompt = self._create_generation_prompt(generation_context)
            response = self.llm_service.invoke(prompt)
            
            # Parse generated files from response
            generated_files = self._parse_generated_files(response, story)
            
            # Store files in S3
            stored_files = self._store_files_to_s3(
                generated_files,
                project_context.get('project_id'),
                story.get('story_id')
            )
            
            return {
                'success': True,
                'generated_files': stored_files,
                'story_id': story.get('story_id')
            }
            
        except Exception as e:
            logger.error(f"Failed to execute story: {e}")
            return {
                'success': False,
                'error': str(e),
                'story_id': story.get('story_id')
            }
    
    def _validate_story(
        self,
        story_files: List[Dict[str, Any]],
        existing_files: List[Dict[str, Any]],
        story_metadata: Dict[str, Any],
        architecture: Dict[str, Any],
        project_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate generated story files."""
        try:
            # Invoke the story validator lambda
            payload = {
                'story_files': story_files,
                'existing_files': existing_files,
                'story_metadata': story_metadata,
                'architecture': architecture,
                'project_context': project_context
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.validator_lambda,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            return result.get('data', {})
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                'validation_passed': False,
                'error': str(e)
            }
    
    def _execute_build(
        self,
        story_files: List[Dict[str, Any]],
        existing_files: List[Dict[str, Any]],
        story_metadata: Dict[str, Any],
        architecture: Dict[str, Any],
        project_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute build validation."""
        try:
            # Invoke the build orchestrator lambda
            payload = {
                'story_files': story_files,
                'existing_files': existing_files,
                'story_metadata': story_metadata,
                'architecture': architecture,
                'project_context': project_context
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.build_lambda,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            return result.get('data', {})
            
        except Exception as e:
            logger.error(f"Build execution failed: {e}")
            return {
                'build_passed': False,
                'error': str(e)
            }
    
    def _commit_story(
        self,
        story_files: List[Dict[str, Any]],
        story_metadata: Dict[str, Any],
        project_context: Dict[str, Any],
        architecture: Dict[str, Any],
        repository_info: Optional[Dict[str, Any]],
        commit_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Commit story files to GitHub."""
        try:
            # Invoke the GitHub orchestrator lambda
            payload = {
                'operation_mode': 'incremental_commit',
                'story_files': story_files,
                'story_metadata': story_metadata,
                'project_context': project_context,
                'architecture': architecture,
                'repository_info': repository_info,
                'commit_history': commit_history
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.github_lambda,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            data = result.get('data', {})
            
            return {
                'success': True,
                'commit_id': data.get('commit_info', {}).get('sha'),
                'commit_history': data.get('commit_history', []),
                'pr_info': data.get('pr_info')
            }
            
        except Exception as e:
            logger.error(f"GitHub commit failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _setup_github_infrastructure(
        self,
        project_id: str,
        tech_stack: str,
        architecture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Setup GitHub repository and deployment infrastructure."""
        try:
            payload = {
                'operation_mode': 'setup_deployment',
                'project_id': project_id,
                'tech_stack': tech_stack,
                'architecture': architecture
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.github_lambda,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            return result.get('data', {})
            
        except Exception as e:
            logger.error(f"GitHub setup failed: {e}")
            return {}
    
    def _create_checkpoint(
        self,
        execution_state: Dict[str, Any],
        story_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a checkpoint for potential rollback."""
        checkpoint = {
            'checkpoint_id': f"ckpt_{story_metadata['story_id']}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            'story_id': story_metadata['story_id'],
            'story_index': story_metadata['index'],
            'files_count': len(execution_state['generated_files']),
            'commit_id': execution_state['commit_history'][-1]['commit_id'] if execution_state['commit_history'] else None,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store checkpoint in DynamoDB
        try:
            table = self.dynamodb.Table(self.story_table)
            table.put_item(Item={
                'story_id': f"checkpoint-{checkpoint['checkpoint_id']}",
                'checkpoint': checkpoint,
                'execution_state_summary': {
                    'completed_stories': len(execution_state['completed_stories']),
                    'total_files': len(execution_state['generated_files']),
                    'total_commits': len(execution_state['commit_history'])
                },
                'ttl': int(datetime.utcnow().timestamp()) + (7 * 24 * 60 * 60)  # 7 days
            })
        except Exception as e:
            logger.error(f"Failed to store checkpoint: {e}")
        
        return checkpoint
    
    def rollback_to_checkpoint(
        self,
        project_id: str,
        checkpoint_id: str
    ) -> Dict[str, Any]:
        """Rollback to a previous checkpoint."""
        try:
            # Retrieve checkpoint from DynamoDB
            table = self.dynamodb.Table(self.story_table)
            response = table.get_item(Key={'story_id': f"checkpoint-{checkpoint_id}"})
            
            if 'Item' not in response:
                raise ValueError(f"Checkpoint {checkpoint_id} not found")
            
            checkpoint = response['Item']['checkpoint']
            
            # Invoke GitHub orchestrator for rollback
            if checkpoint.get('commit_id'):
                payload = {
                    'operation_mode': 'rollback',
                    'project_id': project_id,
                    'checkpoint_id': checkpoint['commit_id'],
                    'repository_info': {'full_name': f"{project_id}/{project_id}"}  # Simplified
                }
                
                response = self.lambda_client.invoke(
                    FunctionName=self.github_lambda,
                    InvocationType='RequestResponse',
                    Payload=json.dumps(payload)
                )
                
                result = json.loads(response['Payload'].read())
                return result.get('data', {})
            
            return {'message': 'No commit to rollback to'}
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {'error': str(e)}
    
    def _create_generation_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for code generation."""
        story = context['story']
        architecture = context['architecture']
        existing_files = context.get('existing_files', [])
        validation_feedback = context.get('validation_feedback', [])
        
        prompt = f"""Generate code for the following user story in a {architecture.get('tech_stack')} project.

User Story: {story.get('title')}
Description: {story.get('description', '')}
Acceptance Criteria:
{chr(10).join([f"- {c}" for c in story.get('acceptance_criteria', [])])}

Project Architecture:
- Tech Stack: {architecture.get('tech_stack')}
- Framework: {architecture.get('framework', 'default')}
- Dependencies: {json.dumps(architecture.get('dependencies', {}), indent=2)}

Existing Files in Project:
{chr(10).join([f"- {f['file_path']}: {f.get('purpose', '')}" for f in existing_files[:20]])}

{f"Validation Feedback to Address:{chr(10)}{chr(10).join([f'- {issue}' for issue in validation_feedback])}" if validation_feedback else ""}

Generate the complete code files needed to implement this story. For each file, provide:
1. File path
2. Complete code content
3. Purpose/description

Format your response as:
FILE: <file_path>
PURPOSE: <purpose>
```<language>
<code content>
```
"""
        return prompt
    
    def _parse_generated_files(self, response: str, story: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse generated files from LLM response."""
        files = []
        
        # Simple parsing - in production, use more robust parsing
        parts = response.split('FILE:')
        for part in parts[1:]:  # Skip first empty part
            lines = part.strip().split('\n')
            if len(lines) < 3:
                continue
            
            file_path = lines[0].strip()
            
            # Find PURPOSE line
            purpose_line = next((l for l in lines if l.startswith('PURPOSE:')), '')
            purpose = purpose_line.replace('PURPOSE:', '').strip() if purpose_line else ''
            
            # Extract code content between ```
            code_start = -1
            code_end = -1
            for i, line in enumerate(lines):
                if line.strip().startswith('```'):
                    if code_start == -1:
                        code_start = i
                    else:
                        code_end = i
                        break
            
            if code_start != -1 and code_end != -1:
                code_lines = lines[code_start + 1:code_end]
                content = '\n'.join(code_lines)
                
                files.append({
                    'file_path': file_path,
                    'content': content,
                    'purpose': purpose,
                    'story_id': story.get('story_id'),
                    'story_title': story.get('title'),
                    'language': self._detect_language(file_path),
                    'size_bytes': len(content.encode('utf-8'))
                })
        
        return files
    
    def _detect_language(self, file_path: str) -> str:
        """Detect language from file extension."""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown'
        }
        
        for ext, lang in ext_map.items():
            if file_path.endswith(ext):
                return lang
        
        return 'text'
    
    def _store_files_to_s3(
        self,
        files: List[Dict[str, Any]],
        project_id: str,
        story_id: str
    ) -> List[Dict[str, Any]]:
        """Store generated files in S3."""
        stored_files = []
        
        for file in files:
            try:
                # Generate S3 key
                s3_key = f"projects/{project_id}/stories/{story_id}/{file['file_path']}"
                
                # Store in S3
                self.s3_client.put_object(
                    Bucket=self.code_artifacts_bucket,
                    Key=s3_key,
                    Body=file['content'].encode('utf-8'),
                    ContentType='text/plain',
                    Metadata={
                        'story_id': story_id,
                        'project_id': project_id,
                        'language': file.get('language', 'text')
                    }
                )
                
                # Add S3 reference to file metadata
                file_with_s3 = file.copy()
                file_with_s3['s3_bucket'] = self.code_artifacts_bucket
                file_with_s3['s3_key'] = s3_key
                file_with_s3['content_hash'] = hashlib.md5(file['content'].encode()).hexdigest()
                
                # Remove content to save memory
                del file_with_s3['content']
                
                stored_files.append(file_with_s3)
                
            except Exception as e:
                logger.error(f"Failed to store file {file['file_path']}: {e}")
        
        return stored_files
    
    def _store_execution_state(self, execution_state: Dict[str, Any]):
        """Store execution state for recovery."""
        try:
            table = self.dynamodb.Table(self.story_table)
            table.put_item(Item={
                'story_id': f"execution-{execution_state['execution_id']}",
                'execution_state': execution_state,
                'timestamp': datetime.utcnow().isoformat(),
                'ttl': int(datetime.utcnow().timestamp()) + (30 * 24 * 60 * 60)  # 30 days
            })
        except Exception as e:
            logger.error(f"Failed to store execution state: {e}")
    
    def _calculate_execution_time(self, start_time: str) -> float:
        """Calculate execution time in seconds."""
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end = datetime.utcnow()
            return (end - start).total_seconds()
        except:
            return 0.0


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for sequential story execution.
    
    This refactored version processes stories one at a time with
    validation and commit after each story.
    """
    execution_id = log_lambda_start(event, context)
    
    try:
        executor = SequentialStoryExecutor()
        
        # Determine operation mode
        operation_mode = event.get('operation_mode', 'sequential_execution')
        
        if operation_mode == 'sequential_execution':
            # Extract data from architecture planner result (Step Functions format)
            if 'architecturePlannerResult' in event:
                planner_result = event.get('architecturePlannerResult', {}).get('Payload', {})
                data = planner_result.get('data', {})
            else:
                # Direct invocation
                data = event.get('data', {})
            
            user_stories = data.get('user_stories', [])
            architecture = data.get('architecture', {})
            project_context = data.get('pipeline_context', {})
            
            # If stories are in architecture, use those
            if not user_stories and architecture.get('user_stories'):
                user_stories = architecture['user_stories']
            
            if not user_stories:
                raise ValueError("No user stories found")
            
            # Execute stories sequentially
            execution_result = executor.execute_story_sequence(
                user_stories,
                architecture,
                project_context
            )
            
            response = {
                'status': 'success',
                'message': f"Sequential execution completed: {execution_result['execution_summary']['completed_stories']}/{execution_result['execution_summary']['total_stories']} stories succeeded",
                'execution_id': execution_id,
                'stage': 'story_execution',
                'project_id': project_context.get('project_id'),
                'timestamp': datetime.utcnow().isoformat(),
                'data': {
                    'execution_summary': execution_result['execution_summary'],
                    'generated_files': execution_result['generated_files'],
                    'completed_stories': execution_result['completed_stories'],
                    'failed_stories': execution_result['failed_stories'],
                    'pipeline_context': project_context,
                    'architecture': architecture
                },
                'next_stage': 'complete' if execution_result['execution_summary']['pull_request_url'] else 'review'
            }
            
        elif operation_mode == 'rollback':
            # Rollback to checkpoint
            project_id = event.get('project_id')
            checkpoint_id = event.get('checkpoint_id')
            
            rollback_result = executor.rollback_to_checkpoint(project_id, checkpoint_id)
            
            response = {
                'status': 'success',
                'message': f"Rolled back to checkpoint {checkpoint_id}",
                'execution_id': execution_id,
                'stage': 'story_execution_rollback',
                'data': rollback_result
            }
            
        else:
            raise ValueError(f"Unknown operation mode: {operation_mode}")
        
        log_lambda_end(execution_id, response)
        return response
        
    except Exception as e:
        error_msg = f"Story execution failed: {str(e)}"
        log_error(e, execution_id, "story_execution")
        
        error_response = {
            'status': 'error',
            'message': error_msg,
            'execution_id': execution_id,
            'stage': 'story_execution',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }
        
        log_lambda_end(execution_id, error_response)
        raise RuntimeError(error_msg)