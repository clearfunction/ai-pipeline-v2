"""
S3 service for AI Pipeline Orchestrator v2.

Provides centralized S3 operations with project-based path management.
"""

import boto3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from botocore.exceptions import ClientError
from loguru import logger


class S3Service:
    """Service for S3 operations with project-based organization."""
    
    def __init__(self, region_name: str = 'us-east-1'):
        """
        Initialize S3 service.
        
        Args:
            region_name: AWS region name
        """
        self.s3_client = boto3.client('s3', region_name=region_name)
        self.region_name = region_name
    
    def get_object(self, bucket_name: str, key: str) -> str:
        """
        Get object content from S3.
        
        Args:
            bucket_name: S3 bucket name
            key: Object key
            
        Returns:
            Object content as string
            
        Raises:
            ClientError: If object not found or access denied
        """
        try:
            response = self.s3_client.get_object(Bucket=bucket_name, Key=key)
            content = response['Body'].read().decode('utf-8')
            
            logger.info(
                "S3 object retrieved",
                bucket=bucket_name,
                key=key,
                content_length=len(content)
            )
            
            return content
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(
                "Failed to get S3 object",
                bucket=bucket_name,
                key=key,
                error_code=error_code,
                error_message=str(e)
            )
            raise
    
    def put_object(self, bucket_name: str, key: str, content: str, 
                   content_type: str = 'text/plain', metadata: Optional[Dict[str, str]] = None) -> bool:
        """
        Put object content to S3.
        
        Args:
            bucket_name: S3 bucket name
            key: Object key
            content: Content to store
            content_type: MIME content type
            metadata: Optional metadata dictionary
            
        Returns:
            True if successful
            
        Raises:
            ClientError: If put operation fails
        """
        try:
            put_args = {
                'Bucket': bucket_name,
                'Key': key,
                'Body': content.encode('utf-8'),
                'ContentType': content_type
            }
            
            if metadata:
                put_args['Metadata'] = metadata
            
            self.s3_client.put_object(**put_args)
            
            logger.info(
                "S3 object stored",
                bucket=bucket_name,
                key=key,
                content_length=len(content),
                content_type=content_type
            )
            
            return True
            
        except ClientError as e:
            logger.error(
                "Failed to put S3 object",
                bucket=bucket_name,
                key=key,
                error_message=str(e)
            )
            raise
    
    def list_objects(self, bucket_name: str, prefix: str = '', max_keys: int = 1000) -> List[Dict[str, Any]]:
        """
        List objects in S3 bucket with optional prefix.
        
        Args:
            bucket_name: S3 bucket name
            prefix: Key prefix filter
            max_keys: Maximum number of keys to return
            
        Returns:
            List of object metadata dictionaries
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            objects = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    objects.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'etag': obj['ETag'].strip('"')
                    })
            
            logger.info(
                "S3 objects listed",
                bucket=bucket_name,
                prefix=prefix,
                object_count=len(objects)
            )
            
            return objects
            
        except ClientError as e:
            logger.error(
                "Failed to list S3 objects",
                bucket=bucket_name,
                prefix=prefix,
                error_message=str(e)
            )
            raise
    
    def object_exists(self, bucket_name: str, key: str) -> bool:
        """
        Check if object exists in S3.
        
        Args:
            bucket_name: S3 bucket name
            key: Object key
            
        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def delete_object(self, bucket_name: str, key: str) -> bool:
        """
        Delete object from S3.
        
        Args:
            bucket_name: S3 bucket name
            key: Object key
            
        Returns:
            True if successful
        """
        try:
            self.s3_client.delete_object(Bucket=bucket_name, Key=key)
            
            logger.info(
                "S3 object deleted",
                bucket=bucket_name,
                key=key
            )
            
            return True
            
        except ClientError as e:
            logger.error(
                "Failed to delete S3 object",
                bucket=bucket_name,
                key=key,
                error_message=str(e)
            )
            raise
    
    def generate_project_path(self, project_name: str, project_date: str, path_type: str, 
                            execution_id: Optional[str] = None, filename: Optional[str] = None) -> str:
        """
        Generate project-based S3 path.
        
        Args:
            project_name: Name of the project
            project_date: Project date (YYYY-MM-DD format)
            path_type: Type of path ('raw', 'processed', 'generated', 'vectors')
            execution_id: Optional execution ID for sub-paths
            filename: Optional filename
            
        Returns:
            Generated S3 key path
        """
        path_components = [f"{project_name}-{project_date}", path_type]
        
        if execution_id:
            path_components.append(execution_id)
        
        if filename:
            path_components.append(filename)
        
        return '/'.join(path_components)
    
    def store_code_artifact(self, bucket_name: str, project_name: str, project_date: str,
                          execution_id: str, file_path: str, content: str) -> str:
        """
        Store generated code artifact with project-based path.
        
        Args:
            bucket_name: S3 bucket name
            project_name: Project name
            project_date: Project date
            execution_id: Execution ID
            file_path: Relative file path (e.g., 'src/components/LoginPage.tsx')
            content: File content
            
        Returns:
            S3 key where content was stored
        """
        s3_key = self.generate_project_path(
            project_name=project_name,
            project_date=project_date,
            path_type='generated',
            execution_id=execution_id,
            filename=file_path
        )
        
        # Determine content type based on file extension
        content_type = self._get_content_type(file_path)
        
        # Add metadata
        metadata = {
            'project-name': project_name,
            'project-date': project_date,
            'execution-id': execution_id,
            'file-path': file_path,
            'generated-at': datetime.utcnow().isoformat()
        }
        
        self.put_object(bucket_name, s3_key, content, content_type, metadata)
        
        return s3_key
    
    def _get_content_type(self, file_path: str) -> str:
        """
        Get content type based on file extension.
        
        Args:
            file_path: File path with extension
            
        Returns:
            MIME content type
        """
        extension_mapping = {
            '.js': 'application/javascript',
            '.ts': 'application/typescript',
            '.tsx': 'application/typescript',
            '.jsx': 'application/javascript',
            '.py': 'text/x-python',
            '.css': 'text/css',
            '.scss': 'text/x-scss',
            '.html': 'text/html',
            '.json': 'application/json',
            '.md': 'text/markdown',
            '.yml': 'application/x-yaml',
            '.yaml': 'application/x-yaml',
            '.txt': 'text/plain'
        }
        
        import os
        file_extension = os.path.splitext(file_path)[1].lower()
        return extension_mapping.get(file_extension, 'text/plain')