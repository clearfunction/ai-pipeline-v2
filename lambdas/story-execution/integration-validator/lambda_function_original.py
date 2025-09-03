"""
Integration Validator Lambda

Validates cross-component integration, consistency, and generates GitHub workflow configurations.
This lambda ensures generated components work together and sets up GitHub repository structure.

Author: AI Pipeline Orchestrator v2
Version: 1.0.0 (Simplified)
"""

import json
import os
from typing import Dict, Any, List, Optional
import boto3
from datetime import datetime

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def retrieve_file_content_from_s3(file_metadata: Dict[str, Any]) -> str:
    """
    Retrieve file content from S3 using metadata.
    
    Args:
        file_metadata: File metadata containing S3 location
        
    Returns:
        File content as string
    """
    s3_bucket = file_metadata.get('s3_bucket')
    s3_key = file_metadata.get('s3_key')
    
    # If no S3 info, check for inline content (backward compatibility)
    if not s3_bucket or not s3_key:
        return file_metadata.get('content', '')
    
    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        print(f"Error retrieving file from S3: {e}")
        return ''

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main lambda handler for integration validation and GitHub setup.
    
    Args:
        event: Lambda event containing execution context and component specifications
        context: Lambda runtime context
        
    Returns:
        Dict containing validation results and GitHub workflow configuration
    """
    execution_id = f"integration_val_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
    
    try:
        print(f"Starting integration validation with execution_id: {execution_id}")
        print(f"Event data: {json.dumps(event, default=str)}")
        
        # Handle both direct lambda input and Step Functions input
        if 'storyExecutorResult' in event:
            # Step Functions format - extract from story executor result
            story_result = event.get('storyExecutorResult', {}).get('Payload', {})
            data = story_result.get('data', {})
        else:
            # Direct lambda input format
            data = event.get('data', {})
        
        project_context = data.get('pipeline_context', {})
        generated_files = data.get('generated_files', [])
        architecture = data.get('architecture', {})
        
        project_id = project_context.get('project_id')
        tech_stack = architecture.get('tech_stack')
        components = architecture.get('components', [])
        
        if not all([project_id, tech_stack, components]):
            raise ValueError("Missing required data: project_id, tech_stack, or components")
        
        print(f"Validating project: {project_id}, tech_stack: {tech_stack}, components: {len(components)}")
        
        # Perform validation tasks
        validation_results = []
        
        # 1. Cross-component dependency validation
        dependency_validation = validate_component_dependencies(components)
        validation_results.append(dependency_validation)
        
        # 2. File generation validation
        file_validation = validate_generated_files(components, generated_files)
        validation_results.append(file_validation)
        
        # 3. Tech stack consistency validation
        tech_stack_validation = validate_tech_stack_consistency(components, tech_stack)
        validation_results.append(tech_stack_validation)
        
        # 4. Lock file validation (NEW)
        lock_file_validation = validate_lock_files(generated_files, tech_stack)
        validation_results.append(lock_file_validation)
        
        # 5. Build requirements validation (NEW)
        build_requirements_validation = validate_build_requirements(generated_files, tech_stack, architecture)
        validation_results.append(build_requirements_validation)
        
        # Prepare validation summary
        validation_summary = {
            'execution_id': execution_id,
            'project_id': project_id,
            'tech_stack': tech_stack,
            'validation_results': validation_results,
            'validation_passed': all(result.get('passed', False) for result in validation_results),
            'validated_at': datetime.utcnow().isoformat()
        }
        
        # Store validation results in DynamoDB
        try:
            table = dynamodb.Table(os.environ.get('COMPONENT_SPECS_TABLE', 'ai-pipeline-v2-component-specs-dev'))
            table.put_item(Item={
                'component_id': f"validation-{execution_id}",
                'validation_summary': validation_summary,
                'ttl': int(datetime.utcnow().timestamp()) + (30 * 24 * 60 * 60)  # 30 days
            })
            print(f"Stored validation results in DynamoDB")
        except Exception as e:
            print(f"Warning: Failed to store validation results: {str(e)}")
        
        # Store full validation results and data in S3 for retrieval
        try:
            full_results = {
                'execution_id': execution_id,
                'project_id': project_id,
                'validation_summary': validation_summary,
                'validation_results': validation_results,
                'architecture': architecture,
                'generated_files': generated_files,
                'pipeline_context': project_context,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            bucket_name = os.environ.get('PROCESSED_BUCKET_NAME', 'ai-pipeline-v2-processed-008537862626-us-east-1')
            s3_key = f"validation-results/{execution_id}/full-results.json"
            
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=json.dumps(full_results, default=str),
                ContentType='application/json'
            )
            print(f"Stored full validation results in S3: s3://{bucket_name}/{s3_key}")
        except Exception as e:
            print(f"Warning: Failed to store full results in S3: {str(e)}")
        
        # Prepare response - minimize payload size for Step Functions
        # Only pass essential data and summaries, not full file contents
        validation_passed = validation_summary['validation_passed']
        response = {
            'status': 'success' if validation_passed else 'failed',
            'message': f'Integration validation {"passed" if validation_passed else "failed"} - {len(validation_results)} validations performed',
            'execution_id': execution_id,
            'stage': 'integration_validation',
            'project_id': project_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'validation_summary': validation_summary,
                'validation_passed': validation_summary['validation_passed'],
                'pipeline_context': {
                    'project_id': project_context.get('project_id'),
                    'execution_id': project_context.get('execution_id'),
                    'stage': 'integration_validation'
                },
                # Only pass essential architecture info, not full components
                'architecture_summary': {
                    'project_id': architecture.get('project_id'),
                    'tech_stack': architecture.get('tech_stack'),
                    'components_count': len(architecture.get('components', [])),
                    'build_config': architecture.get('build_config', {})
                },
                # Only pass file count and summary, not full file contents
                'generated_files_summary': {
                    'total_files': len(generated_files),
                    'file_paths': [f.get('file_path') for f in generated_files[:20]]  # First 20 files only
                },
                # Store full data reference for retrieval if needed
                'full_data_reference': {
                    'bucket': os.environ.get('PROCESSED_BUCKET_NAME'),
                    'key': f"validation-results/{execution_id}/full-results.json"
                }
            },
            'next_stage': 'github_orchestrator' if validation_passed else None
        }
        
        if validation_passed:
            print(f"Integration validation completed successfully")
            return response
        else:
            print(f"Integration validation failed - validation issues found")
            # Raise exception for Step Functions to handle the failure
            failed_validations = [v for v in validation_results if not v.get('passed', False)]
            error_details = f"Validation failed: {len(failed_validations)} of {len(validation_results)} validations failed"
            raise ValueError(error_details)
        
    except Exception as e:
        print(f"Integration validation failed: {str(e)}")
        
        # Return proper error status - raise exception for Step Functions to handle
        error_msg = f"Integration validation failed: {str(e)}"
        raise RuntimeError(error_msg)


def validate_component_dependencies(components: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate that all component dependencies are satisfied.
    
    Args:
        components: List of component specifications
        
    Returns:
        Validation result with dependency validation results
    """
    try:
        component_names = {comp.get('name') for comp in components}
        
        issues = []
        for component in components:
            component_name = component.get('name')
            dependencies = component.get('dependencies', [])
            
            for dependency in dependencies:
                if dependency not in component_names:
                    issues.append(f"Component '{component_name}' depends on '{dependency}' which is not defined")
        
        return {
            'validation_type': 'dependency_validation',
            'passed': len(issues) == 0,
            'issues': issues,
            'details': {
                'total_components': len(components), 
                'total_dependencies': sum(len(c.get('dependencies', [])) for c in components)
            }
        }
        
    except Exception as e:
        return {
            'validation_type': 'dependency_validation',
            'passed': False,
            'issues': [f"Dependency validation failed: {str(e)}"],
            'details': {}
        }


def validate_generated_files(components: List[Dict[str, Any]], generated_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate that all required component files were generated.
    
    Args:
        components: List of component specifications
        generated_files: List of generated file metadata
        
    Returns:
        Validation result with file generation validation results
    """
    try:
        expected_files = {comp.get('file_path') for comp in components}
        generated_file_paths = {file.get('file_path') for file in generated_files}
        
        issues = []
        missing_files = expected_files - generated_file_paths
        for missing_file in missing_files:
            issues.append(f"Expected file '{missing_file}' was not generated")
        
        # Check for consistent component IDs
        for file in generated_files:
            component_id = file.get('component_id')
            matching_components = [c for c in components if c.get('component_id') == component_id]
            if not matching_components:
                issues.append(f"Generated file has component_id '{component_id}' not found in architecture")
        
        return {
            'validation_type': 'file_generation_validation',
            'passed': len(issues) == 0,
            'issues': issues,
            'details': {
                'expected_files': len(expected_files),
                'generated_files': len(generated_files),
                'missing_files': list(missing_files)
            }
        }
        
    except Exception as e:
        return {
            'validation_type': 'file_generation_validation',
            'passed': False,
            'issues': [f"File generation validation failed: {str(e)}"],
            'details': {}
        }


def validate_tech_stack_consistency(components: List[Dict[str, Any]], tech_stack: str) -> Dict[str, Any]:
    """
    Validate that all components are consistent with the chosen tech stack.
    
    Args:
        components: List of component specifications
        tech_stack: Selected tech stack (e.g., 'react_fullstack', 'react_spa')
        
    Returns:
        Validation result with tech stack validation results
    """
    try:
        # Define expected file extensions by tech stack
        tech_stack_extensions = {
            'react_spa': ['.tsx', '.ts', '.jsx', '.js', '.css', '.scss'],
            'node_api': ['.js', '.ts', '.json'],
            'python_api': ['.py', '.pyi'],
            'vue_spa': ['.vue', '.js', '.ts', '.css', '.scss'],
            'react_fullstack': ['.tsx', '.ts', '.jsx', '.js', '.css', '.scss', '.json']
        }
        
        # Common config/build files that are valid for all tech stacks
        universal_extensions = ['.json', '.yml', '.yaml', '.md', '.txt', '.gitignore', '.env', '.lock', '.html']
        config_file_names = ['package.json', 'package-lock.json', 'yarn.lock', 'tsconfig.json', 
                            'vite.config.ts', 'vite.config.js', 'webpack.config.js', '.eslintrc.json',
                            '.prettierrc', '.gitignore', 'README.md', 'index.html']
        
        expected_extensions = tech_stack_extensions.get(tech_stack.lower(), [])
        issues = []
        
        for component in components:
            file_path = component.get('file_path', '')
            component_name = component.get('name', 'unknown')
            component_type = component.get('type', '')
            
            # Skip validation for scaffold/config components
            if component_type in ['scaffold', 'config'] or component_name in ['ProjectScaffold', 'ConfigFiles']:
                continue
            
            # Skip validation for known config files
            file_name = file_path.split('/')[-1] if '/' in file_path else file_path
            if file_name in config_file_names:
                continue
                
            if '.' in file_path:
                file_extension = '.' + file_path.split('.')[-1]
                
                # Allow universal extensions for all tech stacks
                if file_extension in universal_extensions:
                    continue
                
                if file_extension not in expected_extensions:
                    issues.append(f"Component '{component_name}' has file extension '{file_extension}' not expected for tech stack '{tech_stack}'")
            else:
                # Files without extensions might be valid (e.g., Dockerfile)
                if file_name not in ['Dockerfile', 'Makefile', 'LICENSE']:
                    issues.append(f"Component '{component_name}' has invalid file path '{file_path}'")
        
        return {
            'validation_type': 'tech_stack_validation',
            'passed': len(issues) == 0,
            'issues': issues,
            'details': {
                'tech_stack': tech_stack,
                'expected_extensions': expected_extensions,
                'components_validated': len(components)
            }
        }
        
    except Exception as e:
        return {
            'validation_type': 'tech_stack_validation', 
            'passed': False,
            'issues': [f"Tech stack validation failed: {str(e)}"],
            'details': {}
        }


def generate_github_workflows(tech_stack: str, project_name: str) -> Dict[str, Any]:
    """
    Generate GitHub Actions workflow configuration based on tech stack.
    
    Args:
        tech_stack: Selected tech stack
        project_name: Project name for workflow customization
        
    Returns:
        GitHub workflow configuration
    """
    # Define workflow templates by tech stack
    workflow_templates = {
        'react_spa': {
            'name': 'React SPA CI/CD',
            'file_name': 'react-spa.yml',
            'template_path': 'github-workflows/react-spa.yml',
            'node_version': '18'
        },
        'node_api': {
            'name': 'Node.js API CI/CD',
            'file_name': 'node-api.yml', 
            'template_path': 'github-workflows/node-api.yml',
            'node_version': '18'
        },
        'python_api': {
            'name': 'Python API CI/CD',
            'file_name': 'python-api.yml',
            'template_path': 'github-workflows/python-api.yml',
            'python_version': '3.11'
        },
        'vue_spa': {
            'name': 'Vue SPA CI/CD',
            'file_name': 'vue-spa.yml',
            'template_path': 'github-workflows/vue-spa.yml',
            'node_version': '18'
        },
        'react_fullstack': {
            'name': 'React Fullstack CI/CD',
            'file_name': 'react-fullstack.yml',
            'template_path': 'github-workflows/react-fullstack.yml',
            'node_version': '18'
        }
    }
    
    template = workflow_templates.get(tech_stack.lower())
    if not template:
        template = workflow_templates['react_fullstack']  # Default fallback
    
    return {
        'tech_stack': tech_stack,
        'workflow_name': template['name'],
        'workflow_file': template['file_name'],
        'template_path': template['template_path'],
        'project_name': project_name,
        'triggers': ['push', 'pull_request'],
        'node_version': template.get('node_version'),
        'python_version': template.get('python_version'),
        'build_commands': get_build_commands(tech_stack),
        'deployment_target': get_deployment_target(tech_stack)
    }


def validate_lock_files(generated_files: List[Dict[str, Any]], tech_stack: str) -> Dict[str, Any]:
    """
    Validate that required dependency lock files are present for the tech stack.
    
    Args:
        generated_files: List of generated file metadata
        tech_stack: Selected tech stack
        
    Returns:
        Validation result with lock file validation results
    """
    try:
        # Define required lock files by tech stack
        required_lock_files = {
            'react_spa': ['package-lock.json', 'yarn.lock'],  # Either one is acceptable
            'react_fullstack': ['package-lock.json', 'yarn.lock'],
            'node_api': ['package-lock.json', 'yarn.lock'],
            'vue_spa': ['package-lock.json', 'yarn.lock'],
            'python_api': ['requirements.txt', 'poetry.lock', 'Pipfile.lock']  # Multiple options
        }
        
        generated_file_paths = {file.get('file_path') for file in generated_files}
        expected_lock_files = required_lock_files.get(tech_stack.lower(), ['package-lock.json'])
        
        issues = []
        
        # Check if ANY of the expected lock files are present
        if tech_stack.lower() in ['react_spa', 'react_fullstack', 'node_api', 'vue_spa']:
            # For Node.js-based stacks, we need either package-lock.json OR yarn.lock
            has_npm_lock = 'package-lock.json' in generated_file_paths
            has_yarn_lock = 'yarn.lock' in generated_file_paths
            has_package_json = 'package.json' in generated_file_paths
            
            if not has_package_json:
                issues.append("Missing package.json - required for Node.js projects")
            
            # NOTE: package-lock.json is NOT required because GitHub Actions will generate it
            # automatically during "npm install". The GitHub orchestrator intentionally 
            # skips generating it to avoid conflicts with npm ci.
            if not has_yarn_lock and 'yarn' in str(generated_file_paths):
                issues.append(
                    f"Yarn project detected but missing yarn.lock for {tech_stack}. "
                    f"Consider including yarn.lock for reproducible builds."
                )
            # For npm projects, package-lock.json will be auto-generated - no validation needed
        
        elif tech_stack.lower() == 'python_api':
            # For Python, check for requirements.txt at minimum
            has_requirements = 'requirements.txt' in generated_file_paths
            has_poetry_lock = 'poetry.lock' in generated_file_paths
            has_pipfile_lock = 'Pipfile.lock' in generated_file_paths
            
            if not has_requirements:
                issues.append("Missing requirements.txt - required for Python projects")
            
            if not (has_poetry_lock or has_pipfile_lock):
                issues.append(
                    f"Missing dependency lock file for Python project. "
                    f"Consider adding poetry.lock or Pipfile.lock for reproducible builds."
                )
        
        return {
            'validation_type': 'lock_file_validation',
            'passed': len(issues) == 0,
            'issues': issues,
            'details': {
                'tech_stack': tech_stack,
                'note': 'package-lock.json not required - GitHub Actions auto-generates it',
                'generated_files_count': len(generated_files),
                'has_package_json': 'package.json' in generated_file_paths,
                'has_package_lock': 'package-lock.json' in generated_file_paths,
                'has_yarn_lock': 'yarn.lock' in generated_file_paths
            }
        }
        
    except Exception as e:
        return {
            'validation_type': 'lock_file_validation',
            'passed': False,
            'issues': [f"Lock file validation failed: {str(e)}"],
            'details': {}
        }


def validate_build_requirements(generated_files: List[Dict[str, Any]], tech_stack: str, architecture: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that all required build files and configuration are present.
    
    Args:
        generated_files: List of generated file metadata
        tech_stack: Selected tech stack
        architecture: Project architecture configuration
        
    Returns:
        Validation result with build requirements validation results
    """
    try:
        generated_file_paths = {file.get('file_path') for file in generated_files}
        issues = []
        
        # Define required build files by tech stack
        required_build_files = {
            'react_spa': {
                'required': ['package.json'],
                'recommended': ['vite.config.ts', 'tsconfig.json', '.eslintrc.json', '.gitignore']
            },
            'react_fullstack': {
                'required': ['package.json'],
                'recommended': ['vite.config.ts', 'tsconfig.json', '.eslintrc.json', '.gitignore']
            },
            'node_api': {
                'required': ['package.json'],
                'recommended': ['tsconfig.json', '.eslintrc.json', '.gitignore', 'nodemon.json']
            },
            'vue_spa': {
                'required': ['package.json'],
                'recommended': ['vite.config.ts', 'tsconfig.json', '.eslintrc.json', '.gitignore']
            },
            'python_api': {
                'required': ['requirements.txt'],
                'recommended': ['pyproject.toml', '.gitignore', 'Dockerfile']
            }
        }
        
        build_files = required_build_files.get(tech_stack.lower(), {'required': ['package.json'], 'recommended': []})
        
        # Check required files
        for required_file in build_files['required']:
            if required_file not in generated_file_paths:
                issues.append(f"Missing required build file: {required_file}")
        
        # Check recommended files (warnings, not failures)
        missing_recommended = []
        for recommended_file in build_files['recommended']:
            if recommended_file not in generated_file_paths:
                missing_recommended.append(recommended_file)
        
        # Validate package.json content for Node.js-based projects
        if tech_stack.lower() in ['react_spa', 'react_fullstack', 'node_api', 'vue_spa']:
            # For react_fullstack, check both root and workspace package.json files
            package_files_to_check = []
            
            if tech_stack.lower() == 'react_fullstack':
                # Check root, client, and server package.json files
                for path in ['package.json', 'client/package.json', 'server/package.json']:
                    pkg_file = next((f for f in generated_files if f.get('file_path') == path), None)
                    if pkg_file:
                        package_files_to_check.append((path, pkg_file))
            else:
                # For other tech stacks, just check root package.json
                pkg_file = next((f for f in generated_files if f.get('file_path') == 'package.json'), None)
                if pkg_file:
                    package_files_to_check.append(('package.json', pkg_file))
            
            for file_path, package_json_file in package_files_to_check:
                try:
                    import json
                    # Retrieve content from S3 if using metadata pattern
                    if 's3_bucket' in package_json_file and 's3_key' in package_json_file:
                        content = retrieve_file_content_from_s3(package_json_file)
                    else:
                        # Backward compatibility - content might be inline
                        content = package_json_file.get('content', '{}')
                    
                    package_content = json.loads(content if content else '{}')
                    
                    # Check for required scripts - flexible to handle different React project patterns
                    scripts = package_content.get('scripts', {})
                    
                    # Always require build script
                    if 'build' not in scripts:
                        issues.append(f"Missing required script in {file_path}: build")
                    
                    # Check for development script - accept 'dev', 'start', or 'develop'
                    dev_scripts = ['dev', 'start', 'develop']
                    has_dev_script = any(script in scripts for script in dev_scripts)
                    if not has_dev_script:
                        issues.append(f"Missing development script in {file_path}: requires one of {dev_scripts}")
                    
                    # For server packages specifically, require start script
                    if 'server' in file_path and 'start' not in scripts:
                        issues.append(f"Missing required script in {file_path}: start (required for server packages)")
                    
                    # Check for dependencies - but allow empty for monorepo root
                    # Monorepos (react_fullstack) may have empty dependencies at root with workspaces
                    is_monorepo = 'workspaces' in package_content
                    dependencies = package_content.get('dependencies', {})
                    
                    # Only require dependencies if not a monorepo structure and not root package.json in fullstack
                    if not dependencies and not is_monorepo and not (tech_stack.lower() == 'react_fullstack' and file_path == 'package.json'):
                        issues.append(f"{file_path} has no dependencies defined")
                        
                except json.JSONDecodeError:
                    issues.append(f"{file_path} contains invalid JSON")
                except Exception as e:
                    issues.append(f"Failed to validate {file_path}: {str(e)}")
        
        # Check build configuration consistency
        build_config = architecture.get('build_config', {})
        expected_package_manager = build_config.get('package_manager', 'npm')
        
        if tech_stack.lower() in ['react_spa', 'react_fullstack', 'node_api', 'vue_spa']:
            # Validate package manager consistency
            if expected_package_manager == 'npm' and 'yarn.lock' in generated_file_paths:
                issues.append("Build config specifies npm but yarn.lock found - package manager mismatch")
            elif expected_package_manager == 'yarn' and 'package-lock.json' in generated_file_paths:
                issues.append("Build config specifies yarn but package-lock.json found - package manager mismatch")
        
        return {
            'validation_type': 'build_requirements_validation',
            'passed': len(issues) == 0,
            'issues': issues,
            'warnings': [f"Missing recommended file: {f}" for f in missing_recommended] if missing_recommended else [],
            'details': {
                'tech_stack': tech_stack,
                'required_files': build_files['required'],
                'recommended_files': build_files['recommended'],
                'missing_recommended': missing_recommended,
                'package_manager': expected_package_manager,
                'generated_files_count': len(generated_files)
            }
        }
        
    except Exception as e:
        return {
            'validation_type': 'build_requirements_validation',
            'passed': False,
            'issues': [f"Build requirements validation failed: {str(e)}"],
            'details': {}
        }


def get_build_commands(tech_stack: str) -> List[str]:
    """Get build commands for the tech stack."""
    build_commands = {
        'react_spa': ['npm install', 'npm run build', 'npm test'],
        'react_fullstack': ['npm install', 'npm run build', 'npm test'],
        'node_api': ['npm install', 'npm run build', 'npm test'],
        'vue_spa': ['npm install', 'npm run build', 'npm test'],
        'python_api': ['pip install -r requirements.txt', 'python -m pytest', 'python -m build']
    }
    return build_commands.get(tech_stack.lower(), ['npm install', 'npm run build', 'npm test'])


def get_deployment_target(tech_stack: str) -> str:
    """Get deployment target for the tech stack."""
    deployment_targets = {
        'react_spa': 'netlify',
        'react_fullstack': 'netlify_and_aws',
        'node_api': 'aws_ecs',
        'vue_spa': 'netlify', 
        'python_api': 'aws_ecs'
    }
    return deployment_targets.get(tech_stack.lower(), 'netlify')