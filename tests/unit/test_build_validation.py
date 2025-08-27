"""
Comprehensive tests for build validation functionality.
Tests lock file validation, build requirements, and GitHub orchestrator build readiness.
"""

import pytest
import json
from unittest.mock import Mock, patch
import sys
import os

# Add the lambda paths to the Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lambdas', 'story-execution', 'integration-validator'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lambdas', 'story-execution', 'github-orchestrator'))


class TestLockFileValidation:
    """Test lock file validation in Integration Validator."""
    
    def test_react_spa_with_package_lock_passes(self):
        """Test React SPA with package-lock.json passes validation."""
        from lambda_function import validate_lock_files
        
        generated_files = [
            {'file_path': 'package.json', 'content': '{}'},
            {'file_path': 'package-lock.json', 'content': '{}'},
            {'file_path': 'src/App.tsx', 'content': 'code'}
        ]
        
        result = validate_lock_files(generated_files, 'react_spa')
        
        assert result['validation_type'] == 'lock_file_validation'
        assert result['passed'] is True
        assert len(result['issues']) == 0
        assert result['details']['has_package_json'] is True
        assert result['details']['has_package_lock'] is True
        
    def test_react_spa_with_yarn_lock_passes(self):
        """Test React SPA with yarn.lock passes validation."""
        from lambda_function import validate_lock_files
        
        generated_files = [
            {'file_path': 'package.json', 'content': '{}'},
            {'file_path': 'yarn.lock', 'content': '{}'},
            {'file_path': 'src/App.tsx', 'content': 'code'}
        ]
        
        result = validate_lock_files(generated_files, 'react_spa')
        
        assert result['passed'] is True
        assert result['details']['has_yarn_lock'] is True
        
    def test_react_spa_missing_lock_file_fails(self):
        """Test React SPA missing lock file fails validation."""
        from lambda_function import validate_lock_files
        
        generated_files = [
            {'file_path': 'package.json', 'content': '{}'},
            {'file_path': 'src/App.tsx', 'content': 'code'}
        ]
        
        result = validate_lock_files(generated_files, 'react_spa')
        
        assert result['passed'] is False
        assert len(result['issues']) > 0
        assert any('lock file' in issue.lower() for issue in result['issues'])
        assert 'GitHub Actions requires lock files' in ' '.join(result['issues'])
        
    def test_react_spa_missing_package_json_fails(self):
        """Test React SPA missing package.json fails validation."""
        from lambda_function import validate_lock_files
        
        generated_files = [
            {'file_path': 'src/App.tsx', 'content': 'code'}
        ]
        
        result = validate_lock_files(generated_files, 'react_spa')
        
        assert result['passed'] is False
        assert any('package.json' in issue for issue in result['issues'])
        
    def test_python_api_with_requirements_passes(self):
        """Test Python API with requirements.txt passes validation."""
        from lambda_function import validate_lock_files
        
        generated_files = [
            {'file_path': 'requirements.txt', 'content': 'flask>=2.0.0'},
            {'file_path': 'app.py', 'content': 'code'}
        ]
        
        result = validate_lock_files(generated_files, 'python_api')
        
        assert result['passed'] is True
        
    def test_python_api_missing_requirements_fails(self):
        """Test Python API missing requirements.txt fails validation."""
        from lambda_function import validate_lock_files
        
        generated_files = [
            {'file_path': 'app.py', 'content': 'code'}
        ]
        
        result = validate_lock_files(generated_files, 'python_api')
        
        assert result['passed'] is False
        assert any('requirements.txt' in issue for issue in result['issues'])


class TestBuildRequirementsValidation:
    """Test build requirements validation in Integration Validator."""
    
    def test_react_spa_with_valid_package_json_passes(self):
        """Test React SPA with valid package.json passes validation."""
        from lambda_function import validate_build_requirements
        
        package_json_content = {
            "name": "test-project",
            "scripts": {
                "build": "vite build",
                "dev": "vite",
                "test": "vitest"
            },
            "dependencies": {
                "react": "^18.2.0"
            }
        }
        
        generated_files = [
            {
                'file_path': 'package.json', 
                'content': json.dumps(package_json_content)
            },
            {'file_path': 'src/App.tsx', 'content': 'code'}
        ]
        
        architecture = {
            'tech_stack': 'react_spa',
            'build_config': {'package_manager': 'npm'}
        }
        
        result = validate_build_requirements(generated_files, 'react_spa', architecture)
        
        assert result['validation_type'] == 'build_requirements_validation'
        assert result['passed'] is True
        assert len(result['issues']) == 0
        
    def test_react_spa_missing_build_script_fails(self):
        """Test React SPA missing build script fails validation."""
        from lambda_function import validate_build_requirements
        
        package_json_content = {
            "name": "test-project",
            "scripts": {
                "dev": "vite"
                # Missing "build" script
            },
            "dependencies": {
                "react": "^18.2.0"
            }
        }
        
        generated_files = [
            {
                'file_path': 'package.json', 
                'content': json.dumps(package_json_content)
            }
        ]
        
        architecture = {
            'tech_stack': 'react_spa',
            'build_config': {'package_manager': 'npm'}
        }
        
        result = validate_build_requirements(generated_files, 'react_spa', architecture)
        
        assert result['passed'] is False
        assert any('build' in issue for issue in result['issues'])
        
    def test_package_manager_mismatch_fails(self):
        """Test package manager mismatch fails validation."""
        from lambda_function import validate_build_requirements
        
        generated_files = [
            {'file_path': 'package.json', 'content': '{}'},
            {'file_path': 'yarn.lock', 'content': '{}'}  # yarn.lock present
        ]
        
        architecture = {
            'tech_stack': 'react_spa',
            'build_config': {'package_manager': 'npm'}  # but npm configured
        }
        
        result = validate_build_requirements(generated_files, 'react_spa', architecture)
        
        assert result['passed'] is False
        assert any('mismatch' in issue.lower() for issue in result['issues'])
        
    def test_missing_dependencies_fails(self):
        """Test package.json with no dependencies fails validation."""
        from lambda_function import validate_build_requirements
        
        package_json_content = {
            "name": "test-project",
            "scripts": {
                "build": "vite build",
                "dev": "vite"
            }
            # Missing dependencies
        }
        
        generated_files = [
            {
                'file_path': 'package.json', 
                'content': json.dumps(package_json_content)
            }
        ]
        
        architecture = {'tech_stack': 'react_spa'}
        
        result = validate_build_requirements(generated_files, 'react_spa', architecture)
        
        assert result['passed'] is False
        assert any('dependencies' in issue.lower() for issue in result['issues'])


class TestGitHubOrchestratorBuildValidation:
    """Test build readiness validation in GitHub Orchestrator."""
    
    def test_validate_build_readiness_complete_project_passes(self):
        """Test complete project passes build readiness validation."""
        from lambda_function import validate_build_readiness
        
        generated_files = [
            {'file_path': 'package.json', 'content': '{}'},
            {'file_path': 'package-lock.json', 'content': '{}'},
            {'file_path': '.gitignore', 'content': 'node_modules/'},
            {'file_path': 'src/App.tsx', 'content': 'code'}
        ]
        
        architecture = {'tech_stack': 'react_spa'}
        
        result = validate_build_readiness(generated_files, 'react_spa', architecture)
        
        assert result['ready'] is True
        assert len(result['missing_files']) == 0
        assert len(result['issues']) == 0
        
    def test_validate_build_readiness_missing_lock_file_fails(self):
        """Test missing lock file fails build readiness validation."""
        from lambda_function import validate_build_readiness
        
        generated_files = [
            {'file_path': 'package.json', 'content': '{}'},
            {'file_path': 'src/App.tsx', 'content': 'code'}
        ]
        
        architecture = {'tech_stack': 'react_spa'}
        
        result = validate_build_readiness(generated_files, 'react_spa', architecture)
        
        assert result['ready'] is False
        assert 'package-lock.json' in result['missing_files']
        assert any('lock file' in issue.lower() for issue in result['issues'])
        
    def test_add_missing_build_files_package_lock(self):
        """Test adding missing package-lock.json file."""
        from lambda_function import add_missing_build_files
        
        generated_files = [
            {'file_path': 'package.json', 'content': '{}'},
            {'file_path': 'src/App.tsx', 'content': 'code'}
        ]
        
        missing_files = ['package-lock.json']
        
        result = add_missing_build_files(generated_files, missing_files, 'react_spa')
        
        # Should have original files plus the added lock file
        assert len(result) == len(generated_files) + 1
        
        # Check if package-lock.json was added
        added_lock_file = next((f for f in result if f['file_path'] == 'package-lock.json'), None)
        assert added_lock_file is not None
        assert added_lock_file['auto_generated'] is True
        
        # Validate the lock file content
        lock_content = json.loads(added_lock_file['content'])
        assert lock_content['lockfileVersion'] == 3
        assert 'packages' in lock_content
        
    def test_add_missing_build_files_package_json(self):
        """Test adding missing package.json file."""
        from lambda_function import add_missing_build_files
        
        generated_files = [
            {'file_path': 'src/App.tsx', 'content': 'code'}
        ]
        
        missing_files = ['package.json']
        
        result = add_missing_build_files(generated_files, missing_files, 'react_spa')
        
        # Check if package.json was added
        added_package_file = next((f for f in result if f['file_path'] == 'package.json'), None)
        assert added_package_file is not None
        
        # Validate the package.json content
        package_content = json.loads(added_package_file['content'])
        assert 'scripts' in package_content
        assert 'build' in package_content['scripts']
        assert 'dev' in package_content['scripts']
        assert 'react' in package_content['dependencies']
        
    def test_add_missing_build_files_python_requirements(self):
        """Test adding missing requirements.txt for Python projects."""
        from lambda_function import add_missing_build_files
        
        generated_files = [
            {'file_path': 'app.py', 'content': 'code'}
        ]
        
        missing_files = ['requirements.txt']
        
        result = add_missing_build_files(generated_files, missing_files, 'python_api')
        
        # Check if requirements.txt was added
        added_requirements = next((f for f in result if f['file_path'] == 'requirements.txt'), None)
        assert added_requirements is not None
        
        # Validate the requirements.txt content
        assert 'flask' in added_requirements['content']
        assert 'pytest' in added_requirements['content']


class TestIntegrationValidatorEndToEnd:
    """End-to-end tests for Integration Validator with new validations."""
    
    @patch('lambda_function.dynamodb')
    def test_lambda_handler_with_build_validation_success(self, mock_dynamodb):
        """Test lambda handler with successful build validation."""
        from lambda_function import lambda_handler
        
        # Mock DynamoDB table
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Complete event with all required build files
        event = {
            'storyExecutorResult': {
                'Payload': {
                    'data': {
                        'generated_files': [
                            {'file_path': 'package.json', 'content': '{}'},
                            {'file_path': 'package-lock.json', 'content': '{}'},
                            {'file_path': 'src/App.tsx', 'content': 'code'}
                        ],
                        'architecture': {
                            'project_id': 'test-project',
                            'tech_stack': 'react_spa',
                            'components': [
                                {
                                    'component_id': 'comp_001',
                                    'name': 'App',
                                    'file_path': 'src/App.tsx'
                                }
                            ]
                        },
                        'pipeline_context': {
                            'project_id': 'test-project'
                        }
                    }
                }
            }
        }
        
        result = lambda_handler(event, Mock())
        
        assert result['status'] == 'success'
        assert result['data']['validation_passed'] is True
        
        # Check that all 5 validations were performed (including new ones)
        validation_results = result['data']['validation_summary']['validation_results']
        assert len(validation_results) == 5
        
        # Verify new validations are present
        validation_types = [v['validation_type'] for v in validation_results]
        assert 'lock_file_validation' in validation_types
        assert 'build_requirements_validation' in validation_types
        
    @patch('lambda_function.dynamodb')
    def test_lambda_handler_with_build_validation_failure(self, mock_dynamodb):
        """Test lambda handler with failed build validation."""
        from lambda_function import lambda_handler
        
        # Mock DynamoDB table
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Event missing critical build files
        event = {
            'storyExecutorResult': {
                'Payload': {
                    'data': {
                        'generated_files': [
                            {'file_path': 'src/App.tsx', 'content': 'code'}
                            # Missing package.json and package-lock.json
                        ],
                        'architecture': {
                            'project_id': 'test-project',
                            'tech_stack': 'react_spa',
                            'components': [
                                {
                                    'component_id': 'comp_001',
                                    'name': 'App',
                                    'file_path': 'src/App.tsx'
                                }
                            ]
                        },
                        'pipeline_context': {
                            'project_id': 'test-project'
                        }
                    }
                }
            }
        }
        
        result = lambda_handler(event, Mock())
        
        assert result['status'] == 'success'  # Lambda succeeds but validation fails
        assert result['data']['validation_passed'] is False
        
        # Check that lock file validation failed
        validation_results = result['data']['validation_summary']['validation_results']
        lock_file_result = next((v for v in validation_results if v['validation_type'] == 'lock_file_validation'), None)
        assert lock_file_result is not None
        assert lock_file_result['passed'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])