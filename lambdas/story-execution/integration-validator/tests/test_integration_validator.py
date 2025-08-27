"""Tests for Integration Validator Lambda."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock AWS services before importing lambda function
with patch('boto3.client'), patch('boto3.resource'):
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from lambda_function import (
        lambda_handler,
        validate_component_dependencies,
        validate_tech_stack_consistency,
        generate_github_workflows,
        extract_exports_from_code,
        extract_imports_from_code,
        is_external_library
    )


class TestIntegrationValidator:
    """Test cases for Integration Validator Lambda."""

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
            'component_specs': [
                {
                    'component_id': 'comp_001',
                    'name': 'LoginPage',
                    'type': 'page',
                    'file_path': 'src/pages/LoginPage.tsx',
                    'dependencies': ['AuthService'],
                    'exports': ['LoginPage'],
                    'story_ids': ['story-1']
                },
                {
                    'component_id': 'comp_002',
                    'name': 'AuthService',
                    'type': 'service',
                    'file_path': 'src/services/AuthService.ts',
                    'dependencies': [],
                    'exports': ['AuthService'],
                    'story_ids': ['story-2']
                }
            ]
        }

    @pytest.fixture
    def lambda_context(self):
        """Mock Lambda context."""
        context = Mock()
        context.function_name = 'integration-validator'
        context.function_version = '1'
        context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:integration-validator'
        context.memory_limit_in_mb = '512'
        context.remaining_time_in_millis = lambda: 300000
        context.log_group_name = '/aws/lambda/integration-validator'
        context.log_stream_name = '2024/01/15/[$LATEST]1234567890abcdef1234567890abcdef'
        context.aws_request_id = 'test-request-id-123'
        return context

    @patch.dict(os.environ, {
        'CODE_ARTIFACTS_BUCKET': 'test-code-bucket',
        'COMPONENT_SPECS_TABLE': 'test-component-specs-table'
    })
    @patch('lambda_function.S3Service')
    @patch('lambda_function.DynamoDBService')
    @patch('lambda_function.setup_logger')
    @patch('lambda_function.log_lambda_start')
    @patch('lambda_function.log_lambda_end')
    def test_lambda_handler_success(self, mock_log_end, mock_log_start, mock_setup_logger, 
                                   mock_dynamodb_service, mock_s3_service, sample_event, lambda_context):
        """Test successful lambda handler execution."""
        # Setup mocks
        mock_log_start.return_value = 'test-execution-id'
        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger
        
        mock_s3_instance = Mock()
        mock_s3_service.return_value = mock_s3_instance
        mock_s3_instance.get_object.side_effect = [
            'export function LoginPage() { return <div>Login</div>; }',
            'export class AuthService { authenticate() { return true; } }'
        ]
        
        mock_dynamodb_instance = Mock()
        mock_dynamodb_service.return_value = mock_dynamodb_instance
        mock_dynamodb_instance.put_item.return_value = True
        
        # Execute
        result = lambda_handler(sample_event, lambda_context)
        
        # Verify
        assert result['success'] is True
        assert 'validation_summary' in result['data']
        assert 'github_workflow_config' in result['data']
        assert result['data']['next_stage'] == 'github-orchestrator'
        
        # Verify validation passed
        validation_summary = result['data']['validation_summary']
        assert validation_summary['validation_passed'] is True
        assert len(validation_summary['validation_results']) == 3  # 3 validation types

    def test_validate_component_dependencies_success(self):
        """Test successful component dependency validation."""
        component_specs = [
            {
                'component_id': 'comp_001',
                'name': 'LoginPage',
                'type': 'page',
                'file_path': 'src/pages/LoginPage.tsx',
                'dependencies': ['AuthService'],
                'exports': ['LoginPage'],
                'story_ids': ['story-1']
            },
            {
                'component_id': 'comp_002',
                'name': 'AuthService',
                'type': 'service', 
                'file_path': 'src/services/AuthService.ts',
                'dependencies': [],
                'exports': ['AuthService'],
                'story_ids': ['story-2']
            }
        ]
        
        result = validate_component_dependencies(component_specs)
        
        assert result.passed is True
        assert result.validation_type == 'dependency_validation'
        assert len(result.issues) == 0
        assert result.details['total_components'] == 2

    def test_validate_component_dependencies_missing_dependency(self):
        """Test dependency validation with missing dependency."""
        component_specs = [
            {
                'component_id': 'comp_001',
                'name': 'LoginPage',
                'type': 'page',
                'file_path': 'src/pages/LoginPage.tsx',
                'dependencies': ['MissingService'],
                'exports': ['LoginPage'],
                'story_ids': ['story-1']
            }
        ]
        
        result = validate_component_dependencies(component_specs)
        
        assert result.passed is False
        assert result.validation_type == 'dependency_validation'
        assert len(result.issues) == 1
        assert 'MissingService' in result.issues[0]

    def test_validate_tech_stack_consistency_react_spa(self):
        """Test tech stack validation for React SPA."""
        component_specs = [
            {
                'component_id': 'comp_001',
                'name': 'LoginPage',
                'type': 'page',
                'file_path': 'src/pages/LoginPage.tsx',
                'dependencies': [],
                'exports': ['LoginPage'],
                'story_ids': ['story-1']
            },
            {
                'component_id': 'comp_002', 
                'name': 'styles',
                'type': 'style',
                'file_path': 'src/styles/main.css',
                'dependencies': [],
                'exports': [],
                'story_ids': []
            }
        ]
        
        result = validate_tech_stack_consistency(component_specs, 'REACT_SPA')
        
        assert result.passed is True
        assert result.validation_type == 'tech_stack_validation'
        assert len(result.issues) == 0

    def test_validate_tech_stack_consistency_wrong_extension(self):
        """Test tech stack validation with wrong file extension."""
        component_specs = [
            {
                'component_id': 'comp_001',
                'name': 'LoginPage',
                'type': 'page',
                'file_path': 'src/pages/LoginPage.py',  # Python file in React project
                'dependencies': [],
                'exports': ['LoginPage'],
                'story_ids': ['story-1']
            }
        ]
        
        result = validate_tech_stack_consistency(component_specs, 'REACT_SPA')
        
        assert result.passed is False
        assert result.validation_type == 'tech_stack_validation'
        assert len(result.issues) == 1
        assert '.py' in result.issues[0]

    def test_generate_github_workflows_react_spa(self):
        """Test GitHub workflow generation for React SPA."""
        result = generate_github_workflows('REACT_SPA', 'test-project')
        
        assert result.tech_stack == 'REACT_SPA'
        assert result.workflow_name == 'React SPA CI/CD'
        assert result.workflow_file == 'react-spa.yml'
        assert result.project_name == 'test-project'
        assert 'push' in result.triggers
        assert 'pull_request' in result.triggers
        assert result.node_version == '18'
        assert result.python_version is None

    def test_generate_github_workflows_python_api(self):
        """Test GitHub workflow generation for Python API."""
        result = generate_github_workflows('PYTHON_API', 'test-project')
        
        assert result.tech_stack == 'PYTHON_API'
        assert result.workflow_name == 'Python API CI/CD'
        assert result.workflow_file == 'python-api.yml'
        assert result.project_name == 'test-project'
        assert result.node_version is None
        assert result.python_version == '3.11'

    def test_generate_github_workflows_unsupported_stack(self):
        """Test GitHub workflow generation with unsupported tech stack."""
        with pytest.raises(ValueError, match="Unsupported tech stack"):
            generate_github_workflows('UNSUPPORTED_STACK', 'test-project')

    def test_extract_exports_from_code_react(self):
        """Test export extraction from React TypeScript code."""
        code = '''
import React from 'react';

export function LoginPage() {
    return <div>Login Page</div>;
}

export default LoginPage;

export class AuthService {
    authenticate() {
        return true;
    }
}

export { LoginPage as DefaultLogin };
        '''
        
        exports = extract_exports_from_code(code, 'LoginPage.tsx')
        
        assert 'LoginPage' in exports
        assert 'AuthService' in exports
        assert 'DefaultLogin' in exports or 'LoginPage' in exports  # Named export handling

    def test_extract_imports_from_code_react(self):
        """Test import extraction from React TypeScript code."""
        code = '''
import React from 'react';
import { useState, useEffect } from 'react';
import axios from 'axios';
import { AuthService } from '../services/AuthService';
        '''
        
        imports = extract_imports_from_code(code, 'LoginPage.tsx')
        
        assert 'React' in imports
        assert 'useState' in imports
        assert 'useEffect' in imports
        assert 'axios' in imports
        assert 'AuthService' in imports

    def test_extract_imports_from_code_python(self):
        """Test import extraction from Python code."""
        code = '''
from fastapi import FastAPI, HTTPException
from typing import Optional
import json
import os
        '''
        
        imports = extract_imports_from_code(code, 'main.py')
        
        assert 'FastAPI' in imports
        assert 'HTTPException' in imports
        assert 'Optional' in imports

    def test_is_external_library(self):
        """Test external library detection."""
        assert is_external_library('react') is True
        assert is_external_library('express') is True
        assert is_external_library('fastapi') is True
        assert is_external_library('axios') is True
        assert is_external_library('@types/node') is True  # Scoped package
        
        assert is_external_library('MyComponent') is False
        assert is_external_library('AuthService') is False

    @patch.dict(os.environ, {
        'CODE_ARTIFACTS_BUCKET': 'test-code-bucket',
        'COMPONENT_SPECS_TABLE': 'test-component-specs-table'
    })
    @patch('lambda_function.setup_logger')
    @patch('lambda_function.log_lambda_start')
    def test_lambda_handler_missing_context(self, mock_log_start, mock_setup_logger, lambda_context):
        """Test lambda handler with missing required context."""
        mock_log_start.return_value = 'test-execution-id'
        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger
        
        # Missing project context
        event = {
            'execution_context': {
                'tech_stack': 'REACT_SPA'
            },
            'component_specs': []
        }
        
        result = lambda_handler(event, lambda_context)
        
        assert result['success'] is False
        assert 'Missing required context' in result['error']


if __name__ == '__main__':
    pytest.main([__file__])