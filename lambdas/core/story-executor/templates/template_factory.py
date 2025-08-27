"""
Template Factory for creating appropriate template generators.
Uses Factory pattern to encapsulate template generator creation logic.
"""

from typing import Dict, Type
from templates.base_template_generator import BaseTemplateGenerator
from templates.react_spa_generator import ReactSPATemplateGenerator
from templates.vue_spa_generator import VueSPATemplateGenerator
from templates.node_api_generator import NodeAPITemplateGenerator
from templates.react_fullstack_generator import ReactFullstackTemplateGenerator
import logging

logger = logging.getLogger(__name__)


class TechStack:
    """Enum-like class for supported tech stacks."""
    REACT_SPA = 'react_spa'
    VUE_SPA = 'vue_spa'
    NODE_API = 'node_api'
    REACT_FULLSTACK = 'react_fullstack'
    PYTHON_API = 'python_api'
    
    @classmethod
    def all_values(cls):
        return [cls.REACT_SPA, cls.VUE_SPA, cls.NODE_API, cls.REACT_FULLSTACK, cls.PYTHON_API]


class TemplateGeneratorFactory:
    """
    Factory for creating template generators based on tech stack.
    Follows the Factory pattern to encapsulate object creation logic.
    """
    
    def __init__(self):
        self.logger = logger
        self._generators: Dict[str, Type[BaseTemplateGenerator]] = {
            TechStack.REACT_SPA: ReactSPATemplateGenerator,
            TechStack.VUE_SPA: VueSPATemplateGenerator,
            TechStack.NODE_API: NodeAPITemplateGenerator,
            TechStack.REACT_FULLSTACK: ReactFullstackTemplateGenerator,
            # Future generators can be added here
            # TechStack.PYTHON_API: PythonAPITemplateGenerator,
        }
    
    def create_generator(self, tech_stack: str) -> BaseTemplateGenerator:
        """
        Create and return a template generator for the specified tech stack.
        
        Args:
            tech_stack: The technology stack identifier
            
        Returns:
            BaseTemplateGenerator: Configured template generator instance
            
        Raises:
            ValueError: If tech stack is not supported
        """
        if tech_stack not in self._generators:
            supported_stacks = list(self._generators.keys())
            raise ValueError(
                f"Unsupported tech stack: {tech_stack}. "
                f"Supported stacks: {supported_stacks}"
            )
        
        generator_class = self._generators[tech_stack]
        generator = generator_class()
        
        self.logger.info(
            f"Created template generator: {generator_class.__name__} for {tech_stack}"
        )
        
        return generator
    
    def get_supported_stacks(self) -> Dict[str, str]:
        """
        Get a dictionary of supported tech stacks and their descriptions.
        
        Returns:
            Dict mapping tech stack names to descriptions
        """
        descriptions = {}
        for tech_stack, generator_class in self._generators.items():
            # Create a temporary instance to get description
            temp_generator = generator_class()
            descriptions[tech_stack] = temp_generator.get_description()
        
        return descriptions
    
    def is_supported(self, tech_stack: str) -> bool:
        """
        Check if a tech stack is supported by this factory.
        
        Args:
            tech_stack: The technology stack to check
            
        Returns:
            bool: True if supported, False otherwise
        """
        return tech_stack in self._generators
    
    def register_generator(self, tech_stack: str, generator_class: Type[BaseTemplateGenerator]) -> None:
        """
        Register a new template generator for a tech stack.
        This allows for extension without modifying the factory code.
        
        Args:
            tech_stack: The technology stack identifier
            generator_class: The generator class to register
        """
        if not issubclass(generator_class, BaseTemplateGenerator):
            raise ValueError(
                f"Generator class must inherit from BaseTemplateGenerator"
            )
        
        self._generators[tech_stack] = generator_class
        self.logger.info(f"Registered new generator: {generator_class.__name__} for {tech_stack}")


# Global factory instance
template_factory = TemplateGeneratorFactory()