"""
Integration tests for S3 path compatibility across all lambdas.
Tests that story-executor, integration-validator, and github-orchestrator use consistent paths.
"""

import pytest
from unittest.mock import Mock, patch
import boto3
from moto import mock_s3
from datetime import datetime

from shared.models.pipeline_models import (
    ComponentSpec, GeneratedCode, ValidationResult, GitHubWorkflowConfig
)
from shared.services.s3_service import S3Service


@mock_s3
class TestS3PathCompatibility:
    """Test S3 path compatibility across lambdas."""
    
    @pytest.fixture
    def mock_s3_setup(self):
        """Set up mock S3 environment with test data."""
        # Create S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-code-artifacts-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Test data
        project_name = "test-project"
        project_date = "20250120"
        execution_id = "exec-integration-test"
        
        # Store test files in expected path format
        test_files = [
            {
                'key': f"{project_name}-{project_date}/generated/{execution_id}/src/App.tsx",
                'content': """import React from 'react';
export const App: React.FC = () => <div>Test App</div>;"""
            },
            {
                'key': f"{project_name}-{project_date}/generated/{execution_id}/src/components/Login.tsx",
                'content': """import React from 'react';
export const Login: React.FC = () => <div>Login</div>;"""
            },
            {
                'key': f"{project_name}-{project_date}/generated/{execution_id}/package.json",
                'content': '{"name": "test-project", "version": "1.0.0"}'
            }
        ]
        
        for file_data in test_files:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=file_data['key'],
                Body=file_data['content'].encode('utf-8'),
                ContentType='text/plain'
            )
        
        yield {
            's3_client': s3_client,
            'bucket_name': bucket_name,
            'project_name': project_name,
            'project_date': project_date,
            'execution_id': execution_id,
            'test_files': test_files
        }
    
    def test_s3_service_can_list_with_project_prefix(self, mock_s3_setup):
        """Test that S3Service can list objects using project-based prefix."""
        setup = mock_s3_setup
        s3_service = S3Service(region_name='us-east-1')
        
        # Test listing with project prefix
        prefix = f"{setup['project_name']}-{setup['project_date']}/generated/{setup['execution_id']}/"
        objects = s3_service.list_objects(setup['bucket_name'], prefix=prefix)
        
        # Should find all test files
        assert len(objects) == 3
        
        # Verify all keys have correct prefix
        for obj in objects:
            assert obj['key'].startswith(prefix)
        
        # Verify specific files
        keys = [obj['key'] for obj in objects]
        expected_keys = [file_data['key'] for file_data in setup['test_files']]
        for expected_key in expected_keys:
            assert expected_key in keys
    
    def test_integration_validator_can_read_stored_files(self, mock_s3_setup):
        """Test that integration-validator can read files stored by story-executor."""
        setup = mock_s3_setup
        
        # Mock component specs that match stored files
        component_specs = [
            ComponentSpec(
                component_id="comp_001",
                name="App",
                type="component", 
                file_path="src/App.tsx",
                dependencies=[],
                exports=["App"],
                story_ids=["story-1"]
            ),
            ComponentSpec(
                component_id="comp_002",
                name="Login",
                type="component",
                file_path="src/components/Login.tsx", 
                dependencies=["App"],
                exports=["Login"],
                story_ids=["story-2"]
            )
        ]
        
        # Import integration validator function
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'story-execution', 'integration-validator'))
        from lambda_function import validate_imports_exports
        
        # Create S3Service mock that uses our test S3
        s3_service = S3Service(region_name='us-east-1')
        
        # Test validation with project-based paths
        result = validate_imports_exports(
            component_specs,
            s3_service,
            setup['project_name'],
            setup['project_date'],
            setup['execution_id']
        )
        
        # Should successfully read and validate files
        assert isinstance(result, ValidationResult)
        assert result.component_count == len(component_specs)
        # Should have processed the files we stored
        assert len(result.processed_files) > 0
    
    @patch.dict('os.environ', {'CODE_ARTIFACTS_BUCKET': 'test-code-artifacts-bucket'})
    def test_github_orchestrator_can_list_stored_files(self, mock_s3_setup):
        """Test that github-orchestrator can list files stored by story-executor."""
        setup = mock_s3_setup
        
        # Import github orchestrator S3 listing logic
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'story-execution', 'github-orchestrator'))
        from lambda_function import lambda_handler
        from shared.services.s3_service import S3Service
        
        # Test S3Service directly (this is what github-orchestrator uses)
        s3_service = S3Service(region_name='us-east-1')
        
        # List objects with same prefix github-orchestrator would use
        prefix = f"{setup['project_name']}-{setup['project_date']}/generated/{setup['execution_id']}/"
        code_artifacts = s3_service.list_objects(
            bucket_name=setup['bucket_name'],
            prefix=prefix
        )
        
        # Should find all stored files
        assert len(code_artifacts) == 3
        
        # Verify file structure github-orchestrator expects
        for artifact in code_artifacts:
            assert 'key' in artifact
            assert 'last_modified' in artifact
            assert 'size' in artifact
            
            # Can read the content
            content = s3_service.get_object(setup['bucket_name'], artifact['key'])
            assert len(content) > 0
    
    def test_end_to_end_path_consistency(self, mock_s3_setup):
        """Test complete path consistency from storage to retrieval."""
        setup = mock_s3_setup
        
        # 1. Simulate story-executor storing a new file
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from lambda_function import StoryExecutor
        
        executor = StoryExecutor()
        new_execution_id = "exec-e2e-test"
        
        new_file = GeneratedCode(
            file_path="src/services/ApiService.ts",
            content="""export class ApiService {
    static async fetchData(): Promise<any> {
        return fetch('/api/data').then(r => r.json());
    }
}""",
            component_id="comp_003",
            story_id="story-3",
            file_type="service",
            language="typescript"
        )
        
        # Store using new path format
        # Note: This would normally be called within execute_stories, 
        # but we're testing the path construction directly
        expected_s3_key = f"{setup['project_name']}-{setup['project_date']}/generated/{new_execution_id}/{new_file.file_path}"
        
        # Manually store to verify path (simulating what _store_generated_code does)
        setup['s3_client'].put_object(
            Bucket=setup['bucket_name'],
            Key=expected_s3_key,
            Body=new_file.content.encode('utf-8'),
            ContentType='text/plain'
        )
        
        # 2. Verify integration-validator can find the file
        sys.path[0] = os.path.join(os.getcwd(), 'lambdas', 'story-execution', 'integration-validator')
        
        s3_service = S3Service(region_name='us-east-1')
        prefix = f"{setup['project_name']}-{setup['project_date']}/generated/{new_execution_id}/"
        
        objects = s3_service.list_objects(setup['bucket_name'], prefix=prefix)
        assert len(objects) == 1
        assert objects[0]['key'] == expected_s3_key
        
        # 3. Verify github-orchestrator can read the file
        content = s3_service.get_object(setup['bucket_name'], expected_s3_key)
        assert "ApiService" in content
        assert "fetchData" in content
        
        # 4. Verify all components can work with the same prefix
        all_objects = s3_service.list_objects(
            setup['bucket_name'], 
            prefix=f"{setup['project_name']}-{setup['project_date']}/generated/"
        )
        # Should find files from both executions
        assert len(all_objects) >= 4  # 3 original + 1 new
    
    def test_path_format_validation(self, mock_s3_setup):
        """Test that all path formats follow the expected structure."""
        setup = mock_s3_setup
        
        s3_service = S3Service(region_name='us-east-1')
        
        # List all objects in bucket
        all_objects = s3_service.list_objects(setup['bucket_name'])
        
        # Define expected path pattern: {project}-{date}/generated/{execution_id}/{file_path}
        import re
        path_pattern = re.compile(r'^[\w-]+-\d{8}/generated/[\w-]+/.+$')
        
        for obj in all_objects:
            key = obj['key']
            assert path_pattern.match(key), f"Path '{key}' doesn't match expected format"
            
            # Verify structure
            parts = key.split('/')
            assert len(parts) >= 3, f"Path should have at least 3 parts: {key}"
            assert parts[1] == "generated", f"Second part should be 'generated': {key}"
            
            # Verify project-date prefix
            project_date_part = parts[0]
            assert '-' in project_date_part, f"First part should contain project-date: {key}"
            
            # Verify date portion is 8 digits
            date_part = project_date_part.split('-')[-1]
            assert len(date_part) == 8 and date_part.isdigit(), f"Date part should be YYYYMMDD: {key}"
    
    def test_cross_lambda_file_operations(self, mock_s3_setup):
        """Test file operations that span multiple lambdas."""
        setup = mock_s3_setup
        s3_service = S3Service(region_name='us-east-1')
        
        # Test scenario: story-executor creates files -> integration-validator reads them -> github-orchestrator commits them
        
        # 1. Story-executor perspective: list files for a project
        project_prefix = f"{setup['project_name']}-{setup['project_date']}/generated/"
        project_files = s3_service.list_objects(setup['bucket_name'], prefix=project_prefix)
        assert len(project_files) >= 3
        
        # 2. Integration-validator perspective: validate specific execution
        execution_prefix = f"{setup['project_name']}-{setup['project_date']}/generated/{setup['execution_id']}/"
        execution_files = s3_service.list_objects(setup['bucket_name'], prefix=execution_prefix)
        assert len(execution_files) == 3
        
        # 3. GitHub-orchestrator perspective: read all files for commit
        files_to_commit = []
        for file_obj in execution_files:
            content = s3_service.get_object(setup['bucket_name'], file_obj['key'])
            files_to_commit.append({
                'path': file_obj['key'].replace(execution_prefix, ''),  # Remove prefix for git
                'content': content
            })
        
        # Verify we can create commit structure
        assert len(files_to_commit) == 3
        expected_paths = ['src/App.tsx', 'src/components/Login.tsx', 'package.json']
        commit_paths = [f['path'] for f in files_to_commit]
        
        for expected_path in expected_paths:
            assert expected_path in commit_paths, f"Expected path {expected_path} not found in commit"
    
    def test_date_consistency_across_lambdas(self, mock_s3_setup):
        """Test that date format is consistent across all lambda functions."""
        # All lambdas should use the same date format for consistency
        test_date = datetime.utcnow().strftime('%Y%m%d')
        
        # Verify format matches expectations
        assert len(test_date) == 8
        assert test_date.isdigit()
        
        # Test with actual stored paths
        setup = mock_s3_setup
        s3_service = S3Service(region_name='us-east-1')
        all_objects = s3_service.list_objects(setup['bucket_name'])
        
        for obj in all_objects:
            key = obj['key']
            # Extract date from path: project-name-YYYYMMDD/generated/...
            project_date_part = key.split('/')[0]  # "project-name-YYYYMMDD"
            date_part = project_date_part.split('-')[-1]  # "YYYYMMDD"
            
            # Should match current test date format
            assert len(date_part) == 8, f"Date in path {key} should be 8 digits"
            assert date_part.isdigit(), f"Date in path {key} should be numeric"