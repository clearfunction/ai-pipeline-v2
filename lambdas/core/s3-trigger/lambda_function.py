"""
S3 Trigger Lambda

Automatically starts the AI pipeline when documents are uploaded to the raw S3 bucket.
This lambda is triggered by S3 events and initiates the Step Functions execution.

Author: AI Pipeline Orchestrator v2
Version: 1.0.0
"""

import json
import os
import boto3
from datetime import datetime
from urllib.parse import unquote_plus
from typing import Dict, Any

# Initialize AWS clients
stepfunctions_client = boto3.client('stepfunctions')
s3_client = boto3.client('s3')

# Environment variables
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN', 
                                   'arn:aws:states:us-east-1:008537862626:stateMachine:ai-pipeline-v2-main-dev')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main lambda handler for S3 trigger.
    
    Args:
        event: S3 event containing bucket and object information
        context: Lambda runtime context
        
    Returns:
        Dict containing execution results
    """
    print(f"S3 trigger activated: {json.dumps(event)}")
    
    responses = []
    
    try:
        # Process each S3 record in the event
        for record in event.get('Records', []):
            # Skip if not an S3 event
            if record.get('eventSource') != 'aws:s3':
                continue
                
            # Extract S3 bucket and object information
            bucket_name = record['s3']['bucket']['name']
            object_key = unquote_plus(record['s3']['object']['key'])
            object_size = record['s3']['object'].get('size', 0)
            event_name = record['eventName']
            
            print(f"Processing S3 event: {event_name} for {bucket_name}/{object_key}")
            
            # Only process PUT/POST events (new uploads)
            if not event_name.startswith('ObjectCreated:'):
                print(f"Skipping non-creation event: {event_name}")
                continue
                
            # Skip if file is too small (likely empty) or not a document
            if object_size < 100:
                print(f"Skipping small file: {object_key} ({object_size} bytes)")
                continue
                
            # Check file extension
            valid_extensions = ['.pdf', '.txt', '.doc', '.docx', '.md']
            if not any(object_key.lower().endswith(ext) for ext in valid_extensions):
                print(f"Skipping non-document file: {object_key}")
                continue
            
            # Generate project ID from file name (remove extension and special chars)
            base_name = os.path.splitext(os.path.basename(object_key))[0]
            project_id = base_name.lower().replace(' ', '-').replace('_', '-')[:50]
            project_id = f"{project_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Prepare Step Functions input
            step_functions_input = {
                "project_id": project_id,
                "document_content": f"s3://{bucket_name}/{object_key}",
                "project_metadata": {
                    "project_id": project_id,
                    "name": base_name,
                    "requester": "s3-trigger",
                    "priority": "normal",
                    "source": "s3-upload",
                    "version": "1.0.0",
                    "s3_bucket": bucket_name,
                    "s3_key": object_key,
                    "file_size": object_size
                },
                "project_context": {
                    "project_id": project_id,
                    "project_name": base_name,
                    "description": f"Auto-generated project from {os.path.basename(object_key)}",
                    "environment": ENVIRONMENT
                },
                "execution_config": {
                    "enable_human_review": False,
                    "auto_deploy": True,
                    "validation_level": "standard",
                    "test_mode": False
                }
            }
            
            # Start Step Functions execution
            execution_name = f"{project_id}-{os.urandom(4).hex()}"
            
            try:
                response = stepfunctions_client.start_execution(
                    stateMachineArn=STATE_MACHINE_ARN,
                    name=execution_name,
                    input=json.dumps(step_functions_input)
                )
                
                print(f"✅ Started Step Functions execution: {response['executionArn']}")
                
                responses.append({
                    'status': 'success',
                    'object_key': object_key,
                    'project_id': project_id,
                    'execution_arn': response['executionArn'],
                    'start_date': response['startDate'].isoformat() if hasattr(response['startDate'], 'isoformat') else str(response['startDate'])
                })
                
            except Exception as e:
                print(f"❌ Failed to start Step Functions execution: {str(e)}")
                responses.append({
                    'status': 'error',
                    'object_key': object_key,
                    'project_id': project_id,
                    'error': str(e)
                })
        
        # Return summary
        successful = len([r for r in responses if r['status'] == 'success'])
        failed = len([r for r in responses if r['status'] == 'error'])
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processed {len(responses)} S3 events',
                'successful': successful,
                'failed': failed,
                'details': responses
            })
        }
        
    except Exception as e:
        print(f"Error processing S3 trigger: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to process S3 trigger'
            })
        }