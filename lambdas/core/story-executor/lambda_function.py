"""
Story Executor Lambda - Simplified version without pydantic dependencies.
Generates basic code from user stories using templates.
"""

import json
import os
import hashlib
from typing import Dict, Any, List
import boto3
from datetime import datetime

# Configure logging
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3 = boto3.client('s3')

# Environment variables
CODE_ARTIFACTS_BUCKET = os.environ.get('CODE_ARTIFACTS_BUCKET', 'ai-pipeline-v2-code-artifacts-008537862626-us-east-1')


# The SimpleStoryExecutor class has been removed as it's no longer used.
# The new implementation uses ModernStoryExecutor with project generators.


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for story execution.
    """
    logger.info(f"Starting story execution with execution_id: {context.aws_request_id}")
    logger.info(f"Received event: {json.dumps(event, default=str)}")
    
    try:
        # Extract architecture planner result
        architecture_planner_result = event.get('architecturePlannerResult', {})
        
        if not architecture_planner_result:
            raise ValueError("Missing architecturePlannerResult in event")
        
        # Extract payload from the architecture planner result
        payload = architecture_planner_result.get('Payload', {})
        
        if not payload:
            raise ValueError("Missing Payload in architecturePlannerResult")
        
        # Extract data from payload
        data = payload.get('data', {})
        
        if not data:
            raise ValueError("Missing data in Payload")
        
        # Get user stories and architecture
        # User stories can be in data.user_stories OR data.architecture.user_stories
        user_stories = data.get('user_stories', [])
        architecture = data.get('architecture', {})
        pipeline_context = data.get('pipeline_context', {})
        
        # If no user stories at top level, check inside architecture
        if not user_stories and architecture:
            user_stories = architecture.get('user_stories', [])
            logger.info(f"Found {len(user_stories)} user stories in architecture.user_stories")
        
        if not user_stories:
            logger.error(f"No user stories found. Data keys: {list(data.keys())}")
            if architecture:
                logger.error(f"Architecture keys: {list(architecture.keys())}")
            raise ValueError("No user stories found in data")
        
        if not architecture:
            raise ValueError("No architecture found in data")
        
        logger.info(f"🚀 Generating project using proven generators and AI enhancement for {len(user_stories)} user stories")
        
        # Create execution context
        execution_id = f"story_exec_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{context.aws_request_id[:8]}"
        project_id = architecture.get('project_id', 'unknown-project')
        
        # Execute ALL user stories using modern project generator approach
        from modern_story_executor import ModernStoryExecutor
        
        executor = ModernStoryExecutor()
        all_generated_files = executor.execute_stories(user_stories, architecture)
        
        # Convert GeneratedCode objects to dictionaries for JSON serialization
        generated_files_dict = []
        for file in all_generated_files:
            file_dict = {
                "file_path": file.file_path,
                "content": file.content,
                "component_id": file.component_id,
                "story_id": file.story_id,
                "file_type": file.file_type,
                "language": file.language,
                "content_hash": file.content_hash,
                "size_bytes": file.size_bytes,
                "created_at": file.created_at
            }
            generated_files_dict.append(file_dict)
        
        # Store files in S3
        store_files_to_s3(generated_files_dict, project_id, execution_id)
        
        # Process stories and update status
        processed_stories = []
        completed_stories = []
        
        for story in user_stories:
            try:
                # Mark story as completed since files were generated successfully
                story_copy = story.copy()
                story_copy['status'] = 'completed'
                processed_stories.append(story_copy)
                completed_stories.append(story_copy)
                
                logger.info(f"✅ Story '{story.get('title')}' completed successfully")
                
            except Exception as e:
                # Mark story as failed
                story_copy = story.copy()
                story_copy['status'] = 'failed' 
                story_copy['error'] = str(e)
                processed_stories.append(story_copy)
                
                logger.error(f"❌ Failed to execute story '{story.get('title')}': {str(e)}")
        
        # Create component specifications from generated files for integration validator
        components = []
        unique_component_ids = set()
        
        for file_dict in generated_files_dict:
            component_id = file_dict.get('component_id', 'unknown')
            file_path = file_dict.get('file_path', '')
            
            # Only create one component spec per unique component_id
            if component_id not in unique_component_ids:
                unique_component_ids.add(component_id)
                
                # Create component name from component_id or file_path
                if component_id.startswith('comp_'):
                    component_name = file_path.split('/')[-1].split('.')[0] if file_path else component_id
                elif component_id == 'project_scaffold':
                    component_name = 'ProjectScaffold'
                else:
                    component_name = component_id
                
                components.append({
                    'component_id': component_id,
                    'name': component_name,
                    'type': file_dict.get('file_type', 'source'),
                    'file_path': file_path,
                    'dependencies': [],  # Modern approach doesn't track explicit dependencies
                    'exports': [component_name],
                    'story_ids': [file_dict.get('story_id', 'unknown')]
                })
        
        logger.info(f"Created {len(components)} component specifications from generated files")
        
        # Update architecture with generated components
        updated_architecture = architecture.copy()
        updated_architecture['components'] = components
        
        # Create response with file metadata only (not content) to avoid size limits
        response = {
            "status": "success",
            "message": f"All {len(user_stories)} stories executed successfully - generated {len(generated_files_dict)} files",
            "execution_id": execution_id,
            "stage": "story_execution",
            "project_id": project_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                # Return file metadata with S3 references instead of content
                "generated_files": [
                    {
                        "file_path": f["file_path"],
                        "component_id": f.get("component_id", ""),
                        "story_id": f.get("story_id", ""),
                        "file_type": f.get("file_type", ""),
                        "language": f.get("language", ""),
                        "size_bytes": f.get("size_bytes", 0),
                        "content_hash": f.get("content_hash", ""),
                        "s3_bucket": CODE_ARTIFACTS_BUCKET,
                        "s3_key": f"projects/{project_id}/executions/{execution_id}/{f['file_path']}"
                    }
                    for f in generated_files_dict
                ],
                "files_stored_in_s3": {
                    "bucket": CODE_ARTIFACTS_BUCKET,
                    "prefix": f"projects/{project_id}/executions/{execution_id}/"
                },
                "processed_stories": processed_stories,
                "stories_completed": len(completed_stories),
                "stories_failed": len(processed_stories) - len(completed_stories),
                "pipeline_context": {
                    "execution_id": execution_id,
                    "project_id": project_id,
                    "stage": "story_execution",
                    "user_story": None if len(user_stories) != 1 else completed_stories[0] if completed_stories else None,
                    "processed_stories": processed_stories,
                    "architecture": updated_architecture,
                    # Removed generated_files from pipeline_context to reduce size
                    "created_at": datetime.utcnow().isoformat()
                },
                "architecture": updated_architecture
            },
            "next_stage": "integration_validation"
        }
        
        logger.info(f"Multi-story execution completed for execution_id: {execution_id} - {len(completed_stories)}/{len(processed_stories)} stories successful")
        return response
        
    except Exception as e:
        logger.error(f"Error in story execution: {str(e)}", exc_info=True)
        
        # Return proper error status - raise exception for Step Functions to handle
        error_msg = f"Story execution failed: {str(e)}"
        raise RuntimeError(error_msg)


def store_files_to_s3(generated_files: List[Dict[str, Any]], project_id: str, execution_id: str) -> None:
    """Store generated files to S3."""
    bucket = CODE_ARTIFACTS_BUCKET
    
    for file_info in generated_files:
        file_path = file_info['file_path']
        content = file_info['content']
        
        # Create S3 key with project and execution context
        s3_key = f"projects/{project_id}/executions/{execution_id}/{file_path}"
        
        try:
            s3.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=content.encode('utf-8'),
                ContentType='text/plain',
                Metadata={
                    'project-id': project_id,
                    'execution-id': execution_id,
                    'component-id': file_info.get('component_id', ''),
                    'story-id': file_info.get('story_id', ''),
                    'file-type': file_info.get('file_type', ''),
                    'language': file_info.get('language', ''),
                    'content-hash': str(file_info.get('content_hash', ''))
                }
            )
            
            logger.info(f"Stored file to S3: {s3_key}")
            
        except Exception as e:
            logger.error(f"Failed to store file {file_path}: {e}")
            raise