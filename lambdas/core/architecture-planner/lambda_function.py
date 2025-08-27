"""
Architecture Planner Lambda - Simplified version without pydantic dependencies.
Designs project architecture and tech stack based on user stories.
"""

import json
import os
from typing import Dict, Any, List
import boto3
from datetime import datetime

# Configure logging
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
COMPONENT_SPECS_TABLE = os.environ.get('COMPONENT_SPECS_TABLE', 'ai-pipeline-v2-component-specs')


class SimpleArchitecturePlanner:
    """Plans project architecture and component structure from user stories."""
    
    def __init__(self):
        """Initialize the architecture planner."""
        self.logger = logger
        self.component_specs_table = dynamodb.Table(COMPONENT_SPECS_TABLE)
    
    def plan_architecture(
        self, 
        user_stories: List[Dict[str, Any]], 
        execution_id: str,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Plan complete project architecture from user stories.
        """
        # Determine tech stack based on story analysis
        tech_stack = self._determine_tech_stack(user_stories)
        
        # Design components for the selected tech stack
        components = self._design_components(user_stories, tech_stack)
        
        # Generate build configuration
        build_config = self._generate_build_config(tech_stack)
        
        # Map stories to components
        for story in user_stories:
            story['assigned_components'] = self._assign_components_to_story(story, components)
        
        # Create architecture dictionary
        architecture = {
            "project_id": project_id,
            "name": f"ai-generated-project-{execution_id[:8]}",
            "tech_stack": tech_stack,
            "components": components,
            "user_stories": user_stories,
            "dependencies": self._extract_dependencies(tech_stack),
            "build_config": build_config,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store component specifications
        for component in components:
            self._store_component_spec(component)
        
        self.logger.info(f"Planned architecture with {len(components)} components for {tech_stack}")
        return architecture
    
    def _determine_tech_stack(self, user_stories: List[Dict[str, Any]]) -> str:
        """
        Determine optimal tech stack based on user stories.
        Simple rule-based approach.
        """
        # Calculate complexity and patterns
        total_effort = sum(story.get('estimated_effort', 0) for story in user_stories)
        story_titles = ' '.join([story.get('title', '').lower() for story in user_stories])
        story_descriptions = ' '.join([story.get('description', '').lower() for story in user_stories])
        all_text = story_titles + ' ' + story_descriptions
        
        # Detect patterns
        has_auth = any(keyword in all_text for keyword in ['auth', 'login', 'user', 'password', 'signin'])
        has_dashboard = any(keyword in all_text for keyword in ['dashboard', 'analytics', 'chart', 'graph'])
        has_realtime = any(keyword in all_text for keyword in ['realtime', 'real-time', 'websocket', 'notification'])
        has_api_only = 'api' in all_text and not any(keyword in all_text for keyword in ['ui', 'frontend', 'dashboard', 'page'])
        
        # Decision tree
        if has_api_only:
            return "node_api"
        elif has_realtime or (has_auth and has_dashboard):
            return "react_fullstack"
        elif has_dashboard:
            return "react_spa"
        elif total_effort <= 15:
            return "vue_spa"
        else:
            return "react_spa"
    
    def _design_components(self, user_stories: List[Dict[str, Any]], tech_stack: str) -> List[Dict[str, Any]]:
        """
        Design component architecture for the project.
        """
        components = []
        component_id = 1
        
        # Base components for each tech stack
        if tech_stack in ["react_spa", "react_fullstack"]:
            # Core React components
            components.extend([
                {
                    "component_id": f"comp_{component_id:03d}",
                    "name": "App",
                    "type": "component",
                    "file_path": "src/App.tsx",
                    "dependencies": [],
                    "exports": ["App"],
                    "story_ids": [],
                    "created_at": datetime.utcnow().isoformat()
                },
                {
                    "component_id": f"comp_{component_id+1:03d}",
                    "name": "Layout",
                    "type": "component",
                    "file_path": "src/components/Layout.tsx",
                    "dependencies": [],
                    "exports": ["Layout"],
                    "story_ids": [],
                    "created_at": datetime.utcnow().isoformat()
                }
            ])
            component_id += 2
            
            # Add components based on user stories
            for story in user_stories:
                title = story.get('title', '').replace(' ', '')
                if 'auth' in story.get('title', '').lower():
                    components.append({
                        "component_id": f"comp_{component_id:03d}",
                        "name": "LoginPage",
                        "type": "page",
                        "file_path": "src/pages/LoginPage.tsx",
                        "dependencies": ["AuthService"],
                        "exports": ["LoginPage"],
                        "story_ids": [story['story_id']],
                        "created_at": datetime.utcnow().isoformat()
                    })
                    component_id += 1
                    components.append({
                        "component_id": f"comp_{component_id:03d}",
                        "name": "AuthService",
                        "type": "service",
                        "file_path": "src/services/AuthService.ts",
                        "dependencies": [],
                        "exports": ["AuthService", "useAuth"],
                        "story_ids": [story['story_id']],
                        "created_at": datetime.utcnow().isoformat()
                    })
                    component_id += 1
                elif 'task' in story.get('title', '').lower():
                    components.append({
                        "component_id": f"comp_{component_id:03d}",
                        "name": "TaskList",
                        "type": "component",
                        "file_path": "src/components/TaskList.tsx",
                        "dependencies": ["TaskService"],
                        "exports": ["TaskList"],
                        "story_ids": [story['story_id']],
                        "created_at": datetime.utcnow().isoformat()
                    })
                    component_id += 1
                    components.append({
                        "component_id": f"comp_{component_id:03d}",
                        "name": "TaskService",
                        "type": "service",
                        "file_path": "src/services/TaskService.ts",
                        "dependencies": [],
                        "exports": ["TaskService"],
                        "story_ids": [story['story_id']],
                        "created_at": datetime.utcnow().isoformat()
                    })
                    component_id += 1
                elif 'dashboard' in story.get('title', '').lower():
                    components.append({
                        "component_id": f"comp_{component_id:03d}",
                        "name": "Dashboard",
                        "type": "page",
                        "file_path": "src/pages/Dashboard.tsx",
                        "dependencies": ["TaskList"],
                        "exports": ["Dashboard"],
                        "story_ids": [story['story_id']],
                        "created_at": datetime.utcnow().isoformat()
                    })
                    component_id += 1
        
        elif tech_stack == "vue_spa":
            # Vue components
            components.append({
                "component_id": f"comp_{component_id:03d}",
                "name": "App",
                "type": "component",
                "file_path": "src/App.vue",
                "dependencies": [],
                "exports": ["default"],
                "story_ids": [],
                "created_at": datetime.utcnow().isoformat()
            })
            component_id += 1
        
        elif tech_stack == "node_api":
            # Node API components
            components.extend([
                {
                    "component_id": f"comp_{component_id:03d}",
                    "name": "server",
                    "type": "config",
                    "file_path": "src/server.js",
                    "dependencies": [],
                    "exports": ["app"],
                    "story_ids": [],
                    "created_at": datetime.utcnow().isoformat()
                },
                {
                    "component_id": f"comp_{component_id+1:03d}",
                    "name": "routes",
                    "type": "config",
                    "file_path": "src/routes/index.js",
                    "dependencies": [],
                    "exports": ["router"],
                    "story_ids": [],
                    "created_at": datetime.utcnow().isoformat()
                }
            ])
            component_id += 2
        
        return components
    
    def _generate_build_config(self, tech_stack: str) -> Dict[str, Any]:
        """Generate build configuration that matches actual template capabilities."""
        configs = {
            "react_spa": {
                "package_manager": "npm",
                "build_command": "npm run build",
                "dev_command": "npm run dev",
                "test_command": "npm run test:ci",  # Updated to match actual React template
                "test_coverage_command": "npm run test:coverage",
                "type_check_command": "npm run type-check",
                "bundler": "vite"
            },
            "react_fullstack": {
                "package_manager": "npm",
                "build_command": "npm run build",
                "dev_command": "npm run dev",
                "test_command": "npm run test:ci",  # Updated to match actual React template
                "test_coverage_command": "npm run test:coverage",
                "type_check_command": "npm run type-check",
                "bundler": "vite",
                "backend": "express"
            },
            "vue_spa": {
                "package_manager": "npm",
                "build_command": "npm run build",
                "dev_command": "npm run dev",  # Updated - Vue uses dev not serve
                "test_command": "npm run test:unit",  # Updated to match actual Vue template
                "test_coverage_command": "npm run test:coverage",
                "test_e2e_command": "npm run test:e2e",
                "test_component_command": "npm run test:component",
                "bundler": "vite"
            },
            "node_api": {
                "package_manager": "npm",
                "build_command": "npm run build",  # This is just a placeholder for Node.js
                "dev_command": "npm run dev",
                "test_command": "npm run test:unit",  # Updated to match actual Node.js template
                "test_integration_command": "npm run test:integration",
                "test_security_command": "npm run test:security",
                "test_coverage_command": "npm run test:coverage",
                "runtime": "node"
            }
        }
        return configs.get(tech_stack, configs["react_spa"])
    
    def _extract_dependencies(self, tech_stack: str) -> Dict[str, str]:
        """Extract package dependencies for the tech stack."""
        deps = {
            "react_spa": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "typescript": "^5.0.0",
                "vite": "^5.0.0"
            },
            "react_fullstack": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "express": "^4.18.0",
                "typescript": "^5.0.0"
            },
            "vue_spa": {
                "vue": "^3.3.0",
                "typescript": "^5.0.0",
                "vite": "^5.0.0"
            },
            "node_api": {
                "express": "^4.18.0",
                "cors": "^2.8.5",
                "dotenv": "^16.0.0"
            }
        }
        return deps.get(tech_stack, {})
    
    def _assign_components_to_story(self, story: Dict[str, Any], components: List[Dict[str, Any]]) -> List[str]:
        """Assign relevant components to a user story."""
        assigned = []
        story_keywords = (story.get('title', '') + ' ' + story.get('description', '')).lower()
        
        for component in components:
            # Check if component was specifically created for this story
            if story['story_id'] in component.get('story_ids', []):
                assigned.append(component['component_id'])
            # Or if component name matches story keywords
            elif any(keyword in story_keywords for keyword in component['name'].lower().split()):
                assigned.append(component['component_id'])
        
        return assigned
    
    def _store_component_spec(self, component: Dict[str, Any]) -> None:
        """Store component specification in DynamoDB."""
        try:
            self.component_specs_table.put_item(Item=component)
        except Exception as e:
            self.logger.error(f"Failed to store component {component['component_id']}: {e}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for architecture planning.
    """
    # Generate execution ID
    execution_id = f"arch_plan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{context.aws_request_id[:8] if context else 'local'}"
    
    logger.info(f"Starting architecture planning with execution_id: {execution_id}")
    logger.info(f"Received event: {json.dumps(event, default=str)}")
    
    try:
        # Handle both Step Functions input and direct lambda input
        if 'requirementsSynthesizerResult' in event:
            # Step Functions format - extract from requirements synthesizer result
            req_result = event.get('requirementsSynthesizerResult', {}).get('Payload', {})
            data = req_result.get('data', {})
            user_stories = data.get('user_stories', [])
            pipeline_context = data.get('pipeline_context', {})
        else:
            # Direct lambda input format
            data = event.get('data', {})
            user_stories = data.get('user_stories', [])
            pipeline_context = data.get('pipeline_context', {})
        
        if not user_stories:
            raise ValueError("No user stories provided")
        
        project_id = pipeline_context.get('project_id', 'unknown')
        
        # Plan architecture
        planner = SimpleArchitecturePlanner()
        architecture = planner.plan_architecture(user_stories, execution_id, project_id)
        
        # Create pipeline context
        updated_context = {
            "execution_id": execution_id,
            "project_id": project_id,
            "stage": "architecture_planning",
            "user_stories": user_stories,
            "architecture": architecture,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Prepare response
        response = {
            "status": "success",
            "message": f"Architecture planned successfully with {len(architecture['components'])} components",
            "execution_id": execution_id,
            "stage": "architecture_planning",
            "project_id": project_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "architecture": architecture,
                "pipeline_context": updated_context
            },
            "next_stage": "story_execution"
        }
        
        logger.info(f"Architecture planning completed successfully for execution_id: {execution_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error in architecture planning: {str(e)}", exc_info=True)
        
        # Return proper error status - raise exception for Step Functions to handle
        error_msg = f"Architecture planning failed: {str(e)}"
        raise RuntimeError(error_msg)