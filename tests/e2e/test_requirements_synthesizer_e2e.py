"""
End-to-end tests for requirements synthesizer lambda.
Tests the complete workflow: Processed documents -> User stories -> Prioritized requirements.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from shared.models.pipeline_models import (
    DocumentMetadata, DocumentType, UserStory, StoryStatus, 
    PipelineContext, LambdaResponse
)


class TestRequirementsSynthesizerE2E:
    """End-to-end tests for requirements synthesizer workflow."""
    
    @pytest.fixture
    def sample_processed_documents(self) -> List[DocumentMetadata]:
        """Create sample processed documents for testing."""
        return [
            DocumentMetadata(
                document_id="doc-1",
                document_type=DocumentType.TEXT,
                source_path="requirements.txt",
                processed_at=datetime.utcnow(),
                version_hash="hash123",
                size_bytes=1024
            ),
            DocumentMetadata(
                document_id="doc-2", 
                document_type=DocumentType.PDF,
                source_path="user_interviews.pdf",
                processed_at=datetime.utcnow(),
                version_hash="hash456",
                size_bytes=2048
            )
        ]
    
    @pytest.fixture
    def pipeline_context(self, sample_processed_documents: List[DocumentMetadata]) -> PipelineContext:
        """Create pipeline context from document processing stage."""
        return PipelineContext(
            execution_id="test-exec-123",
            project_id="test-project-456",
            stage="document_processing",
            input_documents=sample_processed_documents,
            metadata={
                "original_request": {
                    "project_type": "web_application",
                    "complexity": "medium"
                }
            }
        )
    
    @pytest.fixture
    def lambda_event(self, pipeline_context: PipelineContext) -> Dict[str, Any]:
        """Create lambda event for requirements synthesizer."""
        return {
            "data": {
                "pipeline_context": pipeline_context.dict()
            },
            "execution_id": "test-exec-123"
        }
    
    @pytest.fixture 
    def mock_anthropic_service(self):
        """Mock Anthropic service for requirements synthesis."""
        with patch('shared.services.anthropic_service.AnthropicService') as mock:
            service_mock = Mock()
            
            # Mock user story extraction response
            user_stories_response = json.dumps({
                "user_stories": [
                    {
                        "title": "User Registration",
                        "description": "As a new user, I want to create an account so that I can access the application",
                        "acceptance_criteria": [
                            "User can enter email and password",
                            "System validates email format",
                            "User receives confirmation email",
                            "Account is created in database"
                        ],
                        "priority": 1,
                        "estimated_effort": 5,
                        "dependencies": [],
                        "category": "authentication"
                    },
                    {
                        "title": "User Login", 
                        "description": "As a registered user, I want to login so that I can access my account",
                        "acceptance_criteria": [
                            "User can enter credentials",
                            "System validates credentials",
                            "User is redirected to dashboard on success",
                            "Error message shown for invalid credentials"
                        ],
                        "priority": 2,
                        "estimated_effort": 3,
                        "dependencies": ["User Registration"],
                        "category": "authentication"
                    },
                    {
                        "title": "Password Reset",
                        "description": "As a user, I want to reset my password if I forget it",
                        "acceptance_criteria": [
                            "User can request password reset",
                            "Reset link sent to email",
                            "User can set new password via link",
                            "Old password is invalidated"
                        ],
                        "priority": 3,
                        "estimated_effort": 4,
                        "dependencies": ["User Registration"],
                        "category": "authentication"
                    },
                    {
                        "title": "User Dashboard",
                        "description": "As a logged-in user, I want to see a dashboard with my information",
                        "acceptance_criteria": [
                            "Dashboard shows user profile",
                            "Dashboard shows recent activity", 
                            "User can navigate to other features",
                            "Dashboard loads within 2 seconds"
                        ],
                        "priority": 2,
                        "estimated_effort": 8,
                        "dependencies": ["User Login"],
                        "category": "user_interface"
                    }
                ]
            })
            
            service_mock.generate_text.return_value = user_stories_response
            mock.return_value = service_mock
            yield service_mock
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client for reading processed documents."""
        with patch('boto3.client') as mock:
            s3_mock = Mock()
            mock.return_value = s3_mock
            
            # Mock document content retrieval
            def mock_get_object(**kwargs):
                key = kwargs['Key']
                if 'doc-1' in key:
                    content = """
                    User Authentication Requirements:
                    - Users need to register with email/password
                    - Users need to login to access features
                    - Password reset functionality required
                    - Dashboard should show user information
                    """
                elif 'doc-2' in key:
                    content = """
                    User Interview Notes:
                    - Users want simple registration process
                    - Login should be quick and secure
                    - Forgot password is essential feature
                    - Dashboard should be personalized
                    """
                else:
                    content = "Generic document content"
                    
                return {
                    "Body": Mock(read=lambda: content.encode('utf-8'))
                }
            
            s3_mock.get_object.side_effect = mock_get_object
            yield s3_mock
    
    @pytest.fixture
    def mock_dynamodb_table(self):
        """Mock DynamoDB table for storing user stories."""
        with patch('boto3.resource') as mock:
            table_mock = Mock()
            mock.return_value.Table.return_value = table_mock
            
            # Mock successful batch write
            table_mock.batch_write_item.return_value = {
                "ResponseMetadata": {"HTTPStatusCode": 200}
            }
            yield table_mock

    @patch.dict('os.environ', {
        'PROCESSED_BUCKET_NAME': 'test-processed-bucket',
        'USER_STORIES_TABLE': 'test-user-stories-table',
        'ANTHROPIC_API_KEY': 'test-api-key'
    })
    def test_requirements_synthesizer_e2e_success(
        self,
        lambda_event: Dict[str, Any],
        mock_anthropic_service: Mock,
        mock_s3_client: Mock,
        mock_dynamodb_table: Mock
    ):
        """
        Test complete requirements synthesis workflow.
        
        Expected flow:
        1. Lambda receives pipeline context with processed documents
        2. Processed documents are retrieved from S3
        3. Document content is sent to Anthropic for story extraction
        4. User stories are parsed and validated
        5. Stories are prioritized and dependencies mapped
        6. Stories are stored in DynamoDB
        7. Updated pipeline context returned for next stage
        """
        from lambdas.core.requirements_synthesizer.lambda_function import lambda_handler
        
        # Execute lambda handler
        result = lambda_handler(lambda_event, Mock())
        
        # Verify response structure
        assert result["status"] == "success"
        assert result["stage"] == "requirements_synthesis" 
        assert result["next_stage"] == "architecture_planning"
        assert "execution_id" in result
        
        # Verify user stories in response
        assert "data" in result
        assert "user_stories" in result["data"]
        user_stories = result["data"]["user_stories"]
        assert len(user_stories) == 4
        
        # Verify user story structure and content
        registration_story = next(
            (story for story in user_stories if story["title"] == "User Registration"), 
            None
        )
        assert registration_story is not None
        assert registration_story["priority"] == 1
        assert registration_story["estimated_effort"] == 5
        assert len(registration_story["acceptance_criteria"]) == 4
        assert registration_story["status"] == StoryStatus.PENDING.value
        
        # Verify dependencies are correctly mapped
        login_story = next(
            (story for story in user_stories if story["title"] == "User Login"),
            None
        )
        assert login_story is not None
        assert "User Registration" in login_story["dependencies"]
        
        # Verify pipeline context is updated
        assert "pipeline_context" in result["data"]
        updated_context = result["data"]["pipeline_context"]
        assert updated_context["stage"] == "requirements_synthesis"
        assert len(updated_context["input_documents"]) == 2  # Original documents preserved
        
        # Verify S3 calls to retrieve document content
        assert mock_s3_client.get_object.call_count == 2
        s3_calls = [call[1] for call in mock_s3_client.get_object.call_args_list]
        assert any('doc-1' in call['Key'] for call in s3_calls)
        assert any('doc-2' in call['Key'] for call in s3_calls)
        
        # Verify Anthropic API call for story extraction
        mock_anthropic_service.generate_text.assert_called_once()
        api_call = mock_anthropic_service.generate_text.call_args[1]
        assert api_call["task_type"] == "requirements_synthesis"
        assert "extract user stories" in api_call["prompt"].lower()
        
        # Verify DynamoDB storage
        mock_dynamodb_table.batch_write_item.assert_called_once()

    def test_requirements_synthesizer_story_prioritization(
        self,
        lambda_event: Dict[str, Any],
        mock_anthropic_service: Mock, 
        mock_s3_client: Mock,
        mock_dynamodb_table: Mock
    ):
        """Test that user stories are properly prioritized and dependencies mapped."""
        from lambdas.core.requirements_synthesizer.lambda_function import lambda_handler
        
        result = lambda_handler(lambda_event, Mock())
        
        user_stories = result["data"]["user_stories"]
        
        # Verify priority ordering
        priorities = [story["priority"] for story in user_stories]
        assert 1 in priorities  # High priority stories exist
        assert max(priorities) <= 3  # Reasonable priority range
        
        # Verify dependency mapping
        story_titles = [story["title"] for story in user_stories]
        for story in user_stories:
            for dependency in story["dependencies"]:
                assert dependency in story_titles, f"Dependency '{dependency}' not found in story list"

    def test_requirements_synthesizer_story_validation(
        self,
        lambda_event: Dict[str, Any],
        mock_anthropic_service: Mock,
        mock_s3_client: Mock,
        mock_dynamodb_table: Mock
    ):
        """Test that generated user stories pass validation."""
        from lambdas.core.requirements_synthesizer.lambda_function import lambda_handler
        
        result = lambda_handler(lambda_event, Mock())
        
        user_stories = result["data"]["user_stories"]
        
        # Verify each story has required fields
        required_fields = ["title", "description", "acceptance_criteria", "priority", "estimated_effort"]
        for story in user_stories:
            for field in required_fields:
                assert field in story, f"Story missing required field: {field}"
                assert story[field] is not None, f"Story field '{field}' is None"
            
            # Verify acceptance criteria is a list with content
            assert isinstance(story["acceptance_criteria"], list)
            assert len(story["acceptance_criteria"]) > 0
            
            # Verify priority and effort are reasonable
            assert 1 <= story["priority"] <= 5
            assert 1 <= story["estimated_effort"] <= 20

    def test_requirements_synthesizer_error_handling(self):
        """Test error handling when story extraction fails."""
        # Event with missing pipeline context
        event = {
            "data": {},
            "execution_id": "test-error-exec"
        }
        
        from lambdas.core.requirements_synthesizer.lambda_function import lambda_handler
        
        result = lambda_handler(event, Mock())
        
        # Verify error response
        assert result["status"] == "failed"
        assert "error" in result
        assert result["stage"] == "requirements_synthesis"

    @patch.dict('os.environ', {
        'PROCESSED_BUCKET_NAME': 'test-processed-bucket',
        'USER_STORIES_TABLE': 'test-user-stories-table', 
        'ANTHROPIC_API_KEY': 'test-api-key'
    })
    def test_requirements_synthesizer_handles_anthropic_failure(
        self,
        lambda_event: Dict[str, Any],
        mock_s3_client: Mock,
        mock_dynamodb_table: Mock
    ):
        """Test handling when Anthropic API fails."""
        with patch('shared.services.anthropic_service.AnthropicService') as mock:
            service_mock = Mock()
            service_mock.generate_text.side_effect = Exception("Anthropic API error")
            mock.return_value = service_mock
            
            from lambdas.core.requirements_synthesizer.lambda_function import lambda_handler
            
            result = lambda_handler(lambda_event, Mock())
            
            # Verify error handling
            assert result["status"] == "failed"
            assert "Anthropic API error" in result["error"]

    @patch.dict('os.environ', {
        'PROCESSED_BUCKET_NAME': 'test-processed-bucket', 
        'USER_STORIES_TABLE': 'test-user-stories-table',
        'ANTHROPIC_API_KEY': 'test-api-key'
    })
    def test_requirements_synthesizer_handles_s3_failure(
        self,
        lambda_event: Dict[str, Any],
        mock_anthropic_service: Mock,
        mock_dynamodb_table: Mock
    ):
        """Test handling when S3 document retrieval fails."""
        with patch('boto3.client') as mock:
            s3_mock = Mock()
            s3_mock.get_object.side_effect = Exception("S3 access denied")
            mock.return_value = s3_mock
            
            from lambdas.core.requirements_synthesizer.lambda_function import lambda_handler
            
            result = lambda_handler(lambda_event, Mock())
            
            # Verify error handling
            assert result["status"] == "failed"
            assert "S3 access denied" in result["error"]

    def test_requirements_synthesizer_creates_story_ids(
        self,
        lambda_event: Dict[str, Any], 
        mock_anthropic_service: Mock,
        mock_s3_client: Mock,
        mock_dynamodb_table: Mock
    ):
        """Test that unique story IDs are generated for each user story."""
        from lambdas.core.requirements_synthesizer.lambda_function import lambda_handler
        
        result = lambda_handler(lambda_event, Mock())
        
        user_stories = result["data"]["user_stories"]
        
        # Verify each story has unique ID
        story_ids = [story["story_id"] for story in user_stories]
        assert len(story_ids) == len(set(story_ids)), "Story IDs are not unique"
        
        # Verify ID format
        for story_id in story_ids:
            assert isinstance(story_id, str)
            assert len(story_id) > 0
            # Should include execution_id for traceability
            assert lambda_event["execution_id"] in story_id

    def test_requirements_synthesizer_preserves_document_lineage(
        self,
        lambda_event: Dict[str, Any],
        mock_anthropic_service: Mock, 
        mock_s3_client: Mock,
        mock_dynamodb_table: Mock
    ):
        """Test that document lineage is preserved through requirements synthesis."""
        from lambdas.core.requirements_synthesizer.lambda_function import lambda_handler
        
        result = lambda_handler(lambda_event, Mock())
        
        # Verify original documents are preserved in pipeline context
        updated_context = result["data"]["pipeline_context"]
        original_docs = lambda_event["data"]["pipeline_context"]["input_documents"]
        preserved_docs = updated_context["input_documents"]
        
        assert len(preserved_docs) == len(original_docs)
        
        # Verify document metadata is preserved
        for i, doc in enumerate(preserved_docs):
            assert doc["document_id"] == original_docs[i]["document_id"]
            assert doc["version_hash"] == original_docs[i]["version_hash"]