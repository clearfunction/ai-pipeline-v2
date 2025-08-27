"""
Document Processor Lambda - Handles multi-format document intake with versioning.
Processes PDFs, JSON transcripts, emails, chats and stores with metadata tracking.
"""

import json
import hashlib
import os
from datetime import datetime
from typing import Dict, Any, List
from io import BytesIO
import boto3
from botocore.exceptions import ClientError

# PDF processing imports
try:
    import pypdf
except ImportError:
    pypdf = None

# Import shared components - avoiding pydantic to prevent dependency issues
import sys
sys.path.append('/opt/python')

# Avoid importing pydantic models to prevent dependency issues
# from shared.models.pipeline_models import (
#     DocumentMetadata, DocumentType, PipelineContext, LambdaResponse
# )

# Configure logging directly to avoid pydantic dependencies
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Note: Anthropic client not needed for document processing


# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
RAW_BUCKET = os.environ.get('RAW_BUCKET_NAME')
PROCESSED_BUCKET = os.environ.get('PROCESSED_BUCKET_NAME')
METADATA_TABLE = os.environ.get('DOCUMENT_METADATA_TABLE', 'ai-pipeline-v2-document-metadata')


class DocumentProcessor:
    """Handles multi-format document processing and versioning."""
    
    def __init__(self):
        """Initialize the document processor."""
        self.logger = logger
        self.metadata_table = dynamodb.Table(METADATA_TABLE)
        self.processed_bucket = PROCESSED_BUCKET
    
    def process_documents(self, input_sources: List[Dict[str, Any]], execution_id: str) -> List[Dict[str, Any]]:
        """
        Process multiple input documents and extract content.
        
        Args:
            input_sources: List of source documents with type and location
            execution_id: Unique execution identifier
            
        Returns:
            List of processed document metadata as dictionaries
        """
        processed_docs = []
        
        for source in input_sources:
            try:
                doc_metadata = self._process_single_document(source, execution_id)
                processed_docs.append(doc_metadata)
                self.logger.info(f"Processed document: {doc_metadata['document_id']}")
                
            except Exception as e:
                self.logger.error(f"Failed to process document {source.get('path', 'unknown')}: {e}")
                # Continue processing other documents
                continue
        
        return processed_docs
    
    def _process_single_document(self, source: Dict[str, Any], execution_id: str) -> Dict[str, Any]:
        """
        Process a single document based on its type.
        
        Args:
            source: Document source information
            execution_id: Execution identifier
            
        Returns:
            Document metadata as dictionary
        """
        doc_type = source['type']  # Use string directly instead of enum
        source_path = source['path']
        
        # Read document content - check for inline content first
        if 'content' in source and source['content']:
            # Use inline content if provided
            content = source['content'].encode('utf-8')
        elif source_path.startswith('s3://'):
            content = self._read_s3_document(source_path)
        else:
            content = self._read_local_document(source_path)
        
        # Extract text based on document type
        extracted_text = self._extract_text(content, doc_type)
        
        # Generate version hash
        version_hash = hashlib.sha256(extracted_text.encode('utf-8')).hexdigest()
        
        # Create document metadata as plain dictionary
        doc_metadata = {
            "document_id": f"{execution_id}_{version_hash[:8]}",
            "document_type": doc_type,
            "source_path": source_path,
            "processed_at": datetime.utcnow().isoformat(),
            "version_hash": version_hash,
            "size_bytes": len(extracted_text.encode('utf-8')),
            "lineage": []
        }
        
        # Store processed content
        processed_key = f"processed/{execution_id}/{doc_metadata['document_id']}.txt"
        self._store_processed_content(extracted_text, processed_key)
        
        # Store metadata
        self._store_metadata(doc_metadata)
        
        return doc_metadata
    
    def _read_s3_document(self, s3_path: str) -> bytes:
        """Read document from S3."""
        # Parse s3://bucket/key format
        parts = s3_path.replace('s3://', '').split('/', 1)
        bucket, key = parts[0], parts[1]
        
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    
    def _read_local_document(self, file_path: str) -> bytes:
        """Read document from local filesystem."""
        with open(file_path, 'rb') as f:
            return f.read()
    
    def _extract_text(self, content: bytes, doc_type: str) -> str:
        """
        Extract text content based on document type.
        
        Args:
            content: Raw document content
            doc_type: Type of document (string)
            
        Returns:
            Extracted text content
        """
        if doc_type == "pdf":
            return self._extract_pdf_text(content)
        elif doc_type == "json_transcript":
            return self._extract_json_transcript(content)
        elif doc_type == "email":
            return self._extract_email_text(content)
        elif doc_type == "chat_log":
            return self._extract_chat_text(content)
        elif doc_type == "text":
            return content.decode('utf-8')
        else:
            raise ValueError(f"Unsupported document type: {doc_type}")
    
    def _extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF content."""
        if pypdf is None:
            self.logger.error("pypdf not available - cannot extract PDF text")
            raise RuntimeError("PDF processing dependencies not installed")
        
        try:
            pdf_reader = pypdf.PdfReader(BytesIO(content))
            text_parts = []
            
            for page in pdf_reader.pages:
                text_parts.append(page.extract_text())
            
            extracted_text = '\n'.join(text_parts)
            self.logger.info(f"Successfully extracted {len(extracted_text)} characters from PDF")
            return extracted_text
        except Exception as e:
            self.logger.error(f"PDF extraction failed: {e}")
            raise
    
    def _extract_json_transcript(self, content: bytes) -> str:
        """Extract text from JSON transcript format."""
        try:
            data = json.loads(content.decode('utf-8'))
            
            # Handle different transcript formats
            if 'transcript' in data:
                return data['transcript']
            elif 'messages' in data:
                # Chat-style transcript
                messages = []
                for msg in data['messages']:
                    speaker = msg.get('speaker', 'Unknown')
                    text = msg.get('text', '')
                    messages.append(f"{speaker}: {text}")
                return '\n'.join(messages)
            else:
                return json.dumps(data, indent=2)
                
        except Exception as e:
            self.logger.error(f"JSON transcript extraction failed: {e}")
            raise
    
    def _extract_email_text(self, content: bytes) -> str:
        """Extract text from email content."""
        # Basic email parsing - could be enhanced with email library
        return content.decode('utf-8', errors='ignore')
    
    def _extract_chat_text(self, content: bytes) -> str:
        """Extract text from chat log content."""
        return content.decode('utf-8', errors='ignore')
    
    def _store_processed_content(self, content: str, key: str) -> None:
        """Store processed content in S3."""
        s3_client.put_object(
            Bucket=PROCESSED_BUCKET,
            Key=key,
            Body=content.encode('utf-8'),
            ContentType='text/plain'
        )
    
    def _read_processed_content(self, key: str) -> str:
        """Read processed content from S3."""
        try:
            response = s3_client.get_object(Bucket=PROCESSED_BUCKET, Key=key)
            content = response['Body'].read().decode('utf-8')
            self.logger.info(f"Read processed content from s3://{PROCESSED_BUCKET}/{key} ({len(content)} characters)")
            return content
        except Exception as e:
            self.logger.error(f"Failed to read processed content from {key}: {e}")
            raise
    
    def _store_metadata(self, metadata: Dict[str, Any]) -> None:
        """Store document metadata in DynamoDB."""
        try:
            self.metadata_table.put_item(
                Item={
                    'document_id': metadata['document_id'],
                    'document_type': metadata['document_type'],
                    'source_path': metadata['source_path'],
                    'processed_at': metadata['processed_at'],
                    'version_hash': metadata['version_hash'],
                    'size_bytes': metadata['size_bytes'],
                    'lineage': metadata['lineage']
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to store metadata: {e}")
            raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for document processing.
    
    Args:
        event: Lambda event containing input documents
        context: Lambda context
        
    Returns:
        Processing results with document metadata
    """
    # Generate execution ID
    execution_id = f"doc_proc_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{context.aws_request_id[:8] if context else 'local'}"
    
    logger.info(f"Starting document processing with execution_id: {execution_id}")
    logger.info(f"Received event: {json.dumps(event, default=str)}")
    
    try:
        # Handle both Step Functions input and direct lambda input
        input_sources = event.get('input_sources', [])
        
        if not input_sources:
            # Step Functions format - create input_sources from document_content
            document_content = event.get('document_content', '')
            document_url = event.get('document_url', '')
            project_metadata = event.get('project_metadata', {})
            
            if document_content or document_url:
                # Determine document type based on content or metadata
                doc_type = 'text'
                content_path = document_content or document_url or 'step-functions-input'
                
                # Check project metadata for document type hints
                if project_metadata and project_metadata.get('source') == 'pdf-document':
                    doc_type = 'pdf'
                elif content_path.lower().endswith('.pdf') or 'pdf' in content_path.lower():
                    doc_type = 'pdf'
                elif content_path.lower().endswith('.json'):
                    doc_type = 'json_transcript'
                
                # For S3 paths, don't include content - let the processor read from S3
                if content_path.startswith('s3://'):
                    input_sources = [{
                        'type': doc_type,
                        'path': content_path,
                        'metadata': project_metadata
                    }]
                else:
                    input_sources = [{
                        'type': doc_type,
                        'content': document_content,
                        'path': content_path,
                        'metadata': project_metadata
                    }]
            else:
                raise ValueError("No input sources or document content provided")
        
        project_id = event.get('project_id') or event.get('project_metadata', {}).get('project_id', 'unknown')
        
        # Use DocumentProcessor class for proper document processing
        processor = DocumentProcessor()
        processed_docs = processor.process_documents(input_sources, execution_id)
        
        # Convert processed documents to the expected format
        processed_docs_formatted = []
        for doc in processed_docs:
            # Instead of including full content, just add S3 path reference
            # This prevents Step Functions payload size errors
            doc['content_path'] = f"s3://{processor.processed_bucket}/processed/{execution_id}/{doc['document_id']}.txt"
            # Keep a small preview for logging/debugging (first 200 chars)
            processed_content = processor._read_processed_content(f"processed/{execution_id}/{doc['document_id']}.txt")
            doc['content_preview'] = processed_content[:200] if processed_content else ""
            processed_docs_formatted.append(doc)
        processed_docs = processed_docs_formatted
        
        # Create pipeline context as plain dictionary
        pipeline_context = {
            "execution_id": execution_id,
            "project_id": project_id,
            "stage": "document_processing",
            "processed_documents": processed_docs,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Prepare response as plain dictionary
        response = {
            "status": "success",
            "message": f"Processed {len(processed_docs)} documents successfully",
            "execution_id": execution_id,
            "stage": "document_processing",
            "project_id": project_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "processed_documents": processed_docs,
                "pipeline_context": pipeline_context
            },
            "next_stage": "requirements_synthesis"
        }
        
        logger.info(f"Document processing completed successfully for execution_id: {execution_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error in document processing: {str(e)}", exc_info=True)
        
        # Return proper error status - raise exception for Step Functions to handle
        error_msg = f"Document processing failed: {str(e)}"
        raise RuntimeError(error_msg)