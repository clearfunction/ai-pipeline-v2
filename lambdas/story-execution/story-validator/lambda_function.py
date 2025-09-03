"""
Story Validator Lambda

Validates individual story output immediately after generation.
Performs syntax, import, type, and build validation for a single story.

Author: AI Pipeline Orchestrator v2
Version: 2.0.0 (Sequential Processing)
"""

import json
import os
import subprocess
import tempfile
import shutil
from typing import Dict, Any, List, Optional, Tuple
import boto3
from datetime import datetime
import re

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

class StoryValidator:
    """
    Validates individual story output with multiple validation strategies.
    """
    
    def __init__(self):
        self.validation_config = self._load_validation_config()
        self.temp_dir = None
        
    def _load_validation_config(self) -> Dict[str, Any]:
        """Load validation configuration from environment or defaults."""
        return {
            'syntax_check': os.environ.get('ENABLE_SYNTAX_CHECK', 'true').lower() == 'true',
            'type_check': os.environ.get('ENABLE_TYPE_CHECK', 'true').lower() == 'true',
            'import_validation': os.environ.get('ENABLE_IMPORT_VALIDATION', 'true').lower() == 'true',
            'build_validation': os.environ.get('ENABLE_BUILD_VALIDATION', 'true').lower() == 'true',
            'test_execution': os.environ.get('ENABLE_TEST_EXECUTION', 'false').lower() == 'true',
            'max_errors_to_report': int(os.environ.get('MAX_ERRORS_TO_REPORT', '10'))
        }
    
    def validate_story(self, 
                      story_files: List[Dict[str, Any]], 
                      existing_files: List[Dict[str, Any]],
                      tech_stack: str,
                      story_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main validation method for a single story.
        
        Args:
            story_files: Files generated for this story
            existing_files: Files from previous stories
            tech_stack: Project technology stack
            story_metadata: Story information
            
        Returns:
            Validation result with pass/fail and detailed errors
        """
        validation_id = f"story_val_{story_metadata.get('story_id', 'unknown')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"Starting validation {validation_id} for story: {story_metadata.get('title', 'Unknown')}")
        print(f"Validating {len(story_files)} new files against {len(existing_files)} existing files")
        
        # Create temporary project structure
        self.temp_dir = tempfile.mkdtemp(prefix='story_validation_')
        validation_results = []
        
        try:
            # Set up project structure with all files
            self._setup_project_structure(story_files, existing_files, self.temp_dir)
            
            # Run validation steps
            if self.validation_config['syntax_check']:
                syntax_result = self._validate_syntax(story_files, tech_stack)
                validation_results.append(syntax_result)
            
            if self.validation_config['import_validation']:
                import_result = self._validate_imports(story_files, existing_files, tech_stack)
                validation_results.append(import_result)
            
            if self.validation_config['type_check'] and tech_stack in ['react_spa', 'react_fullstack', 'vue_spa']:
                type_result = self._validate_types()
                validation_results.append(type_result)
            
            if self.validation_config['build_validation']:
                build_result = self._validate_build(tech_stack)
                validation_results.append(build_result)
            
            if self.validation_config['test_execution']:
                test_result = self._run_tests(story_files)
                validation_results.append(test_result)
            
            # Aggregate results
            all_passed = all(result.get('passed', False) for result in validation_results)
            total_errors = sum(len(result.get('errors', [])) for result in validation_results)
            
            validation_summary = {
                'validation_id': validation_id,
                'story_id': story_metadata.get('story_id'),
                'story_title': story_metadata.get('title'),
                'passed': all_passed,
                'total_errors': total_errors,
                'validation_results': validation_results,
                'files_validated': len(story_files),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Store validation results
            self._store_validation_results(validation_summary)
            
            return validation_summary
            
        finally:
            # Clean up temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
    
    def _setup_project_structure(self, story_files: List[Dict[str, Any]], 
                                 existing_files: List[Dict[str, Any]], 
                                 temp_dir: str):
        """Set up temporary project structure with all files."""
        all_files = existing_files + story_files
        
        for file_data in all_files:
            file_path = file_data.get('file_path', '')
            content = file_data.get('content', '')
            
            if not file_path:
                continue
            
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        print(f"Set up project structure with {len(all_files)} files in {temp_dir}")
    
    def _validate_syntax(self, story_files: List[Dict[str, Any]], tech_stack: str) -> Dict[str, Any]:
        """Validate syntax of story files."""
        errors = []
        warnings = []
        
        for file_data in story_files:
            file_path = file_data.get('file_path', '')
            content = file_data.get('content', '')
            
            if file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                # Basic JavaScript/TypeScript syntax validation
                syntax_errors = self._check_javascript_syntax(content, file_path)
                errors.extend(syntax_errors)
            
            elif file_path.endswith('.json'):
                # JSON syntax validation
                try:
                    json.loads(content)
                except json.JSONDecodeError as e:
                    errors.append({
                        'file': file_path,
                        'line': e.lineno,
                        'error': f"Invalid JSON: {str(e)}",
                        'type': 'json_syntax'
                    })
            
            elif file_path.endswith(('.css', '.scss')):
                # Basic CSS syntax validation
                css_errors = self._check_css_syntax(content, file_path)
                errors.extend(css_errors)
        
        return {
            'validation_type': 'syntax',
            'passed': len(errors) == 0,
            'errors': errors[:self.validation_config['max_errors_to_report']],
            'warnings': warnings,
            'total_errors': len(errors)
        }
    
    def _validate_imports(self, story_files: List[Dict[str, Any]], 
                         existing_files: List[Dict[str, Any]], 
                         tech_stack: str) -> Dict[str, Any]:
        """Validate that all imports can be resolved."""
        errors = []
        all_files = {f['file_path']: f for f in existing_files + story_files}
        
        for file_data in story_files:
            file_path = file_data.get('file_path', '')
            content = file_data.get('content', '')
            
            if not file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                continue
            
            # Extract imports
            import_pattern = r"import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+)?['\"]([^'\"]+)['\"]"
            imports = re.findall(import_pattern, content)
            
            for import_path in imports:
                # Check if import can be resolved
                if import_path.startswith('.'):
                    # Relative import
                    resolved_path = self._resolve_relative_import(file_path, import_path, all_files)
                    if not resolved_path:
                        errors.append({
                            'file': file_path,
                            'import': import_path,
                            'error': f"Cannot resolve import: {import_path}",
                            'type': 'unresolved_import'
                        })
                elif not import_path.startswith('@') and '/' not in import_path:
                    # Node module import - check if it's in package.json
                    if not self._is_dependency_installed(import_path, all_files):
                        errors.append({
                            'file': file_path,
                            'import': import_path,
                            'error': f"Missing dependency: {import_path}",
                            'type': 'missing_dependency'
                        })
        
        return {
            'validation_type': 'imports',
            'passed': len(errors) == 0,
            'errors': errors[:self.validation_config['max_errors_to_report']],
            'total_errors': len(errors)
        }
    
    def _validate_types(self) -> Dict[str, Any]:
        """Run TypeScript type checking."""
        errors = []
        
        try:
            # Run TypeScript compiler in check mode
            result = subprocess.run(
                ['npx', 'tsc', '--noEmit', '--skipLibCheck'],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                # Parse TypeScript errors
                error_lines = result.stdout.split('\n') if result.stdout else result.stderr.split('\n')
                for line in error_lines:
                    if 'error TS' in line:
                        errors.append({
                            'error': line.strip(),
                            'type': 'typescript'
                        })
            
        except subprocess.TimeoutExpired:
            errors.append({
                'error': 'TypeScript validation timeout',
                'type': 'timeout'
            })
        except Exception as e:
            errors.append({
                'error': f"TypeScript validation failed: {str(e)}",
                'type': 'execution_error'
            })
        
        return {
            'validation_type': 'types',
            'passed': len(errors) == 0,
            'errors': errors[:self.validation_config['max_errors_to_report']],
            'total_errors': len(errors)
        }
    
    def _validate_build(self, tech_stack: str) -> Dict[str, Any]:
        """Validate that the project builds successfully."""
        errors = []
        
        try:
            # First, install dependencies
            npm_install = subprocess.run(
                ['npm', 'ci', '--prefer-offline', '--no-audit'],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if npm_install.returncode != 0:
                errors.append({
                    'error': 'Failed to install dependencies',
                    'details': npm_install.stderr[:500],
                    'type': 'dependency_installation'
                })
                return {
                    'validation_type': 'build',
                    'passed': False,
                    'errors': errors
                }
            
            # Run build command
            build_result = subprocess.run(
                ['npm', 'run', 'build'],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if build_result.returncode != 0:
                # Parse build errors
                error_output = build_result.stderr or build_result.stdout
                errors.append({
                    'error': 'Build failed',
                    'details': error_output[:1000],
                    'type': 'build_failure'
                })
            
        except subprocess.TimeoutExpired:
            errors.append({
                'error': 'Build timeout',
                'type': 'timeout'
            })
        except Exception as e:
            errors.append({
                'error': f"Build validation failed: {str(e)}",
                'type': 'execution_error'
            })
        
        return {
            'validation_type': 'build',
            'passed': len(errors) == 0,
            'errors': errors
        }
    
    def _run_tests(self, story_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run tests for the story files."""
        # Only run tests that are part of this story
        test_files = [f for f in story_files if 'test' in f['file_path'].lower() or 'spec' in f['file_path'].lower()]
        
        if not test_files:
            return {
                'validation_type': 'tests',
                'passed': True,
                'message': 'No tests to run for this story'
            }
        
        errors = []
        
        try:
            test_result = subprocess.run(
                ['npm', 'test', '--', '--passWithNoTests'],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if test_result.returncode != 0:
                errors.append({
                    'error': 'Tests failed',
                    'details': test_result.stdout[:1000],
                    'type': 'test_failure'
                })
            
        except Exception as e:
            errors.append({
                'error': f"Test execution failed: {str(e)}",
                'type': 'execution_error'
            })
        
        return {
            'validation_type': 'tests',
            'passed': len(errors) == 0,
            'errors': errors
        }
    
    def _check_javascript_syntax(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Basic JavaScript/TypeScript syntax checking."""
        errors = []
        lines = content.split('\n')
        
        # Check for common syntax errors
        open_braces = 0
        open_brackets = 0
        open_parens = 0
        
        for i, line in enumerate(lines, 1):
            # Count braces, brackets, parentheses
            open_braces += line.count('{') - line.count('}')
            open_brackets += line.count('[') - line.count(']')
            open_parens += line.count('(') - line.count(')')
            
            # Check for console.log in production code
            if 'console.log' in line and 'test' not in file_path.lower():
                errors.append({
                    'file': file_path,
                    'line': i,
                    'error': 'console.log found in production code',
                    'type': 'console_log'
                })
        
        # Check for unclosed braces/brackets/parens
        if open_braces != 0:
            errors.append({
                'file': file_path,
                'error': f"Unclosed braces: {open_braces} extra '{{' found",
                'type': 'unclosed_brace'
            })
        
        if open_brackets != 0:
            errors.append({
                'file': file_path,
                'error': f"Unclosed brackets: {open_brackets} extra '[' found",
                'type': 'unclosed_bracket'
            })
        
        if open_parens != 0:
            errors.append({
                'file': file_path,
                'error': f"Unclosed parentheses: {open_parens} extra '(' found",
                'type': 'unclosed_paren'
            })
        
        return errors
    
    def _check_css_syntax(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Basic CSS syntax checking."""
        errors = []
        
        # Check for unclosed braces
        open_braces = content.count('{') - content.count('}')
        if open_braces != 0:
            errors.append({
                'file': file_path,
                'error': f"Unclosed CSS braces: {open_braces} extra '{{' found",
                'type': 'unclosed_css_brace'
            })
        
        return errors
    
    def _resolve_relative_import(self, file_path: str, import_path: str, all_files: Dict[str, Any]) -> Optional[str]:
        """Resolve relative import path."""
        # Get directory of the importing file
        file_dir = os.path.dirname(file_path)
        
        # Resolve the import path
        resolved = os.path.normpath(os.path.join(file_dir, import_path))
        
        # Check with various extensions
        extensions = ['', '.ts', '.tsx', '.js', '.jsx', '/index.ts', '/index.tsx', '/index.js', '/index.jsx']
        
        for ext in extensions:
            check_path = resolved + ext
            if check_path in all_files:
                return check_path
        
        return None
    
    def _is_dependency_installed(self, package_name: str, all_files: Dict[str, Any]) -> bool:
        """Check if a package is in package.json dependencies."""
        package_json = all_files.get('package.json', {})
        if not package_json:
            return False
        
        try:
            content = json.loads(package_json.get('content', '{}'))
            dependencies = content.get('dependencies', {})
            dev_dependencies = content.get('devDependencies', {})
            
            # Extract base package name (handle scoped packages and sub-paths)
            base_package = package_name.split('/')[0]
            if package_name.startswith('@'):
                # Scoped package
                parts = package_name.split('/')
                base_package = '/'.join(parts[:2]) if len(parts) > 1 else parts[0]
            
            return base_package in dependencies or base_package in dev_dependencies
            
        except:
            return False
    
    def _store_validation_results(self, validation_summary: Dict[str, Any]):
        """Store validation results in S3 for analysis."""
        try:
            bucket = os.environ.get('PROCESSED_BUCKET_NAME', 'ai-pipeline-v2-processed-008537862626-us-east-1')
            key = f"validation-results/story/{validation_summary['validation_id']}.json"
            
            s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(validation_summary, default=str),
                ContentType='application/json'
            )
            
            print(f"Stored validation results: s3://{bucket}/{key}")
            
        except Exception as e:
            print(f"Warning: Failed to store validation results: {str(e)}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for story validation.
    
    Args:
        event: Contains story_files, existing_files, tech_stack, and story_metadata
        context: Lambda context
        
    Returns:
        Validation results with pass/fail status and detailed errors
    """
    try:
        print(f"Story Validator Lambda started: {context.request_id}")
        print(f"Event: {json.dumps(event, default=str)[:1000]}")
        
        # Extract parameters
        story_files = event.get('story_files', [])
        existing_files = event.get('existing_files', [])
        tech_stack = event.get('tech_stack', 'react_spa')
        story_metadata = event.get('story_metadata', {})
        
        if not story_files:
            return {
                'statusCode': 400,
                'status': 'error',
                'message': 'No story files provided for validation'
            }
        
        # Initialize validator and run validation
        validator = StoryValidator()
        validation_result = validator.validate_story(
            story_files=story_files,
            existing_files=existing_files,
            tech_stack=tech_stack,
            story_metadata=story_metadata
        )
        
        # Prepare response
        response = {
            'statusCode': 200,
            'status': 'success' if validation_result['passed'] else 'validation_failed',
            'data': validation_result,
            'message': f"Story validation {'passed' if validation_result['passed'] else 'failed'} with {validation_result.get('total_errors', 0)} errors"
        }
        
        print(f"Validation complete: {response['message']}")
        
        return response
        
    except Exception as e:
        error_message = f"Story validation error: {str(e)}"
        print(f"ERROR: {error_message}")
        
        return {
            'statusCode': 500,
            'status': 'error',
            'message': error_message,
            'error': str(e)
        }