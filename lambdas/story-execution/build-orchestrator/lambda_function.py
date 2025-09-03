"""
Build Orchestrator Lambda

Executes incremental builds in isolated environments and collects build errors.
Designed for sequential story processing with immediate feedback.

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
import tarfile
import io

# Initialize AWS clients
s3_client = boto3.client('s3')
ecs_client = boto3.client('ecs')
logs_client = boto3.client('logs')

class BuildOrchestrator:
    """
    Manages incremental builds for story validation.
    """
    
    def __init__(self):
        self.build_config = self._load_build_config()
        self.temp_dir = None
        self.build_errors = []
        self.build_warnings = []
        
    def _load_build_config(self) -> Dict[str, Any]:
        """Load build configuration from environment."""
        return {
            'timeout_seconds': int(os.environ.get('BUILD_TIMEOUT', '120')),
            'use_container': os.environ.get('USE_CONTAINER', 'false').lower() == 'true',
            'npm_registry': os.environ.get('NPM_REGISTRY', 'https://registry.npmjs.org'),
            'parallel_jobs': int(os.environ.get('PARALLEL_JOBS', '4')),
            'cache_dependencies': os.environ.get('CACHE_DEPENDENCIES', 'true').lower() == 'true'
        }
    
    def execute_incremental_build(self,
                                  story_files: List[Dict[str, Any]],
                                  existing_files: List[Dict[str, Any]],
                                  tech_stack: str,
                                  story_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute incremental build with new story files.
        
        Args:
            story_files: Files from current story
            existing_files: Files from previous stories
            tech_stack: Technology stack
            story_metadata: Story information
            
        Returns:
            Build result with success/failure and detailed errors
        """
        build_id = f"build_{story_metadata.get('story_id', 'unknown')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"Starting incremental build {build_id}")
        print(f"Tech stack: {tech_stack}, Story: {story_metadata.get('title', 'Unknown')}")
        
        self.temp_dir = tempfile.mkdtemp(prefix='build_orchestrator_')
        
        try:
            # Setup project with all files
            self._setup_build_environment(story_files, existing_files)
            
            # Determine build strategy based on tech stack
            build_strategy = self._get_build_strategy(tech_stack)
            
            # Execute build steps
            build_steps = []
            
            # Step 1: Dependency installation
            dep_result = self._install_dependencies(build_strategy)
            build_steps.append(dep_result)
            
            if dep_result['success']:
                # Step 2: Compilation/Build
                build_result = self._execute_build(build_strategy)
                build_steps.append(build_result)
                
                if build_result['success']:
                    # Step 3: Linting (non-blocking)
                    lint_result = self._run_linting(build_strategy)
                    build_steps.append(lint_result)
            
            # Analyze and categorize errors
            error_analysis = self._analyze_build_errors(build_steps)
            
            # Determine overall success
            build_success = all(step['success'] for step in build_steps if step.get('blocking', True))
            
            build_summary = {
                'build_id': build_id,
                'story_id': story_metadata.get('story_id'),
                'success': build_success,
                'build_steps': build_steps,
                'error_analysis': error_analysis,
                'total_errors': len(self.build_errors),
                'total_warnings': len(self.build_warnings),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Store build artifacts if successful
            if build_success:
                self._store_build_artifacts(build_id)
            
            return build_summary
            
        finally:
            # Cleanup
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
    
    def _setup_build_environment(self, story_files: List[Dict[str, Any]], 
                                 existing_files: List[Dict[str, Any]]):
        """Setup the build environment with all files."""
        all_files = existing_files + story_files
        
        for file_data in all_files:
            file_path = file_data.get('file_path', '')
            content = file_data.get('content', '')
            
            if not file_path:
                continue
            
            full_path = os.path.join(self.temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        print(f"Build environment setup with {len(all_files)} files")
        
        # Create .npmrc for faster installs
        if self.build_config['npm_registry']:
            npmrc_path = os.path.join(self.temp_dir, '.npmrc')
            with open(npmrc_path, 'w') as f:
                f.write(f"registry={self.build_config['npm_registry']}\n")
                f.write("prefer-offline=true\n")
                f.write("audit=false\n")
    
    def _get_build_strategy(self, tech_stack: str) -> Dict[str, Any]:
        """Get build strategy based on tech stack."""
        strategies = {
            'react_spa': {
                'package_manager': 'npm',
                'install_command': ['npm', 'ci', '--prefer-offline', '--no-audit'],
                'build_command': ['npm', 'run', 'build'],
                'lint_command': ['npm', 'run', 'lint'],
                'test_command': ['npm', 'test', '--', '--passWithNoTests']
            },
            'react_fullstack': {
                'package_manager': 'npm',
                'install_command': ['npm', 'ci', '--prefer-offline', '--no-audit'],
                'build_command': ['npm', 'run', 'build:all'],
                'lint_command': ['npm', 'run', 'lint'],
                'test_command': ['npm', 'test', '--', '--passWithNoTests']
            },
            'vue_spa': {
                'package_manager': 'npm',
                'install_command': ['npm', 'ci', '--prefer-offline', '--no-audit'],
                'build_command': ['npm', 'run', 'build'],
                'lint_command': ['npm', 'run', 'lint'],
                'test_command': ['npm', 'run', 'test:unit']
            },
            'node_api': {
                'package_manager': 'npm',
                'install_command': ['npm', 'ci', '--prefer-offline', '--no-audit'],
                'build_command': ['npm', 'run', 'build'],
                'lint_command': ['npm', 'run', 'lint'],
                'test_command': ['npm', 'test']
            }
        }
        
        return strategies.get(tech_stack, strategies['react_spa'])
    
    def _install_dependencies(self, build_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Install project dependencies."""
        print("Installing dependencies...")
        
        try:
            result = subprocess.run(
                build_strategy['install_command'],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=self.build_config['timeout_seconds']
            )
            
            if result.returncode != 0:
                # Parse npm errors
                errors = self._parse_npm_errors(result.stderr or result.stdout)
                self.build_errors.extend(errors)
                
                return {
                    'step': 'dependency_installation',
                    'success': False,
                    'errors': errors,
                    'blocking': True,
                    'output': result.stderr[:2000]
                }
            
            return {
                'step': 'dependency_installation',
                'success': True,
                'message': 'Dependencies installed successfully'
            }
            
        except subprocess.TimeoutExpired:
            error = {
                'type': 'timeout',
                'message': f"Dependency installation timed out after {self.build_config['timeout_seconds']}s"
            }
            self.build_errors.append(error)
            return {
                'step': 'dependency_installation',
                'success': False,
                'errors': [error],
                'blocking': True
            }
        except Exception as e:
            error = {
                'type': 'exception',
                'message': f"Dependency installation failed: {str(e)}"
            }
            self.build_errors.append(error)
            return {
                'step': 'dependency_installation',
                'success': False,
                'errors': [error],
                'blocking': True
            }
    
    def _execute_build(self, build_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the build command."""
        print("Executing build...")
        
        try:
            # Set environment variables for optimized build
            env = os.environ.copy()
            env['NODE_ENV'] = 'production'
            env['CI'] = 'true'
            
            result = subprocess.run(
                build_strategy['build_command'],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=self.build_config['timeout_seconds'],
                env=env
            )
            
            if result.returncode != 0:
                # Parse build errors
                errors = self._parse_build_errors(result.stderr or result.stdout)
                self.build_errors.extend(errors)
                
                return {
                    'step': 'build',
                    'success': False,
                    'errors': errors,
                    'blocking': True,
                    'output': result.stderr[:5000] if result.stderr else result.stdout[:5000]
                }
            
            # Check for build output
            build_dir = os.path.join(self.temp_dir, 'build')
            dist_dir = os.path.join(self.temp_dir, 'dist')
            
            if os.path.exists(build_dir) or os.path.exists(dist_dir):
                return {
                    'step': 'build',
                    'success': True,
                    'message': 'Build completed successfully',
                    'output_size': self._get_directory_size(build_dir if os.path.exists(build_dir) else dist_dir)
                }
            else:
                return {
                    'step': 'build',
                    'success': True,
                    'message': 'Build completed (no output directory expected for this project type)'
                }
            
        except subprocess.TimeoutExpired:
            error = {
                'type': 'timeout',
                'message': f"Build timed out after {self.build_config['timeout_seconds']}s"
            }
            self.build_errors.append(error)
            return {
                'step': 'build',
                'success': False,
                'errors': [error],
                'blocking': True
            }
        except Exception as e:
            error = {
                'type': 'exception',
                'message': f"Build failed: {str(e)}"
            }
            self.build_errors.append(error)
            return {
                'step': 'build',
                'success': False,
                'errors': [error],
                'blocking': True
            }
    
    def _run_linting(self, build_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Run linting (non-blocking)."""
        print("Running linting...")
        
        try:
            result = subprocess.run(
                build_strategy['lint_command'],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                # Parse lint warnings
                warnings = self._parse_lint_warnings(result.stdout or result.stderr)
                self.build_warnings.extend(warnings)
                
                return {
                    'step': 'linting',
                    'success': False,
                    'warnings': warnings,
                    'blocking': False  # Linting failures don't block
                }
            
            return {
                'step': 'linting',
                'success': True,
                'message': 'Linting passed'
            }
            
        except:
            # Linting failures are non-critical
            return {
                'step': 'linting',
                'success': False,
                'message': 'Linting skipped or failed',
                'blocking': False
            }
    
    def _parse_npm_errors(self, output: str) -> List[Dict[str, Any]]:
        """Parse NPM error output."""
        errors = []
        
        # Look for specific npm error patterns
        if 'ERESOLVE' in output:
            errors.append({
                'type': 'dependency_conflict',
                'message': 'Dependency resolution conflict',
                'details': self._extract_eresolve_error(output),
                'fixable': True
            })
        
        if 'Cannot find module' in output:
            module_pattern = r"Cannot find module '([^']+)'"
            modules = re.findall(module_pattern, output)
            for module in modules:
                errors.append({
                    'type': 'missing_module',
                    'module': module,
                    'message': f"Missing module: {module}",
                    'fixable': True
                })
        
        if 'npm ERR!' in output:
            npm_errors = output.split('npm ERR!')
            for npm_error in npm_errors[1:3]:  # Limit to first 2 errors
                errors.append({
                    'type': 'npm_error',
                    'message': npm_error.strip()[:200],
                    'fixable': False
                })
        
        return errors
    
    def _parse_build_errors(self, output: str) -> List[Dict[str, Any]]:
        """Parse build error output."""
        errors = []
        
        # TypeScript errors
        ts_pattern = r"(\S+\.tsx?)\((\d+),(\d+)\): error TS\d+: (.+)"
        ts_matches = re.findall(ts_pattern, output)
        for match in ts_matches[:10]:  # Limit to first 10
            errors.append({
                'type': 'typescript',
                'file': match[0],
                'line': int(match[1]),
                'column': int(match[2]),
                'message': match[3],
                'fixable': True
            })
        
        # Module not found errors
        if 'Module not found' in output:
            module_pattern = r"Module not found: (?:Error: )?Can't resolve '([^']+)'"
            modules = re.findall(module_pattern, output)
            for module in modules[:5]:
                errors.append({
                    'type': 'missing_import',
                    'module': module,
                    'message': f"Cannot resolve module: {module}",
                    'fixable': True
                })
        
        # Syntax errors
        if 'SyntaxError' in output:
            syntax_pattern = r"SyntaxError: (.+)"
            syntax_matches = re.findall(syntax_pattern, output)
            for match in syntax_matches[:3]:
                errors.append({
                    'type': 'syntax',
                    'message': match,
                    'fixable': True
                })
        
        return errors
    
    def _parse_lint_warnings(self, output: str) -> List[Dict[str, Any]]:
        """Parse linting warnings."""
        warnings = []
        
        # ESLint warnings
        eslint_pattern = r"(\S+)\s+(\d+):(\d+)\s+warning\s+(.+)"
        eslint_matches = re.findall(eslint_pattern, output)
        
        for match in eslint_matches[:20]:  # Limit warnings
            warnings.append({
                'type': 'eslint',
                'file': match[0],
                'line': int(match[1]),
                'column': int(match[2]),
                'message': match[3],
                'severity': 'warning'
            })
        
        return warnings
    
    def _extract_eresolve_error(self, output: str) -> str:
        """Extract ERESOLVE error details."""
        lines = output.split('\n')
        eresolve_section = []
        in_eresolve = False
        
        for line in lines:
            if 'ERESOLVE' in line:
                in_eresolve = True
            if in_eresolve:
                eresolve_section.append(line)
                if 'Fix the upstream dependency conflict' in line:
                    break
        
        return '\n'.join(eresolve_section[:10])  # Limit output
    
    def _analyze_build_errors(self, build_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze and categorize build errors for auto-fix."""
        error_categories = {
            'dependency_conflicts': [],
            'missing_modules': [],
            'typescript_errors': [],
            'syntax_errors': [],
            'import_errors': [],
            'other_errors': []
        }
        
        for step in build_steps:
            if not step.get('success', True):
                for error in step.get('errors', []):
                    error_type = error.get('type', 'other')
                    
                    if error_type == 'dependency_conflict':
                        error_categories['dependency_conflicts'].append(error)
                    elif error_type in ['missing_module', 'missing_import']:
                        error_categories['missing_modules'].append(error)
                    elif error_type == 'typescript':
                        error_categories['typescript_errors'].append(error)
                    elif error_type == 'syntax':
                        error_categories['syntax_errors'].append(error)
                    elif error_type == 'missing_import':
                        error_categories['import_errors'].append(error)
                    else:
                        error_categories['other_errors'].append(error)
        
        # Generate fix recommendations
        fix_recommendations = []
        
        if error_categories['dependency_conflicts']:
            fix_recommendations.append({
                'type': 'dependency_resolution',
                'action': 'resolve_conflicts',
                'errors': error_categories['dependency_conflicts']
            })
        
        if error_categories['missing_modules']:
            fix_recommendations.append({
                'type': 'add_dependencies',
                'action': 'install_missing',
                'modules': [e['module'] for e in error_categories['missing_modules']]
            })
        
        if error_categories['typescript_errors']:
            fix_recommendations.append({
                'type': 'fix_types',
                'action': 'correct_typescript',
                'errors': error_categories['typescript_errors'][:5]  # Limit to first 5
            })
        
        return {
            'error_categories': error_categories,
            'fix_recommendations': fix_recommendations,
            'fixable_count': sum(1 for cat in error_categories.values() for e in cat if e.get('fixable', False)),
            'total_errors': sum(len(cat) for cat in error_categories.values())
        }
    
    def _get_directory_size(self, path: str) -> int:
        """Get total size of directory in bytes."""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size
    
    def _store_build_artifacts(self, build_id: str):
        """Store build artifacts in S3."""
        try:
            # Create tar archive of build output
            build_dir = os.path.join(self.temp_dir, 'build')
            dist_dir = os.path.join(self.temp_dir, 'dist')
            
            output_dir = build_dir if os.path.exists(build_dir) else dist_dir
            
            if os.path.exists(output_dir):
                tar_buffer = io.BytesIO()
                with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
                    tar.add(output_dir, arcname=os.path.basename(output_dir))
                
                # Upload to S3
                bucket = os.environ.get('PROCESSED_BUCKET_NAME', 'ai-pipeline-v2-processed-008537862626-us-east-1')
                key = f"build-artifacts/{build_id}/build.tar.gz"
                
                tar_buffer.seek(0)
                s3_client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=tar_buffer.getvalue(),
                    ContentType='application/gzip'
                )
                
                print(f"Stored build artifacts: s3://{bucket}/{key}")
                
        except Exception as e:
            print(f"Warning: Failed to store build artifacts: {str(e)}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for build orchestration.
    
    Args:
        event: Contains story_files, existing_files, tech_stack, and story_metadata
        context: Lambda context
        
    Returns:
        Build results with success/failure and detailed errors
    """
    try:
        print(f"Build Orchestrator Lambda started: {context.request_id}")
        
        # Extract parameters
        story_files = event.get('story_files', [])
        existing_files = event.get('existing_files', [])
        tech_stack = event.get('tech_stack', 'react_spa')
        story_metadata = event.get('story_metadata', {})
        
        if not story_files:
            return {
                'statusCode': 200,
                'status': 'success',
                'message': 'No story files to build',
                'data': {
                    'success': True,
                    'build_skipped': True
                }
            }
        
        # Initialize orchestrator and execute build
        orchestrator = BuildOrchestrator()
        build_result = orchestrator.execute_incremental_build(
            story_files=story_files,
            existing_files=existing_files,
            tech_stack=tech_stack,
            story_metadata=story_metadata
        )
        
        # Prepare response
        response = {
            'statusCode': 200,
            'status': 'success' if build_result['success'] else 'build_failed',
            'data': build_result,
            'message': f"Build {'succeeded' if build_result['success'] else 'failed'} with {build_result.get('total_errors', 0)} errors"
        }
        
        print(f"Build complete: {response['message']}")
        
        return response
        
    except Exception as e:
        error_message = f"Build orchestration error: {str(e)}"
        print(f"ERROR: {error_message}")
        
        return {
            'statusCode': 500,
            'status': 'error',
            'message': error_message,
            'error': str(e)
        }