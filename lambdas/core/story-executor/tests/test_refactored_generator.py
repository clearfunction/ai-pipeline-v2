"""
Unit tests for the refactored project generator service.
Demonstrates improved testability with the Factory pattern refactoring.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pytest

from ..refactored_project_generator_service import RefactoredProjectGeneratorService
from ..templates.base_template_generator import GeneratedCode
from ..templates.template_factory import TechStack


class TestRefactoredProjectGeneratorService(unittest.TestCase):
    """Test suite for RefactoredProjectGeneratorService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = RefactoredProjectGeneratorService()
        
        # Mock architecture object
        self.mock_architecture = Mock()
        self.mock_architecture.tech_stack = TechStack.REACT_SPA
        self.mock_architecture.name = 'test-project'
        self.mock_architecture.components = []
        self.mock_architecture.dependencies = {'react': '^18.2.0'}
        
        # Mock generated files
        self.mock_generated_files = [
            GeneratedCode(
                file_path='package.json',
                content='{"name": "test-project"}',
                component_id='project_scaffold',
                story_id='scaffold',
                file_type='config',
                language='json'
            ),
            GeneratedCode(
                file_path='src/App.tsx',
                content='export default function App() {}',
                component_id='project_scaffold',
                story_id='scaffold',
                file_type='component',
                language='typescript'
            )
        ]
    
    def test_generate_project_scaffold_success(self):
        """Test successful project scaffold generation."""
        with patch.object(self.service.factory, 'create_generator') as mock_create:
            mock_generator = Mock()
            mock_generator.generate_project_scaffold.return_value = self.mock_generated_files
            mock_create.return_value = mock_generator
            
            result = self.service.generate_project_scaffold(self.mock_architecture)
            
            # Verify factory was called with correct tech stack
            mock_create.assert_called_once_with(TechStack.REACT_SPA)
            
            # Verify generator was called with correct parameters
            mock_generator.generate_project_scaffold.assert_called_once_with(
                'test-project', self.mock_architecture
            )
            
            # Verify result
            self.assertEqual(result, self.mock_generated_files)
            self.assertEqual(len(result), 2)
    
    def test_generate_project_scaffold_unsupported_tech_stack(self):
        """Test handling of unsupported tech stack."""
        self.mock_architecture.tech_stack = 'unsupported_stack'
        
        with patch.object(self.service.factory, 'create_generator') as mock_create:
            mock_create.side_effect = ValueError("Unsupported tech stack: unsupported_stack")
            
            with self.assertRaises(ValueError) as context:
                self.service.generate_project_scaffold(self.mock_architecture)
            
            self.assertIn("Unsupported tech stack", str(context.exception))
    
    def test_generate_project_scaffold_generation_failure(self):
        """Test handling of generation failures."""
        with patch.object(self.service.factory, 'create_generator') as mock_create:
            mock_generator = Mock()
            mock_generator.generate_project_scaffold.side_effect = Exception("Generation failed")
            mock_create.return_value = mock_generator
            
            with self.assertRaises(Exception) as context:
                self.service.generate_project_scaffold(self.mock_architecture)
            
            self.assertIn("Project generation failed", str(context.exception))
    
    def test_get_supported_tech_stacks(self):
        """Test retrieval of supported tech stacks."""
        expected_stacks = {
            TechStack.REACT_SPA: 'React + Vite + TypeScript SPA with comprehensive testing',
            TechStack.VUE_SPA: 'Vue 3 + Vite + TypeScript SPA with comprehensive testing',
            TechStack.NODE_API: 'Node.js API with Fastify + TypeScript and comprehensive testing'
        }
        
        with patch.object(self.service.factory, 'get_supported_stacks') as mock_get:
            mock_get.return_value = expected_stacks
            
            result = self.service.get_supported_tech_stacks()
            
            self.assertEqual(result, expected_stacks)
            mock_get.assert_called_once()
    
    def test_is_tech_stack_supported(self):
        """Test tech stack support checking."""
        with patch.object(self.service.factory, 'is_supported') as mock_is_supported:
            mock_is_supported.return_value = True
            
            result = self.service.is_tech_stack_supported(TechStack.REACT_SPA)
            
            self.assertTrue(result)
            mock_is_supported.assert_called_once_with(TechStack.REACT_SPA)
    
    def test_validate_architecture_valid(self):
        """Test validation of valid architecture."""
        result = self.service.validate_architecture(self.mock_architecture)
        
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['errors']), 0)
        self.assertIsInstance(result['warnings'], list)
    
    def test_validate_architecture_missing_tech_stack(self):
        """Test validation with missing tech stack."""
        invalid_architecture = Mock()
        delattr(invalid_architecture, 'tech_stack')
        
        # Mock hasattr to return False
        with patch('builtins.hasattr', return_value=False):
            result = self.service.validate_architecture(invalid_architecture)
        
        self.assertFalse(result['valid'])
        self.assertGreater(len(result['errors']), 0)
        self.assertIn("Architecture must contain 'tech_stack'", str(result['errors']))
    
    def test_validate_architecture_unsupported_tech_stack(self):
        """Test validation with unsupported tech stack."""
        self.mock_architecture.tech_stack = 'unsupported_stack'
        
        result = self.service.validate_architecture(self.mock_architecture)
        
        self.assertFalse(result['valid'])
        self.assertGreater(len(result['errors']), 0)
        self.assertIn("Unsupported tech stack", str(result['errors'][0]))
    
    def test_validate_architecture_empty_project_name(self):
        """Test validation with empty project name."""
        self.mock_architecture.name = ''
        
        result = self.service.validate_architecture(self.mock_architecture)
        
        self.assertFalse(result['valid'])
        self.assertIn("Project name is required", result['errors'])
    
    def test_validate_architecture_long_project_name(self):
        """Test validation with overly long project name."""
        self.mock_architecture.name = 'a' * 101  # 101 characters
        
        result = self.service.validate_architecture(self.mock_architecture)
        
        self.assertFalse(result['valid'])
        self.assertIn("Project name must be less than 100 characters", result['errors'])
    
    def test_validate_architecture_problematic_project_name(self):
        """Test validation with problematic characters in project name."""
        self.mock_architecture.name = 'test<project>'
        
        result = self.service.validate_architecture(self.mock_architecture)
        
        # Should be valid but have warnings
        self.assertTrue(result['valid'])
        self.assertGreater(len(result['warnings']), 0)
        self.assertIn("special characters", result['warnings'][0])
    
    def test_extract_tech_stack_from_object(self):
        """Test tech stack extraction from object with attribute."""
        result = self.service._extract_tech_stack(self.mock_architecture)
        self.assertEqual(result, TechStack.REACT_SPA)
    
    def test_extract_tech_stack_from_dict(self):
        """Test tech stack extraction from dictionary."""
        arch_dict = {'tech_stack': TechStack.VUE_SPA, 'name': 'test-project'}
        
        result = self.service._extract_tech_stack(arch_dict)
        self.assertEqual(result, TechStack.VUE_SPA)
    
    def test_extract_tech_stack_missing(self):
        """Test tech stack extraction when missing."""
        invalid_arch = {'name': 'test-project'}  # Missing tech_stack
        
        with self.assertRaises(ValueError) as context:
            self.service._extract_tech_stack(invalid_arch)
        
        self.assertIn("Architecture must contain 'tech_stack'", str(context.exception))
    
    def test_extract_project_name_from_object(self):
        """Test project name extraction from object with attribute."""
        result = self.service._extract_project_name(self.mock_architecture)
        self.assertEqual(result, 'test-project')
    
    def test_extract_project_name_from_dict(self):
        """Test project name extraction from dictionary."""
        arch_dict = {'tech_stack': TechStack.REACT_SPA, 'name': 'my-project'}
        
        result = self.service._extract_project_name(arch_dict)
        self.assertEqual(result, 'my-project')
    
    def test_extract_project_name_missing(self):
        """Test project name extraction when missing."""
        invalid_arch = {'tech_stack': TechStack.REACT_SPA}  # Missing name
        
        with self.assertRaises(ValueError) as context:
            self.service._extract_project_name(invalid_arch)
        
        self.assertIn("Architecture must contain 'name'", str(context.exception))


class TestProjectGeneratorStats(unittest.TestCase):
    """Test suite for ProjectGeneratorStats."""
    
    def setUp(self):
        """Set up test fixtures."""
        from ..refactored_project_generator_service import ProjectGeneratorStats
        self.stats = ProjectGeneratorStats()
    
    def test_record_generation(self):
        """Test recording a generation event."""
        self.stats.record_generation('react_spa', 'test-project', 20, 2.5)
        
        self.assertEqual(len(self.stats.generations), 1)
        
        generation = self.stats.generations[0]
        self.assertEqual(generation['tech_stack'], 'react_spa')
        self.assertEqual(generation['project_name'], 'test-project')
        self.assertEqual(generation['file_count'], 20)
        self.assertEqual(generation['duration_seconds'], 2.5)
        self.assertIn('timestamp', generation)
    
    def test_get_stats_empty(self):
        """Test statistics when no generations recorded."""
        stats = self.stats.get_stats()
        
        self.assertEqual(stats['total_generations'], 0)
        self.assertEqual(stats['tech_stacks_used'], [])
        self.assertEqual(stats['average_files_per_project'], 0)
        self.assertEqual(stats['average_duration_seconds'], 0)
    
    def test_get_stats_with_data(self):
        """Test statistics calculation with recorded data."""
        # Record multiple generations
        self.stats.record_generation('react_spa', 'project1', 20, 2.0)
        self.stats.record_generation('vue_spa', 'project2', 30, 3.0)
        self.stats.record_generation('react_spa', 'project3', 25, 2.5)
        
        stats = self.stats.get_stats()
        
        self.assertEqual(stats['total_generations'], 3)
        self.assertEqual(set(stats['tech_stacks_used']), {'react_spa', 'vue_spa'})
        self.assertEqual(stats['average_files_per_project'], 25.0)  # (20+30+25)/3
        self.assertEqual(stats['average_duration_seconds'], 2.5)   # (2.0+3.0+2.5)/3
        self.assertIsNotNone(stats['most_recent'])
        self.assertEqual(stats['most_recent']['project_name'], 'project3')


if __name__ == '__main__':
    unittest.main()