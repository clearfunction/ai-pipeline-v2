"""
Modern Story Executor - Uses project generators + AI enhancement
to eliminate build failures and create production-ready code.
"""

import json
from typing import Dict, List, Any
from datetime import datetime

from refactored_project_generator_service import project_generator_service
from templates.base_template_generator import GeneratedCode
# from shared.models.pipeline_models import GeneratedCode, ProjectArchitecture
import logging

logger = logging.getLogger(__name__)


class ModernStoryExecutor:
    """
    Modern story executor that uses proven project generators
    and focuses AI on business logic enhancement.
    """
    
    def __init__(self):
        self.logger = logger
        self.generator_service = project_generator_service
        self.project_scaffold_generated = False
        self.base_project_files = []
    
    def execute_stories(self, user_stories: List[Dict[str, Any]], architecture: Dict[str, Any]) -> List[GeneratedCode]:
        """
        Execute multiple user stories by first generating a project scaffold
        and then enhancing it with business logic.
        
        Args:
            user_stories: List of user story specifications
            architecture: Project architecture configuration
            
        Returns:
            List of GeneratedCode objects representing the complete project
        """
        try:
            # Reset state for each execution to handle Lambda container reuse
            self.project_scaffold_generated = False
            self.base_project_files = []
            
            # Convert architecture dict to ProjectArchitecture object
            arch_obj = self._dict_to_architecture(architecture)
            
            # Step 1: Generate complete project scaffold using proven tools
            self.logger.info(f"Generating project scaffold for {arch_obj.tech_stack}")
            self.base_project_files = self.generator_service.generate_project_scaffold(arch_obj)
            self.project_scaffold_generated = True
            self.logger.info(f"Generated {len(self.base_project_files)} base project files")
            
            # Step 2: Enhance project with business logic for each story
            all_files = list(self.base_project_files)  # Start with scaffold
            
            for story in user_stories:
                self.logger.info(f"Enhancing project for story: {story.get('title', 'Unknown')}")
                
                try:
                    # Generate business logic enhancements for this story
                    story_enhancements = self._enhance_project_for_story(story, arch_obj, all_files)
                    
                    # Add/update files with enhancements
                    for enhancement in story_enhancements:
                        # Replace existing file or add new business logic file
                        existing_file_index = self._find_file_index(all_files, enhancement.file_path)
                        if existing_file_index >= 0:
                            # Update existing file with enhancements
                            all_files[existing_file_index] = enhancement
                        else:
                            # Add new business logic file
                            all_files.append(enhancement)
                    
                    self.logger.info(f"✅ Enhanced project with {len(story_enhancements)} files for story '{story.get('title')}'")
                    
                except Exception as e:
                    self.logger.error(f"❌ Failed to enhance project for story '{story.get('title')}': {str(e)}")
                    continue
            
            self.logger.info(f"🎉 Project generation complete: {len(all_files)} total files")
            return all_files
            
        except Exception as e:
            self.logger.error(f"Failed to execute stories: {str(e)}")
            raise
    
    def _enhance_project_for_story(self, story: Dict[str, Any], architecture: Any, current_files: List[GeneratedCode]) -> List[GeneratedCode]:
        """
        Use AI to enhance the project with business logic for a specific story.
        """
        # Create enhanced prompt that works with existing project structure
        enhanced_prompt = self._create_enhancement_prompt(story, architecture, current_files)
        
        # For now, create simplified business logic files
        # In a real implementation, this would call the Anthropic API with the enhanced prompt
        return self._generate_story_components(story, architecture)
    
    def _create_enhancement_prompt(self, story: Dict[str, Any], architecture: Any, current_files: List[GeneratedCode]) -> str:
        """
        Create an enhanced prompt that focuses on business logic enhancement
        rather than project setup.
        """
        current_structure = self._get_project_structure_summary(current_files)
        
        prompt = f"""
You are enhancing a COMPLETE, WORKING {architecture.tech_stack} project that was generated using industry-standard tools.

CURRENT PROJECT STRUCTURE (DO NOT MODIFY THESE):
{current_structure}

The project already has:
✅ Complete package.json with all dependencies and scripts
✅ package-lock.json for reproducible builds  
✅ Build configuration (vite.config.ts, tsconfig.json, etc.)
✅ ESLint and development tooling setup
✅ Working development and production scripts
✅ Proper .gitignore and project structure

USER STORY TO IMPLEMENT:
Title: {story.get('title', 'Unknown')}
Description: {story.get('description', 'No description')}
Acceptance Criteria:
{chr(10).join(f'- {criteria}' for criteria in story.get('acceptance_criteria', []))}

YOUR TASK:
1. ONLY add business logic components to implement this user story
2. Use the existing project structure and conventions
3. Import from existing files where appropriate
4. Follow the framework's best practices ({architecture.tech_stack})
5. DO NOT create any build configuration files
6. DO NOT modify package.json, vite.config.ts, or other config files
7. FOCUS on components, services, pages, and business logic

GUIDELINES:
- For React: Create components in src/components/, pages in src/pages/, services in src/services/
- For Vue: Create components in src/components/, views in src/views/, composables in src/composables/
- For Node API: Create routes in src/routes/, controllers in src/controllers/, services in src/services/
- Use TypeScript with proper typing
- Include proper error handling and validation
- Add unit tests in the existing test structure

EXAMPLE RESPONSE FORMAT:
src/components/UserLogin.tsx - React component for user authentication
src/services/AuthService.ts - Authentication service with proper error handling
src/types/User.ts - TypeScript interfaces for user data
src/components/__tests__/UserLogin.test.tsx - Unit tests for the component
"""

        return prompt
    
    def _get_project_structure_summary(self, files: List[GeneratedCode]) -> str:
        """Get a summary of the current project structure."""
        structure = {}
        
        for file in files:
            path_parts = file.file_path.split('/')
            current = structure
            
            for part in path_parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Add file
            filename = path_parts[-1]
            current[filename] = f"({file.file_type})"
        
        return self._format_structure(structure)
    
    def _format_structure(self, structure: Dict, indent: int = 0) -> str:
        """Format project structure for display."""
        lines = []
        for key, value in sorted(structure.items()):
            if isinstance(value, dict):
                lines.append("  " * indent + f"{key}/")
                lines.append(self._format_structure(value, indent + 1))
            else:
                lines.append("  " * indent + f"{key} {value}")
        return "\n".join(lines)
    
    def _generate_story_components(self, story: Dict[str, Any], architecture: Any) -> List[GeneratedCode]:
        """
        Generate business logic components for a story.
        This is a simplified implementation - in production, this would use AI.
        """
        components = []
        story_title = story.get('title', 'Unknown')
        story_id = story.get('story_id', 'unknown')
        
        # Determine tech stack and generate appropriate components
        if architecture.tech_stack.lower() in ['react_spa', 'react_fullstack']:
            components.extend(self._generate_react_components(story, story_id))
        elif architecture.tech_stack.lower() == 'vue_spa':
            components.extend(self._generate_vue_components(story, story_id))
        elif architecture.tech_stack.lower() == 'node_api':
            components.extend(self._generate_node_components(story, story_id))
        elif architecture.tech_stack.lower() == 'python_api':
            components.extend(self._generate_python_components(story, story_id))
        
        return components
    
    def _generate_react_components(self, story: Dict[str, Any], story_id: str) -> List[GeneratedCode]:
        """Generate React components for a story."""
        components = []
        story_title = story.get('title', 'Unknown')
        
        # Generate a component based on the story
        component_name = self._story_to_component_name(story_title)
        
        component_content = f"""import React, {{ useState, useEffect }} from 'react';

interface {component_name}Props {{
  // Add props as needed
}}

export const {component_name}: React.FC<{component_name}Props> = () => {{
  // State management
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<any>(null);

  // Implement business logic for: {story.get('description', '')}
  useEffect(() => {{
    const fetchData = async () => {{
      setLoading(true);
      setError(null);
      try {{
        // Add API call or data fetching logic here
        // const response = await fetch('/api/...');
        // const result = await response.json();
        // setData(result);
        setData({{}}); // Placeholder data
      }} catch (err) {{
        setError(err instanceof Error ? err.message : 'An error occurred');
      }} finally {{
        setLoading(false);
      }}
    }};
    
    fetchData();
  }}, []);

  // Implement acceptance criteria:
{chr(10).join(f'  // - {criteria}' for criteria in story.get('acceptance_criteria', []))}

  if (loading) {{
    return <div>Loading...</div>;
  }}

  if (error) {{
    return <div className="error">Error: {{error}}</div>;
  }}

  return (
    <div className="{component_name.lower()}">
      <h2>{story_title}</h2>
      <p>Component implementing: {story.get('description', '')}</p>
      {{/* Display data when available */}}
      {{data && (
        <div>
          <pre>{{JSON.stringify(data, null, 2)}}</pre>
        </div>
      )}}
      {{/* TODO: Implement UI based on acceptance criteria */}}
    </div>
  );
}};

export default {component_name};
"""
        
        components.append(GeneratedCode(
            file_path=f"src/components/{component_name}.tsx",
            content=component_content,
            component_id=f"comp_{story_id}",
            story_id=story_id,
            file_type="component",
            language="typescript"
        ))
        
        # Generate a simple service if needed
        service_content = f"""// Service for {story_title}
export class {component_name}Service {{
  async getData() {{
    // Implement data fetching logic
    try {{
      // Add API calls or business logic here
      return {{ success: true, data: [] }};
    }} catch (error) {{
      console.error('Error in {component_name}Service:', error);
      throw error;
    }}
  }}

  // Implement methods based on acceptance criteria:
{chr(10).join(f'  // - {criteria}' for criteria in story.get('acceptance_criteria', []))}
}}

export const {component_name.lower()}Service = new {component_name}Service();
"""
        
        components.append(GeneratedCode(
            file_path=f"src/services/{component_name}Service.ts",
            content=service_content,
            component_id=f"service_{story_id}",
            story_id=story_id,
            file_type="service",
            language="typescript"
        ))
        
        return components
    
    def _generate_vue_components(self, story: Dict[str, Any], story_id: str) -> List[GeneratedCode]:
        """Generate Vue components for a story."""
        # Similar to React but with Vue syntax
        components = []
        story_title = story.get('title', 'Unknown')
        component_name = self._story_to_component_name(story_title)
        
        vue_content = f"""<template>
  <div class="{component_name.lower()}">
    <h2>{story_title}</h2>
    <p>Component implementing: {story.get('description', '')}</p>
    <!-- TODO: Implement UI based on acceptance criteria -->
  </div>
</template>

<script setup lang="ts">
import {{ ref, onMounted }} from 'vue';

// State management
const loading = ref(false);
const error = ref<string | null>(null);

// Implement business logic for: {story.get('description', '')}
onMounted(() => {{
  // Add initialization logic
}});

// Implement acceptance criteria:
{chr(10).join(f'// - {criteria}' for criteria in story.get('acceptance_criteria', []))}
</script>

<style scoped>
.{component_name.lower()} {{
  /* Add component styles */
}}
</style>
"""
        
        components.append(GeneratedCode(
            file_path=f"src/components/{component_name}.vue",
            content=vue_content,
            component_id=f"comp_{story_id}",
            story_id=story_id,
            file_type="component",
            language="vue"
        ))
        
        return components
    
    def _generate_node_components(self, story: Dict[str, Any], story_id: str) -> List[GeneratedCode]:
        """Generate Node.js API components for a story."""
        components = []
        story_title = story.get('title', 'Unknown')
        
        # Generate API routes
        route_content = f"""// Routes for {story_title}
import {{ Router }} from 'express';
import {{ {story_title.replace(' ', '')}Controller }} from '../controllers/{story_title.replace(' ', '')}Controller';

const router = Router();

// Implement API endpoints based on acceptance criteria:
{chr(10).join(f'// - {criteria}' for criteria in story.get('acceptance_criteria', []))}

router.get('/', {story_title.replace(' ', '')}Controller.getAll);
router.get('/:id', {story_title.replace(' ', '')}Controller.getById);
router.post('/', {story_title.replace(' ', '')}Controller.create);
router.put('/:id', {story_title.replace(' ', '')}Controller.update);
router.delete('/:id', {story_title.replace(' ', '')}Controller.delete);

export default router;
"""
        
        components.append(GeneratedCode(
            file_path=f"src/routes/{story_title.replace(' ', '').lower()}.ts",
            content=route_content,
            component_id=f"route_{story_id}",
            story_id=story_id,
            file_type="route",
            language="typescript"
        ))
        
        return components
    
    def _generate_python_components(self, story: Dict[str, Any], story_id: str) -> List[GeneratedCode]:
        """Generate Python API components for a story."""
        components = []
        story_title = story.get('title', 'Unknown')
        
        # Generate FastAPI routes
        route_content = f'''"""
API routes for {story_title}
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional

router = APIRouter()

# Implement API endpoints based on acceptance criteria:
{chr(10).join(f'# - {criteria}' for criteria in story.get('acceptance_criteria', []))}

@router.get("/")
async def get_items():
    """Get all items for {story_title}."""
    # TODO: Implement business logic
    return {{"message": "Implement {story_title} logic"}}

@router.get("/{{item_id}}")
async def get_item(item_id: int):
    """Get specific item for {story_title}."""
    # TODO: Implement business logic
    return {{"item_id": item_id, "message": "Implement {story_title} logic"}}

@router.post("/")
async def create_item(item_data: dict):
    """Create new item for {story_title}."""
    # TODO: Implement business logic
    return {{"message": "Created item for {story_title}", "data": item_data}}
'''
        
        components.append(GeneratedCode(
            file_path=f"app/api/{story_title.replace(' ', '_').lower()}.py",
            content=route_content,
            component_id=f"route_{story_id}",
            story_id=story_id,
            file_type="route",
            language="python"
        ))
        
        return components
    
    def _story_to_component_name(self, story_title: str) -> str:
        """Convert story title to valid component name."""
        import re
        # Remove non-alphanumeric characters and title case
        name = re.sub(r'[^a-zA-Z0-9\s]', '', story_title)
        words = name.split()
        return ''.join(word.capitalize() for word in words)
    
    def _find_file_index(self, files: List[GeneratedCode], file_path: str) -> int:
        """Find index of file in list by file path."""
        for i, file in enumerate(files):
            if file.file_path == file_path:
                return i
        return -1
    
    def _dict_to_architecture(self, arch_dict: Dict[str, Any]):
        """Convert architecture dictionary to ProjectArchitecture object."""
        # Create a simple object that mimics ProjectArchitecture
        class SimpleArchitecture:
            def __init__(self, data):
                self.project_id = data.get('project_id', 'unknown')
                self.name = data.get('name', 'generated-project')
                self.tech_stack = data.get('tech_stack', 'react_spa')
                self.components = data.get('components', [])
                self.dependencies = data.get('dependencies', {})
                self.build_config = data.get('build_config', {})
        
        return SimpleArchitecture(arch_dict)