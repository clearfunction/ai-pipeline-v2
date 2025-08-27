"""Tests for GitHub Orchestrator Lambda."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock AWS services before importing lambda function
with patch('boto3.client'), patch('requests.get'), patch('requests.post'):
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from lambda_function import (
        lambda_handler,
        GitHubService,
        setup_github_workflows,
        get_workflow_template,
        customize_workflow_template,
        generate_pr_description
    )


class TestGitHubOrchestrator:
    """Test cases for GitHub Orchestrator Lambda."""

    @pytest.fixture
    def sample_event(self):
        """Sample event data for testing."""
        return {
            'project_context': {
                'project_name': 'test-project',
                'project_date': '2024-01-15'
            },
            'execution_context': {
                'execution_id': 'test-exec-123',
                'tech_stack': 'REACT_SPA'
            },
            'validation_summary': {
                'validation_passed': True,
                'validation_results': [
                    {'validation_type': 'dependency_validation', 'passed': True}
                ]
            },
            'github_workflow_config': {
                'tech_stack': 'REACT_SPA',
                'workflow_name': 'React SPA CI/CD',
                'workflow_file': 'react-spa.yml',
                'project_name': 'test-project'
            }
        }

    @pytest.fixture
    def lambda_context(self):
        """Mock Lambda context."""
        context = Mock()
        context.function_name = 'github-orchestrator'
        context.function_version = '1'
        context.aws_request_id = 'test-request-id-123'
        return context

    @pytest.fixture
    def mock_github_service(self):
        """Mock GitHub service."""
        service = Mock(spec=GitHubService)
        service.create_or_get_repository.return_value = {
            'full_name': 'test-owner/test-project-generated',
            'html_url': 'https://github.com/test-owner/test-project-generated'
        }
        service.create_branch.return_value = {'ref': 'refs/heads/test-branch'}
        service.commit_file.return_value = {'sha': 'test-commit-sha', 'commit': {'sha': 'test-commit-sha'}}
        service.create_pull_request.return_value = {
            'html_url': 'https://github.com/test-owner/test-project-generated/pull/1',
            'number': 1
        }
        service.get_workflow_runs.return_value = []
        return service

    @patch.dict(os.environ, {
        'CODE_ARTIFACTS_BUCKET': 'test-code-bucket',
        'COMPONENT_SPECS_TABLE': 'test-table',
        'GITHUB_OWNER': 'test-owner',
        'GITHUB_TOKEN_SECRET': 'test-secret'
    })
    @patch('lambda_function.S3Service')
    @patch('lambda_function.DynamoDBService')
    @patch('lambda_function.GitHubService')
    @patch('lambda_function.setup_github_workflows')
    @patch('lambda_function.setup_logger')
    @patch('lambda_function.log_lambda_start')
    @patch('lambda_function.log_lambda_end')
    def test_lambda_handler_success(self, mock_log_end, mock_log_start, mock_setup_logger, 
                                   mock_setup_workflows, mock_github_service_class, 
                                   mock_dynamodb_service, mock_s3_service, 
                                   sample_event, lambda_context, mock_github_service):
        """Test successful lambda handler execution."""
        # Setup mocks
        mock_log_start.return_value = 'test-execution-id'
        mock_setup_logger.return_value = Mock()
        
        mock_s3_instance = Mock()
        mock_s3_service.return_value = mock_s3_instance
        mock_s3_instance.list_objects.return_value = [
            {'key': 'test-project-2024-01-15/generated/test-exec-123/src/App.tsx'},
            {'key': 'test-project-2024-01-15/generated/test-exec-123/src/components/Login.tsx'}
        ]
        mock_s3_instance.get_object.side_effect = [
            'const App = () => { return <div>App</div>; };',
            'const Login = () => { return <div>Login</div>; };'
        ]
        
        mock_dynamodb_instance = Mock()
        mock_dynamodb_service.return_value = mock_dynamodb_instance
        
        mock_github_service_class.return_value = mock_github_service
        
        mock_setup_workflows.return_value = {
            'setup_successful': True,
            'workflow_file': '.github/workflows/react-spa.yml'
        }
        
        # Execute
        result = lambda_handler(sample_event, lambda_context)
        
        # Verify
        assert result['success'] is True
        assert 'github_integration' in result['data']
        assert 'repository_url' in result['data']
        assert 'pull_request_url' in result['data']
        assert result['data']['committed_files_count'] == 2
        assert result['data']['next_stage'] == 'review-coordinator'
        
        # Verify GitHub service was called correctly
        mock_github_service.create_or_get_repository.assert_called_once_with('test-project', 'REACT_SPA')
        assert mock_github_service.create_branch.called
        assert mock_github_service.commit_file.call_count == 2
        mock_github_service.create_pull_request.assert_called_once()

    @patch('lambda_function.secrets_client')
    def test_github_service_initialization(self, mock_secrets_client):
        """Test GitHub service initialization with token retrieval."""
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': json.dumps({'github_token': 'test-token'})
        }
        
        with patch.dict(os.environ, {'GITHUB_TOKEN_SECRET': 'test-secret'}):
            service = GitHubService()
            
            assert service.token == 'test-token'
            assert 'Bearer test-token' in service.headers['Authorization']

    @patch('lambda_function.requests.get')
    @patch('lambda_function.requests.post')
    @patch('lambda_function.secrets_client')
    def test_github_service_create_repository(self, mock_secrets_client, mock_post, mock_get, mock_github_service):
        """Test GitHub repository creation."""
        # Mock secrets client
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': json.dumps({'github_token': 'test-token'})
        }
        
        # Mock repository doesn't exist
        mock_get.return_value.status_code = 404
        
        # Mock successful creation
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            'full_name': 'test-owner/test-project-generated',
            'html_url': 'https://github.com/test-owner/test-project-generated'
        }
        
        with patch.dict(os.environ, {'GITHUB_OWNER': 'test-owner', 'GITHUB_TOKEN_SECRET': 'test-secret'}):
            service = GitHubService()
            result = service.create_or_get_repository('test-project', 'REACT_SPA')
        
        assert result['full_name'] == 'test-owner/test-project-generated'
        mock_post.assert_called_once()

    @patch('lambda_function.requests.get')
    @patch('lambda_function.requests.post')
    @patch('lambda_function.secrets_client')
    def test_github_service_create_branch(self, mock_secrets_client, mock_post, mock_get):
        """Test GitHub branch creation."""
        # Mock secrets client
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': json.dumps({'github_token': 'test-token'})
        }
        
        # Mock getting main branch SHA
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'object': {'sha': 'main-branch-sha'}
        }
        
        # Mock successful branch creation
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            'ref': 'refs/heads/feature-branch'
        }
        
        service = GitHubService()
        result = service.create_branch('test-owner/test-repo', 'feature-branch')
        
        assert result['ref'] == 'refs/heads/feature-branch'
        mock_post.assert_called_once()

    @patch('lambda_function.requests.put')
    @patch('lambda_function.secrets_client')
    def test_github_service_commit_file(self, mock_secrets_client, mock_put):
        """Test GitHub file commit."""
        # Mock secrets client
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': json.dumps({'github_token': 'test-token'})
        }
        
        mock_put.return_value.status_code = 201
        mock_put.return_value.json.return_value = {
            'commit': {'sha': 'commit-sha'},
            'content': {'sha': 'file-sha'}
        }
        
        service = GitHubService()
        result = service.commit_file(
            'test-owner/test-repo',
            'feature-branch',
            'src/App.tsx',
            'const App = () => {};',
            'Add App component'
        )
        
        assert 'commit' in result
        mock_put.assert_called_once()

    @patch('lambda_function.requests.post')
    @patch('lambda_function.secrets_client')
    def test_github_service_create_pull_request(self, mock_secrets_client, mock_post):
        """Test GitHub pull request creation."""
        # Mock secrets client
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': json.dumps({'github_token': 'test-token'})
        }
        
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            'html_url': 'https://github.com/test-owner/test-repo/pull/1',
            'number': 1
        }
        
        service = GitHubService()
        result = service.create_pull_request(
            'test-owner/test-repo',
            'feature-branch',
            'main',
            'Test PR',
            'Test description'
        )
        
        assert result['number'] == 1
        assert 'pull/1' in result['html_url']
        mock_post.assert_called_once()

    def test_setup_github_workflows_success(self, mock_github_service):
        """Test successful GitHub Actions workflow setup."""
        mock_s3_service = Mock()
        workflow_config = {
            'tech_stack': 'REACT_SPA',
            'workflow_file': 'react-spa.yml',
            'workflow_name': 'React SPA CI/CD',
            'project_name': 'test-project'
        }
        
        mock_github_service.commit_file.return_value = {
            'commit': {'sha': 'workflow-commit-sha'}
        }
        
        result = setup_github_workflows(
            mock_github_service,
            mock_s3_service,
            'test-owner/test-repo',
            'feature-branch',
            workflow_config
        )
        
        assert result['setup_successful'] is True
        assert result['workflow_file'] == '.github/workflows/react-spa.yml'
        mock_github_service.commit_file.assert_called_once()

    def test_get_workflow_template_react_spa(self):
        """Test workflow template retrieval for React SPA."""
        template = get_workflow_template('REACT_SPA')
        
        assert 'React SPA CI/CD' in template
        assert 'npm ci' in template
        assert 'npm run build' in template
        assert 'npm test' in template

    def test_get_workflow_template_python_api(self):
        """Test workflow template retrieval for Python API."""
        template = get_workflow_template('PYTHON_API')
        
        assert 'Python API CI/CD' in template
        assert 'pip install poetry' in template
        assert 'poetry run pytest' in template
        assert 'poetry run mypy' in template

    def test_customize_workflow_template(self):
        """Test workflow template customization."""
        template = "name: {{PROJECT_NAME}}\nnode-version: {{NODE_VERSION}}"
        config = {
            'project_name': 'my-project',
            'node_version': '18'
        }
        
        result = customize_workflow_template(template, config)
        
        assert 'my-project' in result
        assert 'node-version: 18' in result

    def test_generate_pr_description(self):
        """Test pull request description generation."""
        validation_summary = {
            'validation_passed': True,
            'validation_results': [
                {'validation_type': 'dependency_validation', 'passed': True},
                {'validation_type': 'import_export_validation', 'passed': True}
            ]
        }
        
        committed_files = [
            {'path': 'src/App.tsx', 'size': 1024},
            {'path': 'src/components/Login.tsx', 'size': 512}
        ]
        
        description = generate_pr_description(validation_summary, committed_files, 'REACT_SPA')
        
        assert 'REACT_SPA' in description
        assert '✅ Yes' in description  # Validation passed
        assert '2' in description  # Components validated
        assert 'src/App.tsx' in description
        assert '1024 bytes' in description

    def test_generate_pr_description_many_files(self):
        """Test PR description with many files (should limit display)."""
        validation_summary = {'validation_passed': True, 'validation_results': []}
        committed_files = [{'path': f'file{i}.tsx', 'size': 100} for i in range(15)]
        
        description = generate_pr_description(validation_summary, committed_files, 'REACT_SPA')
        
        assert '... and 5 more files' in description
        assert 'file9.tsx' in description  # Should show first 10
        assert 'file14.tsx' not in description  # Should not show beyond 10

    @patch.dict(os.environ, {
        'CODE_ARTIFACTS_BUCKET': 'test-code-bucket',
        'COMPONENT_SPECS_TABLE': 'test-table'
    })
    @patch('lambda_function.setup_logger')
    @patch('lambda_function.log_lambda_start')
    def test_lambda_handler_missing_context(self, mock_log_start, mock_setup_logger, lambda_context):
        """Test lambda handler with missing required context."""
        mock_log_start.return_value = 'test-execution-id'
        mock_setup_logger.return_value = Mock()
        
        # Missing project context
        event = {
            'execution_context': {
                'tech_stack': 'REACT_SPA'
            }
        }
        
        result = lambda_handler(event, lambda_context)
        
        assert result['success'] is False
        assert 'Missing required context' in result['error']


if __name__ == '__main__':
    pytest.main([__file__])