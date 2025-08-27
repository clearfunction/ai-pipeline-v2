"""
End-to-end tests for document processor lambda.
Tests the complete workflow: Input documents -> Processed content -> S3 storage -> Metadata.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch
from typing import Dict, Any

from shared.models.pipeline_models import (
    DocumentType, DocumentMetadata, PipelineContext, LambdaResponse
)


class TestDocumentProcessorE2E:
    """End-to-end tests for document processor workflow."""
    
    @pytest.fixture
    def sample_text_document(self) -> str:
        """Create a sample text document for testing."""
        return """
        # Product Requirements Document
        
        ## Overview
        Build a user authentication system for our web application.
        
        ## User Stories
        - As a user, I want to register with email/password
        - As a user, I want to login with my credentials
        - As a user, I want to reset my password if forgotten
        
        ## Technical Requirements
        - Use JWT tokens for session management
        - Implement rate limiting for login attempts
        - Store passwords securely with bcrypt hashing
        """
    
    @pytest.fixture
    def sample_pdf_content(self) -> bytes:
        """Create sample PDF content for testing."""
        # In a real implementation, this would be actual PDF bytes
        # For now, return text that simulates PDF extraction
        return b"PDF content: User wants to create a task management system with drag-and-drop functionality."
    
    @pytest.fixture  
    def lambda_event(self, sample_text_document: str) -> Dict[str, Any]:
        """Create a valid lambda event for document processing."""
        # Create temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(sample_text_document)
            temp_path = f.name
        
        return {
            "input_sources": [
                {
                    "type": "text",
                    "path": temp_path,
                    "metadata": {
                        "source_name": "product_requirements.txt",
                        "upload_time": datetime.utcnow().isoformat()
                    }
                }
            ],
            "project_id": "test-project-123",
            "execution_id": "test-exec-456"
        }
    
    @pytest.fixture
    def mock_anthropic_service(self):
        """Mock Anthropic service for testing."""
        with patch('shared.services.anthropic_service.AnthropicService') as mock:
            # Mock successful text extraction enhancement (if needed)
            mock.return_value.enhance_text_extraction.return_value = "Enhanced extracted text"
            yield mock.return_value
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client for testing."""
        with patch('boto3.client') as mock:
            s3_mock = Mock()
            mock.return_value = s3_mock
            # Mock successful S3 operations
            s3_mock.put_object.return_value = {"ETag": "test-etag"}
            s3_mock.get_object.return_value = {
                "Body": Mock(read=lambda: b"test content")
            }
            yield s3_mock
    
    @pytest.fixture
    def mock_dynamodb_table(self):
        """Mock DynamoDB table for testing."""
        with patch('boto3.resource') as mock:
            dynamodb_mock = Mock()
            table_mock = Mock()
            mock.return_value.Table.return_value = table_mock
            # Mock successful DynamoDB operations
            table_mock.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
            yield table_mock

    @patch.dict(os.environ, {
        'RAW_BUCKET_NAME': 'test-raw-bucket',
        'PROCESSED_BUCKET_NAME': 'test-processed-bucket', 
        'DOCUMENT_METADATA_TABLE': 'test-metadata-table',
        'ANTHROPIC_API_KEY': 'test-api-key'
    })
    def test_document_processor_text_file_e2e(
        self, 
        lambda_event: Dict[str, Any],
        mock_anthropic_service: Mock,
        mock_s3_client: Mock,
        mock_dynamodb_table: Mock
    ):
        """
        Test complete document processing workflow for text file.
        
        Expected flow:
        1. Lambda receives event with document source
        2. Document is read and processed  
        3. Content is stored in S3 processed bucket
        4. Metadata is stored in DynamoDB
        5. Pipeline context is created for next stage
        6. Success response is returned
        """
        # Import here to ensure environment variables are set
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'document-processor'))
        from lambda_function import lambda_handler
        
        # Execute lambda handler
        result = lambda_handler(lambda_event, Mock())
        
        # Verify response structure
        assert result["status"] == "success"
        assert "execution_id" in result
        assert result["stage"] == "document_processing"
        assert result["next_stage"] == "requirements_synthesis"
        
        # Verify processed documents in response
        assert "data" in result
        assert "processed_documents" in result["data"]
        processed_docs = result["data"]["processed_documents"]
        assert len(processed_docs) == 1
        
        # Verify document metadata structure
        doc = processed_docs[0]
        assert doc["document_type"] == DocumentType.TEXT.value
        assert doc["size_bytes"] > 0
        assert "version_hash" in doc
        assert "document_id" in doc
        
        # Verify pipeline context is created
        assert "pipeline_context" in result["data"]
        context = result["data"]["pipeline_context"]
        assert context["project_id"] == "test-project-123"
        assert context["stage"] == "document_processing"
        assert len(context["input_documents"]) == 1
        
        # Verify S3 operations were called
        mock_s3_client.put_object.assert_called()
        put_call = mock_s3_client.put_object.call_args
        assert put_call[1]["Bucket"] == "test-processed-bucket"
        assert "processed/" in put_call[1]["Key"]
        
        # Verify DynamoDB operations were called  
        mock_dynamodb_table.put_item.assert_called()
        put_item_call = mock_dynamodb_table.put_item.call_args[1]["Item"]
        assert put_item_call["document_type"] == DocumentType.TEXT.value
        assert "version_hash" in put_item_call

    @patch.dict(os.environ, {
        'RAW_BUCKET_NAME': 'test-raw-bucket',
        'PROCESSED_BUCKET_NAME': 'test-processed-bucket',
        'DOCUMENT_METADATA_TABLE': 'test-metadata-table', 
        'ANTHROPIC_API_KEY': 'test-api-key'
    })
    def test_document_processor_pdf_file_e2e(
        self,
        mock_anthropic_service: Mock,
        mock_s3_client: Mock, 
        mock_dynamodb_table: Mock,
        sample_pdf_content: bytes
    ):
        """Test complete document processing workflow for PDF file."""
        # Create event with PDF source
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
            f.write(sample_pdf_content)
            pdf_path = f.name
        
        event = {
            "input_sources": [
                {
                    "type": "pdf",
                    "path": pdf_path,
                    "metadata": {
                        "source_name": "requirements.pdf",
                        "upload_time": datetime.utcnow().isoformat()
                    }
                }
            ],
            "project_id": "test-pdf-project"
        }
        
        from lambdas.core.document_processor.lambda_function import lambda_handler
        
        # Execute lambda handler
        result = lambda_handler(event, Mock())
        
        # Verify PDF processing
        assert result["status"] == "success"
        processed_docs = result["data"]["processed_documents"]
        assert len(processed_docs) == 1
        assert processed_docs[0]["document_type"] == DocumentType.PDF.value

    def test_document_processor_error_handling(self):
        """Test error handling when document processing fails."""
        # Event with invalid document path
        event = {
            "input_sources": [
                {
                    "type": "text", 
                    "path": "/nonexistent/file.txt"
                }
            ],
            "project_id": "test-error-project"
        }
        
        from lambdas.core.document_processor.lambda_function import lambda_handler
        
        # Execute lambda handler
        result = lambda_handler(event, Mock())
        
        # Verify error response
        assert result["status"] == "failed" 
        assert "error" in result
        assert result["stage"] == "document_processing"

    def test_document_processor_multiple_documents(
        self,
        mock_anthropic_service: Mock,
        mock_s3_client: Mock,
        mock_dynamodb_table: Mock
    ):
        """Test processing multiple documents in single request."""
        # Create multiple temporary files
        text_content = "Text document content for user stories"
        pdf_content = b"PDF document content for technical specs"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as text_file:
            text_file.write(text_content)
            text_path = text_file.name
            
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as pdf_file:
            pdf_file.write(pdf_content) 
            pdf_path = pdf_file.name
        
        event = {
            "input_sources": [
                {"type": "text", "path": text_path},
                {"type": "pdf", "path": pdf_path}
            ],
            "project_id": "test-multi-project"
        }
        
        from lambdas.core.document_processor.lambda_function import lambda_handler
        
        result = lambda_handler(event, Mock())
        
        # Verify both documents processed
        assert result["status"] == "success"
        processed_docs = result["data"]["processed_documents"]
        assert len(processed_docs) == 2
        
        # Verify different document types
        doc_types = [doc["document_type"] for doc in processed_docs]
        assert DocumentType.TEXT.value in doc_types
        assert DocumentType.PDF.value in doc_types
        
        # Cleanup temp files
        os.unlink(text_path)
        os.unlink(pdf_path)

    def test_document_processor_creates_pipeline_context(
        self,
        lambda_event: Dict[str, Any], 
        mock_anthropic_service: Mock,
        mock_s3_client: Mock,
        mock_dynamodb_table: Mock
    ):
        """Test that document processor creates proper pipeline context for next stage."""
        from lambdas.core.document_processor.lambda_function import lambda_handler
        
        result = lambda_handler(lambda_event, Mock())
        
        # Verify pipeline context structure
        context = result["data"]["pipeline_context"] 
        
        # Required fields for pipeline context
        assert context["execution_id"] is not None
        assert context["project_id"] == "test-project-123"
        assert context["stage"] == "document_processing"
        assert isinstance(context["input_documents"], list)
        assert len(context["input_documents"]) > 0
        assert "created_at" in context
        
        # Verify input documents have required metadata
        doc = context["input_documents"][0]
        required_fields = ["document_id", "document_type", "source_path", 
                          "processed_at", "version_hash", "size_bytes"]
        for field in required_fields:
            assert field in doc, f"Missing required field: {field}"