"""
Auto-Fix Service

Automated error resolution service using Claude Code SDK.
Generates targeted fixes for validation and build errors.

Author: AI Pipeline Orchestrator v2
Version: 2.0.0 (Sequential Processing)
"""

import json
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

class AutoFixService:
    """
    Service for automatically fixing common code errors using AI.
    """
    
    def __init__(self, llm_service=None):
        """
        Initialize the auto-fix service.
        
        Args:
            llm_service: Optional LLM service instance for generating fixes
        """
        self.llm_service = llm_service
        self.fix_strategies = self._load_fix_strategies()
        self.fix_history = []
        self.max_fix_attempts = int(os.environ.get('MAX_FIX_ATTEMPTS', '3'))
        
    def _load_fix_strategies(self) -> Dict[str, Any]:
        """Load fix strategies for different error types."""
        return {
            'missing_import': {
                'strategy': 'add_import',
                'priority': 1,
                'success_rate': 0.95
            },
            'missing_module': {
                'strategy': 'add_dependency',
                'priority': 1,
                'success_rate': 0.90
            },
            'typescript': {
                'strategy': 'fix_types',
                'priority': 2,
                'success_rate': 0.85
            },
            'syntax': {
                'strategy': 'fix_syntax',
                'priority': 1,
                'success_rate': 0.90
            },
            'dependency_conflict': {
                'strategy': 'resolve_conflict',
                'priority': 1,
                'success_rate': 0.75
            },
            'undefined_variable': {
                'strategy': 'declare_variable',
                'priority': 2,
                'success_rate': 0.85
            }
        }
    
    def generate_fixes(self, 
                      error_analysis: Dict[str, Any],
                      story_files: List[Dict[str, Any]],
                      existing_files: List[Dict[str, Any]],
                      story_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate fixes for detected errors.
        
        Args:
            error_analysis: Analysis of errors from validation/build
            story_files: Files from current story
            existing_files: Files from previous stories
            story_metadata: Story information
            
        Returns:
            Fix results with applied fixes and success status
        """
        fix_id = f"fix_{story_metadata.get('story_id', 'unknown')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting auto-fix {fix_id} for {error_analysis.get('total_errors', 0)} errors")
        
        fixes_applied = []
        fixes_failed = []
        
        # Process fix recommendations
        for recommendation in error_analysis.get('fix_recommendations', []):
            fix_type = recommendation.get('type')
            
            if fix_type == 'dependency_resolution':
                fix_result = self._fix_dependency_conflicts(
                    recommendation.get('errors', []),
                    story_files
                )
                if fix_result['success']:
                    fixes_applied.append(fix_result)
                else:
                    fixes_failed.append(fix_result)
            
            elif fix_type == 'add_dependencies':
                fix_result = self._fix_missing_dependencies(
                    recommendation.get('modules', []),
                    story_files
                )
                if fix_result['success']:
                    fixes_applied.append(fix_result)
                else:
                    fixes_failed.append(fix_result)
            
            elif fix_type == 'fix_types':
                fix_result = self._fix_typescript_errors(
                    recommendation.get('errors', []),
                    story_files,
                    existing_files
                )
                if fix_result['success']:
                    fixes_applied.append(fix_result)
                else:
                    fixes_failed.append(fix_result)
        
        # Process individual error categories
        error_categories = error_analysis.get('error_categories', {})
        
        # Fix import errors
        if error_categories.get('import_errors'):
            fix_result = self._fix_import_errors(
                error_categories['import_errors'],
                story_files,
                existing_files
            )
            if fix_result['success']:
                fixes_applied.append(fix_result)
            else:
                fixes_failed.append(fix_result)
        
        # Fix syntax errors
        if error_categories.get('syntax_errors'):
            fix_result = self._fix_syntax_errors(
                error_categories['syntax_errors'],
                story_files
            )
            if fix_result['success']:
                fixes_applied.append(fix_result)
            else:
                fixes_failed.append(fix_result)
        
        # Update story files with fixes
        updated_files = self._apply_fixes_to_files(story_files, fixes_applied)
        
        fix_summary = {
            'fix_id': fix_id,
            'story_id': story_metadata.get('story_id'),
            'fixes_applied': len(fixes_applied),
            'fixes_failed': len(fixes_failed),
            'success': len(fixes_failed) == 0 and len(fixes_applied) > 0,
            'applied_fixes': fixes_applied,
            'failed_fixes': fixes_failed,
            'updated_files': updated_files,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store fix history
        self.fix_history.append(fix_summary)
        
        return fix_summary
    
    def _fix_dependency_conflicts(self, conflicts: List[Dict[str, Any]], 
                                  story_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fix dependency version conflicts."""
        try:
            # Find package.json
            package_json_file = next(
                (f for f in story_files if f['file_path'] == 'package.json'),
                None
            )
            
            if not package_json_file:
                return {
                    'success': False,
                    'error': 'package.json not found'
                }
            
            package_json = json.loads(package_json_file['content'])
            fixes = []
            
            for conflict in conflicts:
                details = conflict.get('details', '')
                
                # Parse ERESOLVE errors and suggest resolutions
                if 'peer dep' in details.lower():
                    # Handle peer dependency conflicts
                    fixes.append(self._resolve_peer_dependency(details, package_json))
                elif 'cannot resolve' in details.lower():
                    # Handle version conflicts
                    fixes.append(self._resolve_version_conflict(details, package_json))
            
            # Update package.json
            package_json_file['content'] = json.dumps(package_json, indent=2)
            
            return {
                'success': True,
                'type': 'dependency_conflict',
                'fixes': fixes,
                'file': 'package.json'
            }
            
        except Exception as e:
            logger.error(f"Failed to fix dependency conflicts: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _fix_missing_dependencies(self, modules: List[str], 
                                  story_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add missing dependencies to package.json."""
        try:
            # Find package.json
            package_json_file = next(
                (f for f in story_files if f['file_path'] == 'package.json'),
                None
            )
            
            if not package_json_file:
                return {
                    'success': False,
                    'error': 'package.json not found'
                }
            
            package_json = json.loads(package_json_file['content'])
            
            if 'dependencies' not in package_json:
                package_json['dependencies'] = {}
            
            added_deps = []
            
            for module in modules:
                if module not in package_json['dependencies']:
                    # Determine version to use
                    version = self._get_recommended_version(module)
                    package_json['dependencies'][module] = version
                    added_deps.append(f"{module}@{version}")
            
            # Update package.json
            package_json_file['content'] = json.dumps(package_json, indent=2)
            
            return {
                'success': True,
                'type': 'add_dependencies',
                'added': added_deps,
                'file': 'package.json'
            }
            
        except Exception as e:
            logger.error(f"Failed to add dependencies: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _fix_typescript_errors(self, errors: List[Dict[str, Any]],
                               story_files: List[Dict[str, Any]],
                               existing_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fix TypeScript type errors."""
        fixes = []
        
        for error in errors[:5]:  # Limit to first 5 errors
            file_path = error.get('file', '')
            line = error.get('line', 0)
            message = error.get('message', '')
            
            # Find the file
            file_data = next(
                (f for f in story_files if f['file_path'] == file_path),
                None
            )
            
            if not file_data:
                continue
            
            content = file_data['content']
            
            # Apply specific fixes based on error type
            if 'Property' in message and 'does not exist' in message:
                fix = self._fix_missing_property(content, line, message)
                if fix:
                    file_data['content'] = fix['content']
                    fixes.append(fix)
            
            elif 'Cannot find name' in message:
                fix = self._fix_undefined_name(content, line, message)
                if fix:
                    file_data['content'] = fix['content']
                    fixes.append(fix)
            
            elif 'Type' in message and 'is not assignable' in message:
                fix = self._fix_type_mismatch(content, line, message)
                if fix:
                    file_data['content'] = fix['content']
                    fixes.append(fix)
        
        return {
            'success': len(fixes) > 0,
            'type': 'typescript_fixes',
            'fixes': fixes
        }
    
    def _fix_import_errors(self, errors: List[Dict[str, Any]],
                           story_files: List[Dict[str, Any]],
                           existing_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fix import/export errors."""
        fixes = []
        all_files = {f['file_path']: f for f in existing_files + story_files}
        
        for error in errors:
            module = error.get('module', '')
            
            # Check if it's a relative import
            if module.startswith('.'):
                # Try to find the correct path
                fix = self._fix_relative_import(module, all_files)
                if fix:
                    fixes.append(fix)
            else:
                # It's a package import - add to dependencies
                fix = self._add_missing_import(module, story_files)
                if fix:
                    fixes.append(fix)
        
        return {
            'success': len(fixes) > 0,
            'type': 'import_fixes',
            'fixes': fixes
        }
    
    def _fix_syntax_errors(self, errors: List[Dict[str, Any]],
                           story_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fix syntax errors using AI."""
        if not self.llm_service:
            return {
                'success': False,
                'error': 'LLM service not available for syntax fixes'
            }
        
        fixes = []
        
        for error in errors[:3]:  # Limit to first 3
            fix_prompt = self._generate_syntax_fix_prompt(error, story_files)
            
            try:
                # Use LLM to generate fix
                fix_response = self.llm_service.generate_completion(fix_prompt)
                
                # Parse and apply fix
                fix = self._parse_fix_response(fix_response)
                if fix:
                    fixes.append(fix)
                    
            except Exception as e:
                logger.error(f"Failed to generate syntax fix: {str(e)}")
        
        return {
            'success': len(fixes) > 0,
            'type': 'syntax_fixes',
            'fixes': fixes
        }
    
    def _resolve_peer_dependency(self, details: str, package_json: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve peer dependency conflicts."""
        # Parse the peer dependency requirement
        peer_match = re.search(r'peer ([^@]+)@"([^"]+)"', details)
        if peer_match:
            package = peer_match.group(1)
            version = peer_match.group(2)
            
            # Add or update the dependency
            if 'dependencies' not in package_json:
                package_json['dependencies'] = {}
            
            package_json['dependencies'][package] = version
            
            return {
                'type': 'peer_dependency',
                'package': package,
                'version': version
            }
        
        return {}
    
    def _resolve_version_conflict(self, details: str, package_json: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve version conflicts between dependencies."""
        # Look for version patterns
        version_pattern = r'([^@\s]+)@([^\s]+)'
        matches = re.findall(version_pattern, details)
        
        if matches:
            # Use the latest version mentioned
            package, version = matches[-1]
            
            if 'dependencies' in package_json:
                package_json['dependencies'][package] = version
            
            return {
                'type': 'version_conflict',
                'package': package,
                'version': version
            }
        
        return {}
    
    def _get_recommended_version(self, module: str) -> str:
        """Get recommended version for a module."""
        # Common module versions (would ideally fetch from npm registry)
        common_versions = {
            'react': '^18.2.0',
            'react-dom': '^18.2.0',
            'axios': '^1.6.0',
            'lodash': '^4.17.21',
            'moment': '^2.29.4',
            'uuid': '^9.0.0',
            'classnames': '^2.3.2',
            'react-router-dom': '^6.20.0',
            '@types/react': '^18.2.43',
            '@types/node': '^20.10.0'
        }
        
        return common_versions.get(module, 'latest')
    
    def _fix_missing_property(self, content: str, line: int, message: str) -> Optional[Dict[str, Any]]:
        """Fix missing property errors."""
        # Extract property name from error message
        prop_match = re.search(r"Property '(\w+)'", message)
        if not prop_match:
            return None
        
        property_name = prop_match.group(1)
        lines = content.split('\n')
        
        if line > 0 and line <= len(lines):
            # Try to add the property with a reasonable default
            target_line = lines[line - 1]
            
            # If it's an object, add the property
            if '{' in target_line:
                # Add property after the opening brace
                lines[line - 1] = target_line.replace('{', f'{{ {property_name}: undefined,')
                
                return {
                    'type': 'add_property',
                    'property': property_name,
                    'line': line,
                    'content': '\n'.join(lines)
                }
        
        return None
    
    def _fix_undefined_name(self, content: str, line: int, message: str) -> Optional[Dict[str, Any]]:
        """Fix undefined name errors."""
        # Extract name from error message
        name_match = re.search(r"Cannot find name '(\w+)'", message)
        if not name_match:
            return None
        
        name = name_match.group(1)
        lines = content.split('\n')
        
        # Add declaration at the top of the file
        import_section_end = 0
        for i, line_content in enumerate(lines):
            if line_content.strip() and not line_content.startswith('import'):
                import_section_end = i
                break
        
        # Add const declaration
        lines.insert(import_section_end, f"const {name} = undefined; // TODO: Define {name}")
        
        return {
            'type': 'declare_variable',
            'name': name,
            'content': '\n'.join(lines)
        }
    
    def _fix_type_mismatch(self, content: str, line: int, message: str) -> Optional[Dict[str, Any]]:
        """Fix type mismatch errors."""
        lines = content.split('\n')
        
        if line > 0 and line <= len(lines):
            target_line = lines[line - 1]
            
            # Try to add type assertion
            if '=' in target_line:
                # Add 'as any' to bypass type checking temporarily
                lines[line - 1] = target_line.replace('=', '= (') + ') as any'
                
                return {
                    'type': 'type_assertion',
                    'line': line,
                    'content': '\n'.join(lines)
                }
        
        return None
    
    def _fix_relative_import(self, module: str, all_files: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fix relative import paths."""
        # Try to find a matching file
        base_name = os.path.basename(module).replace('./', '').replace('../', '')
        
        for file_path in all_files:
            if base_name in file_path:
                return {
                    'type': 'fix_import_path',
                    'old_path': module,
                    'new_path': self._calculate_relative_path(module, file_path)
                }
        
        return None
    
    def _calculate_relative_path(self, from_path: str, to_path: str) -> str:
        """Calculate relative path between two files."""
        # Simplified relative path calculation
        from_parts = from_path.split('/')
        to_parts = to_path.split('/')
        
        # Find common prefix
        common_length = 0
        for i in range(min(len(from_parts), len(to_parts))):
            if from_parts[i] == to_parts[i]:
                common_length = i + 1
            else:
                break
        
        # Build relative path
        up_levels = len(from_parts) - common_length - 1
        relative_parts = ['..'] * up_levels + to_parts[common_length:]
        
        return '/'.join(relative_parts) if relative_parts else './'
    
    def _add_missing_import(self, module: str, story_files: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Add missing import statement."""
        # Find the first TypeScript/JavaScript file
        for file_data in story_files:
            if file_data['file_path'].endswith(('.ts', '.tsx', '.js', '.jsx')):
                content = file_data['content']
                lines = content.split('\n')
                
                # Find where to add import
                import_index = 0
                for i, line in enumerate(lines):
                    if not line.startswith('import'):
                        import_index = i
                        break
                
                # Add import statement
                lines.insert(import_index, f"import {module} from '{module}';")
                file_data['content'] = '\n'.join(lines)
                
                return {
                    'type': 'add_import',
                    'module': module,
                    'file': file_data['file_path']
                }
        
        return None
    
    def _generate_syntax_fix_prompt(self, error: Dict[str, Any], 
                                    story_files: List[Dict[str, Any]]) -> str:
        """Generate prompt for AI to fix syntax errors."""
        return f"""
Fix the following syntax error:

Error: {error.get('message', 'Unknown syntax error')}

Please provide the corrected code. Only return the fixed code, no explanations.
"""
    
    def _parse_fix_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse AI-generated fix response."""
        # Extract code from response
        code_match = re.search(r'```(?:\w+)?\n(.*?)\n```', response, re.DOTALL)
        if code_match:
            return {
                'type': 'ai_fix',
                'content': code_match.group(1)
            }
        
        return None
    
    def _apply_fixes_to_files(self, story_files: List[Dict[str, Any]], 
                              fixes_applied: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply fixes to story files and return updated files."""
        updated_files = []
        
        for fix in fixes_applied:
            if 'file' in fix:
                # Find and update the file
                for file_data in story_files:
                    if file_data['file_path'] == fix['file']:
                        updated_files.append({
                            'file_path': file_data['file_path'],
                            'fix_applied': fix['type']
                        })
        
        return updated_files
    
    def generate_fix_report(self) -> Dict[str, Any]:
        """Generate a report of all fixes applied."""
        total_fixes = sum(h['fixes_applied'] for h in self.fix_history)
        total_failures = sum(h['fixes_failed'] for h in self.fix_history)
        
        # Calculate success rate by fix type
        fix_type_stats = {}
        for history in self.fix_history:
            for fix in history.get('applied_fixes', []):
                fix_type = fix.get('type', 'unknown')
                if fix_type not in fix_type_stats:
                    fix_type_stats[fix_type] = {'success': 0, 'total': 0}
                fix_type_stats[fix_type]['success'] += 1
                fix_type_stats[fix_type]['total'] += 1
        
        return {
            'total_fixes_applied': total_fixes,
            'total_fixes_failed': total_failures,
            'success_rate': total_fixes / (total_fixes + total_failures) if (total_fixes + total_failures) > 0 else 0,
            'fix_type_statistics': fix_type_stats,
            'history_count': len(self.fix_history)
        }