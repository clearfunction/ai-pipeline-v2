"""
Unit tests for the template factory.
Demonstrates improved testability and separation of concerns.
"""

import unittest
from unittest.mock import Mock, patch

from ..templates.template_factory import TemplateGeneratorFactory, TechStack
from ..templates.base_template_generator import BaseTemplateGenerator
from ..templates.react_spa_generator import ReactSPATemplateGenerator
from ..templates.vue_spa_generator import VueSPATemplateGenerator
from ..templates.node_api_generator import NodeAPITemplateGenerator


class MockTemplateGenerator(BaseTemplateGenerator):
    """Mock template generator for testing."""
    
    def __init__(self):
        super().__init__('mock_stack')
    
    def generate_project_scaffold(self, project_name, architecture):
        return []
    
    def get_supported_runtime(self):
        return 'mock'
    
    def get_description(self):
        return 'Mock generator for testing'


class TestTemplateGeneratorFactory(unittest.TestCase):
    """Test suite for TemplateGeneratorFactory."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.factory = TemplateGeneratorFactory()
    
    def test_create_generator_react_spa(self):
        """Test creating React SPA generator."""
        generator = self.factory.create_generator(TechStack.REACT_SPA)
        
        self.assertIsInstance(generator, ReactSPATemplateGenerator)
        self.assertEqual(generator.tech_stack, TechStack.REACT_SPA)
    
    def test_create_generator_vue_spa(self):
        """Test creating Vue SPA generator."""
        generator = self.factory.create_generator(TechStack.VUE_SPA)
        
        self.assertIsInstance(generator, VueSPATemplateGenerator)
        self.assertEqual(generator.tech_stack, TechStack.VUE_SPA)
    
    def test_create_generator_node_api(self):
        """Test creating Node.js API generator."""
        generator = self.factory.create_generator(TechStack.NODE_API)
        
        self.assertIsInstance(generator, NodeAPITemplateGenerator)
        self.assertEqual(generator.tech_stack, TechStack.NODE_API)
    
    def test_create_generator_unsupported(self):
        """Test handling of unsupported tech stack."""
        with self.assertRaises(ValueError) as context:
            self.factory.create_generator('unsupported_stack')
        
        error_message = str(context.exception)
        self.assertIn("Unsupported tech stack: unsupported_stack", error_message)
        self.assertIn("Supported stacks:", error_message)
    
    def test_get_supported_stacks(self):
        """Test getting supported tech stacks."""
        supported = self.factory.get_supported_stacks()
        
        self.assertIsInstance(supported, dict)
        self.assertIn(TechStack.REACT_SPA, supported)
        self.assertIn(TechStack.VUE_SPA, supported)
        self.assertIn(TechStack.NODE_API, supported)
        
        # Check descriptions are present
        for tech_stack, description in supported.items():
            self.assertIsInstance(description, str)
            self.assertGreater(len(description), 0)
    
    def test_is_supported_true(self):
        """Test checking supported tech stack."""
        self.assertTrue(self.factory.is_supported(TechStack.REACT_SPA))
        self.assertTrue(self.factory.is_supported(TechStack.VUE_SPA))
        self.assertTrue(self.factory.is_supported(TechStack.NODE_API))
    
    def test_is_supported_false(self):
        """Test checking unsupported tech stack."""
        self.assertFalse(self.factory.is_supported('unsupported_stack'))
        self.assertFalse(self.factory.is_supported(''))
        self.assertFalse(self.factory.is_supported(None))
    
    def test_register_generator(self):
        """Test registering a new generator."""
        # Initially not supported
        self.assertFalse(self.factory.is_supported('mock_stack'))
        
        # Register mock generator
        self.factory.register_generator('mock_stack', MockTemplateGenerator)
        
        # Now should be supported
        self.assertTrue(self.factory.is_supported('mock_stack'))
        
        # Should be able to create the generator
        generator = self.factory.create_generator('mock_stack')
        self.assertIsInstance(generator, MockTemplateGenerator)
    
    def test_register_generator_invalid_class(self):
        """Test registering invalid generator class."""
        class InvalidGenerator:
            """Class that doesn't inherit from BaseTemplateGenerator."""
            pass
        
        with self.assertRaises(ValueError) as context:
            self.factory.register_generator('invalid', InvalidGenerator)
        
        self.assertIn("must inherit from BaseTemplateGenerator", str(context.exception))
    
    def test_factory_maintains_state(self):
        """Test that factory maintains its generator registry."""
        # Create two factory instances
        factory1 = TemplateGeneratorFactory()
        factory2 = TemplateGeneratorFactory()
        
        # Both should support the same tech stacks
        supported1 = set(factory1.get_supported_stacks().keys())
        supported2 = set(factory2.get_supported_stacks().keys())
        
        self.assertEqual(supported1, supported2)
        
        # Register a generator on factory1
        factory1.register_generator('test_stack', MockTemplateGenerator)
        
        # factory2 should not have this generator (independent instances)
        self.assertTrue(factory1.is_supported('test_stack'))
        self.assertFalse(factory2.is_supported('test_stack'))


class TestTechStack(unittest.TestCase):
    """Test suite for TechStack enum-like class."""
    
    def test_tech_stack_constants(self):
        """Test that tech stack constants are defined correctly."""
        self.assertEqual(TechStack.REACT_SPA, 'react_spa')
        self.assertEqual(TechStack.VUE_SPA, 'vue_spa')
        self.assertEqual(TechStack.NODE_API, 'node_api')
        self.assertEqual(TechStack.REACT_FULLSTACK, 'react_fullstack')
        self.assertEqual(TechStack.PYTHON_API, 'python_api')
    
    def test_all_values(self):
        """Test getting all tech stack values."""
        all_values = TechStack.all_values()
        
        expected = ['react_spa', 'vue_spa', 'node_api', 'react_fullstack', 'python_api']
        self.assertEqual(set(all_values), set(expected))
        self.assertEqual(len(all_values), len(expected))


if __name__ == '__main__':
    unittest.main()