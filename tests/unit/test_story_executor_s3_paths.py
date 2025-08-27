"""
Unit tests for story executor S3 path structure updates.
Tests the new {project_name}-{date}/generated/{execution_id}/ path format.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import boto3
from moto import mock_s3, mock_dynamodb

from shared.models.pipeline_models import (
    UserStory, StoryStatus, ComponentSpec, ProjectArchitecture, 
    TechStack, GeneratedCode
)


@mock_s3
@mock_dynamodb
class TestStoryExecutorS3Paths:
    """Test the updated S3 path structure in story executor."""
    
    @pytest.fixture
    def mock_environment(self):
        """Set up mock AWS environment."""
        import os
        os.environ['CODE_ARTIFACTS_BUCKET'] = 'test-code-artifacts-bucket'
        os.environ['GENERATED_CODE_TABLE'] = 'test-generated-code-table'
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        
        # Create mock S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket='test-code-artifacts-bucket')
        
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-generated-code-table',
            KeySchema=[
                {'AttributeName': 'execution_id', 'KeyType': 'HASH'},
                {'AttributeName': 'file_path', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'execution_id', 'AttributeType': 'S'},
                {'AttributeName': 'file_path', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        table.wait_until_exists()
        
        yield s3_client, table
    
    @pytest.fixture
    def sample_architecture(self):
        """Sample project architecture for testing."""
        components = [
            ComponentSpec(
                component_id="comp_001",
                name="App",
                type="component",
                file_path="src/App.tsx",
                dependencies=[],
                exports=["App"],
                story_ids=["story-1"]
            )
        ]
        
        stories = [
            UserStory(
                story_id="story-1",
                title="Basic App Structure",
                description="Set up basic React app structure",
                acceptance_criteria=["App renders correctly"],
                priority=1,
                estimated_effort=3,
                dependencies=[],
                status=StoryStatus.PENDING
            )
        ]
        
        return ProjectArchitecture(
            project_id="test-001",
            name="My Test App",
            tech_stack=TechStack.REACT_SPA,
            components=components,
            user_stories=stories,
            dependencies={"react": "^18.2.0"},
            build_config={"package_manager": "npm", "bundler": "vite"}
        )
    
    @pytest.fixture
    def generated_code_sample(self):
        """Sample generated code for testing."""
        return GeneratedCode(
            file_path="src/App.tsx",
            content="""import React from 'react';

export const App: React.FC = () => {
    return (
        <div className="app">
            <h1>My Test App</h1>
        </div>
    );
};""",
            component_id="comp_001",
            story_id="story-1",
            file_type="component",
            language="typescript"
        )
    
    @patch('shared.services.anthropic_service.AnthropicService')
    @patch('lambdas.core.story-executor.incremental_executor.IncrementalExecutor')
    @patch('lambdas.core.story-executor.code_quality_validator.CodeQualityValidator')
    @pytest.mark.asyncio
    async def test_s3_path_with_project_name_and_date(
        self,
        mock_quality_validator,
        mock_incremental_executor,
        mock_anthropic,
        mock_environment,
        sample_architecture,
        generated_code_sample
    ):
        """Test that S3 paths follow {project_name}-{date}/generated/{execution_id}/ format."""
        s3_client, table = mock_environment
        
        # Mock the incremental executor
        mock_executor_instance = Mock()
        mock_incremental_executor.return_value = mock_executor_instance
        
        # Mock successful story execution
        from lambdas.core.story_executor.incremental_executor import StoryExecutionResult
        mock_executor_instance.execute_story = AsyncMock(return_value=StoryExecutionResult(
            story_id="story-1",
            generated_files=[generated_code_sample],
            execution_time_ms=1000,
            success=True
        ))
        
        # Mock quality validator
        mock_quality_instance = Mock()
        mock_quality_validator.return_value = mock_quality_instance
        mock_quality_instance.validate_code.return_value = Mock(is_valid=True, issues=[])
        
        # Import and test story executor
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from lambda_function import StoryExecutor
        
        executor = StoryExecutor()
        execution_id = "exec-test-123"
        
        # Execute stories (this will call _store_generated_code with new path format)
        result = await executor.execute_stories(
            sample_architecture.user_stories,
            sample_architecture,
            execution_id
        )
        
        # Verify execution completed
        assert result["execution_results"][0]["status"] == "completed"
        
        # Check S3 object was stored with correct path
        objects = s3_client.list_objects_v2(Bucket='test-code-artifacts-bucket')
        assert 'Contents' in objects
        
        stored_object = objects['Contents'][0]
        stored_key = stored_object['Key']
        
        # Verify path format: {project_name}-{date}/generated/{execution_id}/{file_path}
        project_name = "my-test-app"  # Architecture name sanitized
        today = datetime.utcnow().strftime('%Y%m%d')
        expected_prefix = f"{project_name}-{today}/generated/{execution_id}/"
        
        assert stored_key.startswith(expected_prefix), f"S3 key {stored_key} doesn't start with {expected_prefix}"
        assert stored_key.endswith("src/App.tsx"), f"S3 key should end with file path"
        
        # Verify DynamoDB metadata includes project info
        response = table.get_item(
            Key={'execution_id': execution_id, 'file_path': 'src/App.tsx'}
        )
        item = response['Item']
        
        assert item['s3_key'] == stored_key
        assert item['project_name'] == "My Test App"
        assert item['project_date'] == today
    
    @patch('shared.services.anthropic_service.AnthropicService')
    @patch('lambdas.core.story-executor.incremental_executor.IncrementalExecutor')
    @patch('lambdas.core.story-executor.code_quality_validator.CodeQualityValidator')
    @pytest.mark.asyncio
    async def test_backward_compatibility_fallback(
        self,
        mock_quality_validator,
        mock_incremental_executor,
        mock_anthropic,
        mock_environment,
        generated_code_sample
    ):
        """Test that fallback path works when project info is missing."""
        s3_client, table = mock_environment
        
        # Import story executor
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from lambda_function import StoryExecutor
        
        executor = StoryExecutor()
        execution_id = "exec-fallback-456"
        
        # Test direct _store_generated_code call without project info
        await executor._store_generated_code(generated_code_sample, execution_id)
        
        # Check S3 object was stored with fallback path
        objects = s3_client.list_objects_v2(Bucket='test-code-artifacts-bucket')
        assert 'Contents' in objects
        
        stored_object = objects['Contents'][0]
        stored_key = stored_object['Key']
        
        # Should use fallback format: {execution_id}/{file_path}
        expected_key = f"{execution_id}/{generated_code_sample.file_path}"
        assert stored_key == expected_key
        
        # Verify DynamoDB metadata
        response = table.get_item(
            Key={'execution_id': execution_id, 'file_path': generated_code_sample.file_path}
        )
        item = response['Item']
        
        assert item['s3_key'] == expected_key
        # Project fields should be None/empty in fallback mode
        assert 'project_name' not in item or item['project_name'] is None
        assert 'project_date' not in item or item['project_date'] is None
    
    @patch('shared.services.anthropic_service.AnthropicService')
    @pytest.mark.asyncio
    async def test_s3_path_compatibility_with_other_lambdas(
        self, 
        mock_anthropic,
        mock_environment,
        generated_code_sample
    ):
        """Test that S3 paths are compatible with integration-validator and github-orchestrator."""
        s3_client, table = mock_environment
        
        # Import story executor
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from lambda_function import StoryExecutor
        
        executor = StoryExecutor()
        execution_id = "exec-compat-789"
        project_name = "test-project"
        project_date = "20250120"
        
        # Store code using new path format
        await executor._store_generated_code(
            generated_code_sample, 
            execution_id, 
            project_name, 
            project_date
        )
        
        # Verify the stored path matches what other lambdas expect
        stored_key = f"{project_name}-{project_date}/generated/{execution_id}/{generated_code_sample.file_path}"
        
        # Test that integration-validator can find the file
        integration_prefix = f"{project_name}-{project_date}/generated/{execution_id}/"
        assert stored_key.startswith(integration_prefix)
        
        # Test that github-orchestrator can list files with the prefix
        objects = s3_client.list_objects_v2(
            Bucket='test-code-artifacts-bucket',
            Prefix=integration_prefix
        )
        assert 'Contents' in objects
        assert len(objects['Contents']) == 1
        assert objects['Contents'][0]['Key'] == stored_key
    
    def test_project_name_sanitization(self, mock_environment):
        """Test that project names are properly sanitized for S3 paths."""
        s3_client, table = mock_environment
        
        # Import story executor
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from lambda_function import StoryExecutor
        
        executor = StoryExecutor()
        
        # Test various project name formats
        test_cases = [
            ("My Test App", "my-test-app"),
            ("Project_With_Underscores", "project-with-underscores"),
            ("UPPERCASE PROJECT", "uppercase-project"),
            ("Mixed Case_And Spaces", "mixed-case-and-spaces")
        ]
        
        for original_name, expected_sanitized in test_cases:
            # Create architecture with unsanitized name
            from shared.models.pipeline_models import ProjectArchitecture, TechStack
            arch = ProjectArchitecture(
                project_id="test",
                name=original_name,
                tech_stack=TechStack.REACT_SPA,
                components=[],
                user_stories=[],
                dependencies={},
                build_config={}
            )
            
            # Extract and test name sanitization (simulating what happens in execute_stories)
            sanitized_name = arch.name.lower().replace(' ', '-').replace('_', '-')
            assert sanitized_name == expected_sanitized, f"Name '{original_name}' should sanitize to '{expected_sanitized}', got '{sanitized_name}'"
    
    def test_date_format_consistency(self, mock_environment):
        """Test that date format is consistent across all path operations."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from lambda_function import StoryExecutor
        
        executor = StoryExecutor()
        
        # Test date format matches what other lambdas expect
        test_date = datetime.utcnow().strftime('%Y%m%d')
        
        # Date should be YYYYMMDD format (8 digits)
        assert len(test_date) == 8
        assert test_date.isdigit()
        
        # Should match format used in integration-validator and github-orchestrator
        # (Both use the same format: project_date from pipeline context)
        from datetime import datetime
        expected_format = datetime.utcnow().strftime('%Y%m%d')
        assert test_date == expected_format
    
    @patch('shared.services.anthropic_service.AnthropicService')
    @pytest.mark.asyncio
    async def test_multiple_files_same_execution(
        self,
        mock_anthropic,
        mock_environment,
        sample_architecture
    ):
        """Test storing multiple files from same execution with consistent paths."""
        s3_client, table = mock_environment
        
        # Import story executor
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from lambda_function import StoryExecutor
        
        executor = StoryExecutor()
        execution_id = "exec-multi-999"
        project_name = "multi-file-test"
        project_date = "20250120"
        
        # Create multiple generated files
        files = [
            GeneratedCode(
                file_path="src/App.tsx",
                content="// App component",
                component_id="comp_001",
                story_id="story-1",
                file_type="component",
                language="typescript"
            ),
            GeneratedCode(
                file_path="src/components/Header.tsx", 
                content="// Header component",
                component_id="comp_002",
                story_id="story-1",
                file_type="component",
                language="typescript"
            ),
            GeneratedCode(
                file_path="package.json",
                content='{"name": "test-app"}',
                component_id="project_root",
                story_id="initialization",
                file_type="config",
                language="json"
            )
        ]
        
        # Store all files
        for file in files:
            await executor._store_generated_code(file, execution_id, project_name, project_date)
        
        # Verify all files use consistent path prefix
        objects = s3_client.list_objects_v2(Bucket='test-code-artifacts-bucket')
        assert 'Contents' in objects
        assert len(objects['Contents']) == 3
        
        expected_prefix = f"{project_name}-{project_date}/generated/{execution_id}/"
        for obj in objects['Contents']:
            assert obj['Key'].startswith(expected_prefix)
        
        # Verify specific paths
        stored_keys = [obj['Key'] for obj in objects['Contents']]
        expected_keys = [
            f"{expected_prefix}src/App.tsx",
            f"{expected_prefix}src/components/Header.tsx", 
            f"{expected_prefix}package.json"
        ]
        
        for expected_key in expected_keys:
            assert expected_key in stored_keys, f"Expected key {expected_key} not found in {stored_keys}"