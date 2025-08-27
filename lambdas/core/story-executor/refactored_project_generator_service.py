"""
Refactored Project Generator Service using Factory Pattern.
This replaces the monolithic 3,200+ line service with a clean, maintainable architecture.

Key improvements:
- Single Responsibility Principle: Each generator handles one tech stack
- Factory Pattern: Centralizes generator creation logic  
- Strategy Pattern: Different generation strategies for different tech stacks
- Testable: Small, focused classes that are easy to unit test
- Extensible: New tech stacks can be added without modifying existing code
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from templates.template_factory import template_factory, TechStack
from templates.base_template_generator import GeneratedCode

logger = logging.getLogger(__name__)


class RefactoredProjectGeneratorService:
    """
    Refactored project generator service following TDD and SOLID principles.
    
    This service:
    1. Uses Factory pattern to create appropriate template generators
    2. Delegates actual generation to specialized generator classes
    3. Maintains a clean, testable interface
    4. Follows Single Responsibility Principle
    """
    
    def __init__(self):
        self.logger = logger
        self.factory = template_factory
    
    def generate_project_scaffold(self, architecture: Any) -> List[GeneratedCode]:
        """
        Generate a complete project scaffold using the appropriate template generator.
        
        Args:
            architecture: Project architecture configuration containing:
                - tech_stack: Technology stack identifier
                - name: Project name
                - components: List of components to generate (optional)
                - dependencies: Package dependencies
                - build_config: Build configuration
                
        Returns:
            List[GeneratedCode]: Complete project scaffold files
            
        Raises:
            ValueError: If tech stack is not supported
            Exception: If generation fails
        """
        try:
            tech_stack = self._extract_tech_stack(architecture)
            project_name = self._extract_project_name(architecture)
            
            self.logger.info(f"Generating project scaffold for {tech_stack}: {project_name}")
            
            # Map unsupported tech stacks to supported ones
            tech_stack_mapping = {
                'angular_spa': 'react_spa',      # Fallback Angular to React for now
                'python_api': 'node_api',        # Fallback Python API to Node API
                'vue_fullstack': 'vue_spa'       # Vue fullstack uses same frontend as SPA
            }
            
            # Apply mapping if needed
            original_stack = tech_stack
            if tech_stack in tech_stack_mapping:
                tech_stack = tech_stack_mapping[tech_stack]
                self.logger.info(f"Mapping {original_stack} -> {tech_stack} (using compatible template)")
            
            # Use factory to create appropriate generator
            generator = self.factory.create_generator(tech_stack)
            
            # Generate project scaffold using the specialized generator
            generated_files = generator.generate_project_scaffold(project_name, architecture)
            
            self.logger.info(
                f"Successfully generated {len(generated_files)} files for {tech_stack} project"
            )
            
            return generated_files
            
        except ValueError as e:
            # Re-raise ValueError for unsupported tech stacks
            self.logger.error(f"Unsupported tech stack: {str(e)}")
            raise
            
        except Exception as e:
            # Log and re-raise other exceptions
            self.logger.error(f"Failed to generate project scaffold: {str(e)}")
            raise Exception(f"Project generation failed: {str(e)}")
    
    def get_supported_tech_stacks(self) -> Dict[str, str]:
        """
        Get information about supported technology stacks.
        
        Returns:
            Dict mapping tech stack names to descriptions
        """
        return self.factory.get_supported_stacks()
    
    def is_tech_stack_supported(self, tech_stack: str) -> bool:
        """
        Check if a technology stack is supported.
        
        Args:
            tech_stack: Technology stack to check
            
        Returns:
            bool: True if supported, False otherwise
        """
        return self.factory.is_supported(tech_stack)
    
    def validate_architecture(self, architecture: Any) -> Dict[str, Any]:
        """
        Validate architecture configuration and return validation results.
        
        Args:
            architecture: Architecture configuration to validate
            
        Returns:
            Dict containing validation results:
                - valid: bool
                - errors: List[str] of validation errors
                - warnings: List[str] of validation warnings
        """
        errors = []
        warnings = []
        
        try:
            # Check required fields
            tech_stack = self._extract_tech_stack(architecture)
            project_name = self._extract_project_name(architecture)
            
            # Validate tech stack
            if not self.is_tech_stack_supported(tech_stack):
                supported = list(self.get_supported_tech_stacks().keys())
                errors.append(f"Unsupported tech stack: {tech_stack}. Supported: {supported}")
            
            # Validate project name
            if not project_name or len(project_name.strip()) == 0:
                errors.append("Project name is required")
            elif len(project_name) > 100:
                errors.append("Project name must be less than 100 characters")
            
            # Check for potentially problematic project names
            problematic_chars = ['<', '>', ':', '"', '|', '?', '*']
            if any(char in project_name for char in problematic_chars):
                warnings.append("Project name contains special characters that may cause issues")
            
        except Exception as e:
            errors.append(f"Architecture validation error: {str(e)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _extract_tech_stack(self, architecture: Any) -> str:
        """Extract and validate tech stack from architecture configuration."""
        if hasattr(architecture, 'tech_stack'):
            return architecture.tech_stack
        elif isinstance(architecture, dict) and 'tech_stack' in architecture:
            return architecture['tech_stack']
        else:
            raise ValueError("Architecture must contain 'tech_stack' field")
    
    def _extract_project_name(self, architecture: Any) -> str:
        """Extract and validate project name from architecture configuration."""
        if hasattr(architecture, 'name'):
            return architecture.name
        elif isinstance(architecture, dict) and 'name' in architecture:
            return architecture['name']
        else:
            raise ValueError("Architecture must contain 'name' field")


class ProjectGeneratorStats:
    """
    Utility class for tracking project generation statistics.
    Useful for monitoring and debugging.
    """
    
    def __init__(self):
        self.generations = []
    
    def record_generation(self, tech_stack: str, project_name: str, 
                         file_count: int, duration_seconds: float) -> None:
        """Record a project generation event."""
        self.generations.append({
            'tech_stack': tech_stack,
            'project_name': project_name,
            'file_count': file_count,
            'duration_seconds': duration_seconds,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        if not self.generations:
            return {
                'total_generations': 0,
                'tech_stacks_used': [],
                'average_files_per_project': 0,
                'average_duration_seconds': 0
            }
        
        tech_stacks = set(gen['tech_stack'] for gen in self.generations)
        total_files = sum(gen['file_count'] for gen in self.generations)
        total_duration = sum(gen['duration_seconds'] for gen in self.generations)
        
        return {
            'total_generations': len(self.generations),
            'tech_stacks_used': list(tech_stacks),
            'average_files_per_project': round(total_files / len(self.generations), 1),
            'average_duration_seconds': round(total_duration / len(self.generations), 2),
            'most_recent': self.generations[-1] if self.generations else None
        }


# Create global instances
project_generator_service = RefactoredProjectGeneratorService()
generation_stats = ProjectGeneratorStats()