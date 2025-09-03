"""
Integration Validator Lambda (Refactored for Incremental Validation)

Performs incremental validation after each story completion rather than waiting
for all stories to be generated. This enables early detection and fixing of issues.

Author: AI Pipeline Orchestrator v2
Version: 2.0.0 (Sequential Story Validation)
"""

import json
import os
from typing import Dict, Any, List, Optional, Tuple
import boto3
from datetime import datetime
import hashlib

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Import shared services
import sys
sys.path.append('/opt/python')
from shared.services.auto_fix_service import AutoFixService
from shared.utils.logger import setup_logger, log_lambda_start, log_lambda_end, log_error

logger = setup_logger("integration-validator")


class IncrementalIntegrationValidator:
    """
    Handles incremental validation of generated components after each story.
    Validates integration points, consistency, and cumulative build integrity.
    """
    
    def __init__(self):
        self.s3_client = s3_client
        self.dynamodb = dynamodb
        self.auto_fix_service = AutoFixService()
        
        # Get configuration from environment
        self.processed_bucket = os.environ.get('PROCESSED_BUCKET_NAME')
        self.component_table = os.environ.get('COMPONENT_SPECS_TABLE', 'ai-pipeline-v2-component-specs-dev')
        self.validation_config_bucket = os.environ.get('CONFIG_BUCKET', self.processed_bucket)
        
        # Load validation configuration
        self.validation_config = self._load_validation_config()
    
    def _load_validation_config(self) -> Dict[str, Any]:
        """Load validation configuration from S3 or use defaults."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.validation_config_bucket,
                Key='config/validation-config.json'
            )
            return json.loads(response['Body'].read().decode('utf-8'))
        except Exception as e:
            logger.warning(f"Could not load validation config: {e}, using defaults")
            return {
                "incremental_validation": {
                    "enabled": True,
                    "validate_after_each_story": True,
                    "auto_fix_enabled": True,
                    "max_fix_attempts": 2
                },
                "validation_levels": {
                    "syntax": True,
                    "imports": True,
                    "types": True,
                    "integration": True,
                    "consistency": True
                }
            }
    
    def validate_story_increment(
        self,
        story_files: List[Dict[str, Any]],
        existing_files: List[Dict[str, Any]],
        story_metadata: Dict[str, Any],
        architecture: Dict[str, Any],
        project_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform incremental validation for a single story's output.
        
        Args:
            story_files: Files generated for the current story
            existing_files: Previously generated files from earlier stories
            story_metadata: Metadata about the current story
            architecture: Project architecture specification
            project_context: Overall project context
            
        Returns:
            Validation result with issues and fixes if applicable
        """
        execution_id = f"inc_val_{story_metadata.get('story_id')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Starting incremental validation for story: {story_metadata.get('title')}")
        
        validation_results = []
        all_files = existing_files + story_files
        
        # 1. Validate new files don't break existing imports
        import_validation = self._validate_import_consistency(
            story_files, existing_files, architecture
        )
        validation_results.append(import_validation)
        
        # 2. Validate component interfaces match expectations
        interface_validation = self._validate_component_interfaces(
            story_files, existing_files, story_metadata, architecture
        )
        validation_results.append(interface_validation)
        
        # 3. Validate no duplicate exports or conflicting names
        export_validation = self._validate_export_consistency(
            story_files, existing_files
        )
        validation_results.append(export_validation)
        
        # 4. Validate dependency graph integrity
        dependency_validation = self._validate_dependency_graph(
            all_files, architecture
        )
        validation_results.append(dependency_validation)
        
        # 5. Validate TypeScript types if applicable
        if architecture.get('tech_stack') in ['react_spa', 'react_fullstack', 'node_api']:
            type_validation = self._validate_typescript_consistency(
                story_files, existing_files, architecture
            )
            validation_results.append(type_validation)
        
        # 6. Validate file structure consistency
        structure_validation = self._validate_file_structure(
            story_files, architecture, story_metadata
        )
        validation_results.append(structure_validation)
        
        # Calculate validation summary
        validation_passed = all(result.get('passed', False) for result in validation_results)
        issues = []
        for result in validation_results:
            issues.extend(result.get('issues', []))
        
        validation_summary = {
            'execution_id': execution_id,
            'story_id': story_metadata.get('story_id'),
            'story_title': story_metadata.get('title'),
            'validation_passed': validation_passed,
            'total_validations': len(validation_results),
            'failed_validations': len([r for r in validation_results if not r.get('passed', False)]),
            'total_issues': len(issues),
            'validation_results': validation_results,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # If validation failed and auto-fix is enabled, attempt fixes
        if not validation_passed and self.validation_config.get('incremental_validation', {}).get('auto_fix_enabled', True):
            logger.info(f"Validation failed with {len(issues)} issues, attempting auto-fix")
            
            fix_result = self._attempt_auto_fix(
                validation_summary,
                story_files,
                existing_files,
                story_metadata,
                architecture
            )
            
            if fix_result.get('fixes_applied'):
                validation_summary['auto_fix_applied'] = True
                validation_summary['fixed_files'] = fix_result.get('fixed_files', [])
                validation_summary['fix_summary'] = fix_result.get('summary')
                
                # Re-validate after fixes
                revalidation_result = self.validate_story_increment(
                    fix_result.get('fixed_files', story_files),
                    existing_files,
                    story_metadata,
                    architecture,
                    project_context
                )
                
                validation_summary['revalidation_result'] = revalidation_result
                validation_summary['final_validation_passed'] = revalidation_result.get('validation_passed', False)
        
        # Store validation results
        self._store_validation_results(validation_summary, project_context)
        
        return validation_summary
    
    def _validate_import_consistency(
        self,
        new_files: List[Dict[str, Any]],
        existing_files: List[Dict[str, Any]],
        architecture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate that new files don't break existing import chains.
        """
        issues = []
        all_files = existing_files + new_files
        file_map = {f.get('file_path'): f for f in all_files}
        
        # Check imports in new files
        for new_file in new_files:
            file_path = new_file.get('file_path')
            content = self._get_file_content(new_file)
            
            if not content:
                continue
            
            # Extract imports (simplified - would need proper parsing in production)
            import_patterns = [
                r"import .* from ['\"](.+)['\"]",
                r"require\(['\"](.+)['\"]\)",
                r"from (['\"].+['\"])"
            ]
            
            for pattern in import_patterns:
                import re
                matches = re.findall(pattern, content)
                for import_path in matches:
                    # Clean import path
                    import_path = import_path.strip('"\'')
                    
                    # Skip external packages
                    if not import_path.startswith('.'):
                        continue
                    
                    # Resolve relative import
                    resolved_path = self._resolve_import_path(file_path, import_path)
                    
                    # Check if imported file exists
                    if resolved_path not in file_map:
                        issues.append({
                            'type': 'missing_import',
                            'file': file_path,
                            'import': import_path,
                            'resolved_path': resolved_path,
                            'message': f"Import '{import_path}' in {file_path} cannot be resolved"
                        })
        
        # Check if new files break existing imports
        for existing_file in existing_files:
            file_path = existing_file.get('file_path')
            content = self._get_file_content(existing_file)
            
            if not content:
                continue
            
            # Check if any new file shadows or conflicts with existing imports
            # This is a simplified check - production would need more sophisticated analysis
            
        return {
            'validation_type': 'import_consistency',
            'passed': len(issues) == 0,
            'issues': issues,
            'details': {
                'new_files_checked': len(new_files),
                'existing_files_checked': len(existing_files),
                'total_issues': len(issues)
            }
        }
    
    def _validate_component_interfaces(
        self,
        new_files: List[Dict[str, Any]],
        existing_files: List[Dict[str, Any]],
        story_metadata: Dict[str, Any],
        architecture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate that component interfaces match architectural expectations.
        """
        issues = []
        
        # Get expected interfaces from story metadata
        expected_interfaces = story_metadata.get('interfaces', [])
        component_specs = story_metadata.get('component_specs', [])
        
        for new_file in new_files:
            file_path = new_file.get('file_path')
            content = self._get_file_content(new_file)
            
            if not content:
                continue
            
            # Check for expected exports
            for spec in component_specs:
                if spec.get('file_path') == file_path:
                    expected_exports = spec.get('exports', [])
                    
                    for export_name in expected_exports:
                        # Simple check for export presence
                        export_patterns = [
                            f"export.*{export_name}",
                            f"module.exports.*{export_name}",
                            f"exports.{export_name}"
                        ]
                        
                        found = False
                        for pattern in export_patterns:
                            import re
                            if re.search(pattern, content):
                                found = True
                                break
                        
                        if not found:
                            issues.append({
                                'type': 'missing_export',
                                'file': file_path,
                                'export': export_name,
                                'message': f"Expected export '{export_name}' not found in {file_path}"
                            })
        
        return {
            'validation_type': 'component_interfaces',
            'passed': len(issues) == 0,
            'issues': issues,
            'details': {
                'expected_interfaces': len(expected_interfaces),
                'files_validated': len(new_files),
                'total_issues': len(issues)
            }
        }
    
    def _validate_export_consistency(
        self,
        new_files: List[Dict[str, Any]],
        existing_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate no duplicate exports or naming conflicts.
        """
        issues = []
        all_exports = {}
        
        # Collect exports from existing files
        for file in existing_files:
            file_path = file.get('file_path')
            exports = self._extract_exports(file)
            for export_name in exports:
                if export_name in all_exports:
                    all_exports[export_name].append(file_path)
                else:
                    all_exports[export_name] = [file_path]
        
        # Check new files for conflicts
        for file in new_files:
            file_path = file.get('file_path')
            exports = self._extract_exports(file)
            
            for export_name in exports:
                if export_name in all_exports:
                    issues.append({
                        'type': 'duplicate_export',
                        'export': export_name,
                        'new_file': file_path,
                        'existing_files': all_exports[export_name],
                        'message': f"Export '{export_name}' already exists in {all_exports[export_name]}"
                    })
        
        return {
            'validation_type': 'export_consistency',
            'passed': len(issues) == 0,
            'issues': issues,
            'details': {
                'total_exports': len(all_exports),
                'new_files_checked': len(new_files),
                'conflicts_found': len(issues)
            }
        }
    
    def _validate_dependency_graph(
        self,
        all_files: List[Dict[str, Any]],
        architecture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the dependency graph has no cycles and all dependencies exist.
        """
        issues = []
        dependency_graph = {}
        
        # Build dependency graph
        for file in all_files:
            file_path = file.get('file_path')
            dependencies = self._extract_dependencies(file)
            dependency_graph[file_path] = dependencies
        
        # Check for cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle(node, graph, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, graph, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in dependency_graph:
            if node not in visited:
                if has_cycle(node, dependency_graph, visited, rec_stack):
                    issues.append({
                        'type': 'circular_dependency',
                        'file': node,
                        'message': f"Circular dependency detected involving {node}"
                    })
        
        return {
            'validation_type': 'dependency_graph',
            'passed': len(issues) == 0,
            'issues': issues,
            'details': {
                'total_files': len(all_files),
                'dependency_edges': sum(len(deps) for deps in dependency_graph.values()),
                'cycles_detected': len(issues)
            }
        }
    
    def _validate_typescript_consistency(
        self,
        new_files: List[Dict[str, Any]],
        existing_files: List[Dict[str, Any]],
        architecture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate TypeScript type consistency across files.
        """
        issues = []
        
        # Collect type definitions from existing files
        existing_types = {}
        for file in existing_files:
            if file.get('file_path', '').endswith(('.ts', '.tsx')):
                types = self._extract_type_definitions(file)
                existing_types.update(types)
        
        # Check new files for type conflicts
        for file in new_files:
            if file.get('file_path', '').endswith(('.ts', '.tsx')):
                types = self._extract_type_definitions(file)
                
                for type_name, type_def in types.items():
                    if type_name in existing_types:
                        if type_def != existing_types[type_name]:
                            issues.append({
                                'type': 'type_conflict',
                                'type_name': type_name,
                                'file': file.get('file_path'),
                                'message': f"Type '{type_name}' conflicts with existing definition"
                            })
        
        return {
            'validation_type': 'typescript_consistency',
            'passed': len(issues) == 0,
            'issues': issues,
            'details': {
                'existing_types': len(existing_types),
                'new_files_checked': len([f for f in new_files if f.get('file_path', '').endswith(('.ts', '.tsx'))]),
                'type_conflicts': len(issues)
            }
        }
    
    def _validate_file_structure(
        self,
        new_files: List[Dict[str, Any]],
        architecture: Dict[str, Any],
        story_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate files follow the expected directory structure.
        """
        issues = []
        
        # Get expected structure from architecture
        expected_structure = architecture.get('directory_structure', {})
        tech_stack = architecture.get('tech_stack')
        
        # Define expected patterns by tech stack
        structure_patterns = {
            'react_spa': {
                'components': r'^src/components/',
                'pages': r'^src/pages/',
                'utils': r'^src/utils/',
                'services': r'^src/services/',
                'styles': r'^src/styles/'
            },
            'react_fullstack': {
                'client': r'^client/',
                'server': r'^server/',
                'shared': r'^shared/'
            },
            'node_api': {
                'routes': r'^src/routes/',
                'controllers': r'^src/controllers/',
                'models': r'^src/models/',
                'middleware': r'^src/middleware/'
            }
        }
        
        patterns = structure_patterns.get(tech_stack, {})
        
        for file in new_files:
            file_path = file.get('file_path')
            component_type = file.get('component_type', '')
            
            # Check if file matches expected pattern
            matched = False
            for pattern_type, pattern in patterns.items():
                import re
                if re.match(pattern, file_path):
                    matched = True
                    break
            
            if not matched and component_type in patterns:
                issues.append({
                    'type': 'structure_violation',
                    'file': file_path,
                    'expected_pattern': patterns.get(component_type),
                    'message': f"File {file_path} doesn't match expected structure for {component_type}"
                })
        
        return {
            'validation_type': 'file_structure',
            'passed': len(issues) == 0,
            'issues': issues,
            'details': {
                'tech_stack': tech_stack,
                'files_checked': len(new_files),
                'structure_violations': len(issues)
            }
        }
    
    def _attempt_auto_fix(
        self,
        validation_summary: Dict[str, Any],
        story_files: List[Dict[str, Any]],
        existing_files: List[Dict[str, Any]],
        story_metadata: Dict[str, Any],
        architecture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Attempt to automatically fix validation issues.
        """
        # Prepare error analysis for auto-fix service
        error_analysis = {
            'validation_summary': validation_summary,
            'issues': [],
            'story_context': story_metadata,
            'architecture': architecture
        }
        
        # Categorize issues for targeted fixes
        for result in validation_summary.get('validation_results', []):
            if not result.get('passed'):
                for issue in result.get('issues', []):
                    error_analysis['issues'].append({
                        'category': result.get('validation_type'),
                        'issue': issue
                    })
        
        # Generate fixes using auto-fix service
        fix_result = self.auto_fix_service.generate_fixes(
            error_analysis,
            story_files,
            existing_files,
            story_metadata
        )
        
        return fix_result
    
    def _get_file_content(self, file: Dict[str, Any]) -> str:
        """Retrieve file content from S3 or inline."""
        if 's3_bucket' in file and 's3_key' in file:
            try:
                response = self.s3_client.get_object(
                    Bucket=file['s3_bucket'],
                    Key=file['s3_key']
                )
                return response['Body'].read().decode('utf-8')
            except Exception as e:
                logger.error(f"Failed to retrieve file from S3: {e}")
                return ''
        return file.get('content', '')
    
    def _resolve_import_path(self, from_file: str, import_path: str) -> str:
        """Resolve relative import path to absolute path."""
        import os
        from_dir = os.path.dirname(from_file)
        resolved = os.path.normpath(os.path.join(from_dir, import_path))
        
        # Add common extensions if not present
        if not os.path.splitext(resolved)[1]:
            # Try common extensions
            for ext in ['.ts', '.tsx', '.js', '.jsx', '/index.ts', '/index.tsx']:
                potential_path = resolved + ext
                # In real implementation, would check if file exists
                # For now, return the first potential match
                return potential_path
        
        return resolved
    
    def _extract_exports(self, file: Dict[str, Any]) -> List[str]:
        """Extract export names from a file."""
        content = self._get_file_content(file)
        exports = []
        
        if not content:
            return exports
        
        # Simple regex patterns for exports
        import re
        patterns = [
            r"export\s+(?:const|let|var|function|class)\s+(\w+)",
            r"export\s+{\s*([^}]+)\s*}",
            r"module\.exports\s*=\s*{\s*([^}]+)\s*}",
            r"exports\.(\w+)\s*="
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if ',' in match:
                    # Handle multiple exports
                    exports.extend([e.strip() for e in match.split(',')])
                else:
                    exports.append(match)
        
        return exports
    
    def _extract_dependencies(self, file: Dict[str, Any]) -> List[str]:
        """Extract dependencies from a file."""
        content = self._get_file_content(file)
        dependencies = []
        
        if not content:
            return dependencies
        
        import re
        patterns = [
            r"import.*from\s+['\"]([^'\"]+)['\"]",
            r"require\(['\"]([^'\"]+)['\"]\)"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if match.startswith('.'):
                    # Resolve relative import
                    resolved = self._resolve_import_path(file.get('file_path'), match)
                    dependencies.append(resolved)
        
        return dependencies
    
    def _extract_type_definitions(self, file: Dict[str, Any]) -> Dict[str, str]:
        """Extract TypeScript type definitions from a file."""
        content = self._get_file_content(file)
        types = {}
        
        if not content:
            return types
        
        import re
        patterns = [
            r"(?:export\s+)?(?:interface|type)\s+(\w+)",
            r"(?:export\s+)?enum\s+(\w+)"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Store a simplified hash of the type definition
                # In production, would parse the actual type definition
                types[match] = hashlib.md5(content.encode()).hexdigest()[:8]
        
        return types
    
    def _store_validation_results(
        self,
        validation_summary: Dict[str, Any],
        project_context: Dict[str, Any]
    ):
        """Store validation results in DynamoDB and S3."""
        try:
            # Store in DynamoDB
            table = self.dynamodb.Table(self.component_table)
            table.put_item(Item={
                'component_id': f"inc-val-{validation_summary['execution_id']}",
                'validation_summary': validation_summary,
                'project_id': project_context.get('project_id'),
                'story_id': validation_summary.get('story_id'),
                'timestamp': validation_summary.get('timestamp'),
                'ttl': int(datetime.utcnow().timestamp()) + (30 * 24 * 60 * 60)
            })
            
            # Store detailed results in S3
            s3_key = f"incremental-validation/{project_context.get('project_id')}/{validation_summary['story_id']}/validation-result.json"
            self.s3_client.put_object(
                Bucket=self.processed_bucket,
                Key=s3_key,
                Body=json.dumps(validation_summary, default=str),
                ContentType='application/json'
            )
            
            logger.info(f"Stored validation results: {s3_key}")
            
        except Exception as e:
            logger.error(f"Failed to store validation results: {e}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for incremental integration validation.
    
    This refactored version handles per-story validation instead of
    validating all stories at the end of the pipeline.
    """
    execution_id = log_lambda_start(event, context)
    
    try:
        validator = IncrementalIntegrationValidator()
        
        # Extract data from event
        if 'story_files' in event:
            # Direct invocation for single story validation
            story_files = event.get('story_files', [])
            existing_files = event.get('existing_files', [])
            story_metadata = event.get('story_metadata', {})
            architecture = event.get('architecture', {})
            project_context = event.get('project_context', {})
            
        elif 'storyExecutorResult' in event:
            # Step Functions format - extract from story executor result  
            story_result = event.get('storyExecutorResult', {}).get('Payload', {})
            data = story_result.get('data', {})
            
            story_files = data.get('generated_files', [])
            existing_files = data.get('existing_files', [])
            story_metadata = data.get('story_metadata', {})
            architecture = data.get('architecture', {})
            project_context = data.get('pipeline_context', {})
            
        else:
            raise ValueError("Invalid event format - missing required data")
        
        # Perform incremental validation
        validation_result = validator.validate_story_increment(
            story_files,
            existing_files,
            story_metadata,
            architecture,
            project_context
        )
        
        # Prepare response
        validation_passed = validation_result.get('final_validation_passed', validation_result.get('validation_passed', False))
        
        response = {
            'status': 'success' if validation_passed else 'validation_failed',
            'message': f"Story validation {'passed' if validation_passed else 'failed'}",
            'execution_id': execution_id,
            'stage': 'incremental_integration_validation',
            'project_id': project_context.get('project_id'),
            'story_id': story_metadata.get('story_id'),
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'validation_result': validation_result,
                'validation_passed': validation_passed,
                'auto_fix_applied': validation_result.get('auto_fix_applied', False),
                'issues_found': validation_result.get('total_issues', 0),
                'issues_fixed': len(validation_result.get('fixed_files', [])) if validation_result.get('auto_fix_applied') else 0,
                'story_files': story_files if validation_passed else validation_result.get('fixed_files', story_files),
                'existing_files': existing_files,
                'story_metadata': story_metadata,
                'architecture': architecture,
                'project_context': project_context
            },
            'next_stage': 'build_orchestrator' if validation_passed else 'retry_story_generation'
        }
        
        log_lambda_end(execution_id, response)
        return response
        
    except Exception as e:
        error_msg = f"Incremental validation failed: {str(e)}"
        log_error(e, execution_id, "incremental_integration_validation")
        
        error_response = {
            'status': 'error',
            'message': error_msg,
            'execution_id': execution_id,
            'stage': 'incremental_integration_validation',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }
        
        log_lambda_end(execution_id, error_response)
        raise RuntimeError(error_msg)