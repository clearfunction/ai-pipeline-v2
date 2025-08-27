"""
End-to-end tests for architecture planner lambda.
Tests the complete workflow: User stories -> Component architecture -> Tech stack decisions.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from shared.models.pipeline_models import (
    UserStory, StoryStatus, ComponentSpec, ProjectArchitecture, 
    TechStack, PipelineContext, LambdaResponse
)


class TestArchitecturePlannerE2E:
    """End-to-end tests for architecture planner workflow."""
    
    @pytest.fixture
    def sample_user_stories(self) -> List[UserStory]:
        """Create sample user stories for architecture planning."""
        return [
            UserStory(
                story_id="story-1",
                title="User Registration", 
                description="As a new user, I want to create an account so that I can access the application",
                acceptance_criteria=[
                    "User can enter email and password",
                    "System validates email format", 
                    "User receives confirmation email",
                    "Account is created in database"
                ],
                priority=1,
                estimated_effort=5,
                dependencies=[],
                status=StoryStatus.PENDING
            ),
            UserStory(
                story_id="story-2",
                title="User Login",
                description="As a registered user, I want to login so that I can access my account", 
                acceptance_criteria=[
                    "User can enter credentials",
                    "System validates credentials",
                    "User is redirected to dashboard on success",
                    "Error message shown for invalid credentials"
                ],
                priority=2,
                estimated_effort=3,
                dependencies=["User Registration"],
                status=StoryStatus.PENDING
            ),
            UserStory(
                story_id="story-3",
                title="User Dashboard",
                description="As a logged-in user, I want to see a dashboard with my information",
                acceptance_criteria=[
                    "Dashboard shows user profile",
                    "Dashboard shows recent activity",
                    "User can navigate to other features", 
                    "Dashboard loads within 2 seconds"
                ],
                priority=2,
                estimated_effort=8,
                dependencies=["User Login"],
                status=StoryStatus.PENDING
            ),
            UserStory(
                story_id="story-4", 
                title="Task Management",
                description="As a user, I want to create and manage tasks in my dashboard",
                acceptance_criteria=[
                    "User can create new tasks",
                    "User can edit existing tasks",
                    "User can mark tasks as complete",
                    "Tasks are persisted to database"
                ],
                priority=3,
                estimated_effort=13,
                dependencies=["User Dashboard"],
                status=StoryStatus.PENDING
            )
        ]
    
    @pytest.fixture 
    def pipeline_context(self, sample_user_stories: List[UserStory]) -> PipelineContext:
        """Create pipeline context from requirements synthesis stage."""
        return PipelineContext(
            execution_id="test-exec-123",
            project_id="test-project-456", 
            stage="requirements_synthesis",
            input_documents=[],  # Documents from previous stage
            metadata={
                "user_stories": [story.dict() for story in sample_user_stories],
                "total_stories": len(sample_user_stories),
                "total_effort": sum(story.estimated_effort for story in sample_user_stories),
                "project_type": "web_application",
                "complexity": "medium"
            }
        )
    
    @pytest.fixture
    def lambda_event(self, pipeline_context: PipelineContext) -> Dict[str, Any]:
        """Create lambda event for architecture planner."""
        return {
            "data": {
                "user_stories": [story.dict() for story in self.sample_user_stories],
                "pipeline_context": pipeline_context.dict()
            },
            "execution_id": "test-exec-123"
        }
    
    @pytest.fixture
    def mock_anthropic_service(self):
        """Mock Anthropic service for architecture planning."""
        with patch('shared.services.anthropic_service.AnthropicService') as mock:
            service_mock = Mock()
            
            # Mock architecture analysis response
            architecture_response = json.dumps({
                "tech_stack_recommendation": {
                    "primary_stack": "react_fullstack",
                    "reasoning": "React fullstack chosen for user management with dashboard UI and task management features",
                    "frontend": "React with TypeScript",
                    "backend": "Node.js with Express",
                    "database": "PostgreSQL",
                    "authentication": "JWT with bcrypt",
                    "deployment": "Docker containers"
                },
                "component_specifications": [
                    {
                        "component_id": "auth-service",
                        "name": "AuthenticationService", 
                        "type": "service",
                        "file_path": "src/services/auth.ts",
                        "dependencies": ["database", "crypto"],
                        "exports": ["register", "login", "validateToken"],
                        "story_ids": ["story-1", "story-2"],
                        "description": "Handles user registration, login, and token validation"
                    },
                    {
                        "component_id": "user-model",
                        "name": "UserModel",
                        "type": "model", 
                        "file_path": "src/models/User.ts",
                        "dependencies": ["database"],
                        "exports": ["User", "UserSchema"],
                        "story_ids": ["story-1", "story-2"],
                        "description": "User data model and database schema"
                    },
                    {
                        "component_id": "login-page",
                        "name": "LoginPage",
                        "type": "component",
                        "file_path": "src/components/auth/LoginPage.tsx", 
                        "dependencies": ["react", "auth-service"],
                        "exports": ["LoginPage"],
                        "story_ids": ["story-2"],
                        "description": "Login form component with validation"
                    },
                    {
                        "component_id": "register-page", 
                        "name": "RegisterPage",
                        "type": "component",
                        "file_path": "src/components/auth/RegisterPage.tsx",
                        "dependencies": ["react", "auth-service"],
                        "exports": ["RegisterPage"],
                        "story_ids": ["story-1"],
                        "description": "User registration form with validation"
                    },
                    {
                        "component_id": "dashboard-page",
                        "name": "DashboardPage", 
                        "type": "page",
                        "file_path": "src/pages/Dashboard.tsx",
                        "dependencies": ["react", "user-service", "task-service"],
                        "exports": ["Dashboard"],
                        "story_ids": ["story-3"],
                        "description": "Main dashboard showing user profile and activity"
                    },
                    {
                        "component_id": "task-service",
                        "name": "TaskService",
                        "type": "service",
                        "file_path": "src/services/tasks.ts",
                        "dependencies": ["database", "auth-service"],
                        "exports": ["createTask", "updateTask", "deleteTask", "getTasks"],
                        "story_ids": ["story-4"], 
                        "description": "Task CRUD operations and business logic"
                    }
                ],
                "build_configuration": {
                    "package_manager": "npm",
                    "bundler": "webpack",
                    "typescript": True,
                    "linting": "eslint",
                    "testing": "jest",
                    "dev_server": "webpack-dev-server",
                    "build_output": "dist/"
                }
            })
            
            service_mock.generate_text.return_value = architecture_response
            mock.return_value = service_mock
            yield service_mock
    
    @pytest.fixture
    def mock_dynamodb_table(self):
        """Mock DynamoDB table for storing component specs."""
        with patch('boto3.resource') as mock:
            table_mock = Mock()
            mock.return_value.Table.return_value = table_mock
            
            # Mock successful batch write
            table_mock.batch_write_item.return_value = {
                "ResponseMetadata": {"HTTPStatusCode": 200}
            }
            yield table_mock

    @patch.dict('os.environ', {
        'COMPONENT_SPECS_TABLE': 'test-component-specs-table',
        'ANTHROPIC_API_KEY': 'test-api-key'
    })
    def test_architecture_planner_e2e_success(
        self,
        lambda_event: Dict[str, Any],
        mock_anthropic_service: Mock,
        mock_dynamodb_table: Mock
    ):
        """
        Test complete architecture planning workflow.
        
        Expected flow:
        1. Lambda receives user stories from requirements synthesis
        2. User stories analyzed for complexity and patterns
        3. Anthropic generates tech stack recommendation and component architecture
        4. Components are validated and dependencies mapped
        5. Build configuration is generated
        6. Component specifications stored in DynamoDB
        7. Project architecture returned for next stage
        """
        # Import here to ensure environment variables are set
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from lambda_function import lambda_handler
        
        # Execute lambda handler
        result = lambda_handler(lambda_event, Mock())
        
        # Verify response structure
        assert result["status"] == "success"
        assert result["stage"] == "architecture_planning"
        assert result["next_stage"] == "story_management"
        assert "execution_id" in result
        
        # Verify project architecture in response
        assert "data" in result
        assert "project_architecture" in result["data"]
        architecture = result["data"]["project_architecture"]
        
        # Verify tech stack selection
        assert architecture["tech_stack"] == TechStack.REACT_FULLSTACK.value
        assert "build_config" in architecture
        assert architecture["build_config"]["typescript"] is True
        
        # Verify component specifications
        assert "components" in architecture
        components = architecture["components"]
        assert len(components) == 6  # Expected number of components
        
        # Verify specific components exist
        component_names = [comp["name"] for comp in components]
        assert "AuthenticationService" in component_names
        assert "LoginPage" in component_names
        assert "DashboardPage" in component_names
        assert "TaskService" in component_names
        
        # Verify component structure
        auth_service = next(comp for comp in components if comp["name"] == "AuthenticationService")
        assert auth_service["type"] == "service"
        assert "auth.ts" in auth_service["file_path"]
        assert "register" in auth_service["exports"]
        assert "login" in auth_service["exports"]
        assert "story-1" in auth_service["story_ids"]
        assert "story-2" in auth_service["story_ids"]
        
        # Verify user stories are mapped to components
        for story_id in ["story-1", "story-2", "story-3", "story-4"]:
            story_mapped = any(
                story_id in comp["story_ids"] 
                for comp in components
            )
            assert story_mapped, f"Story {story_id} not mapped to any component"
        
        # Verify pipeline context is updated
        assert "pipeline_context" in result["data"]
        updated_context = result["data"]["pipeline_context"]
        assert updated_context["stage"] == "architecture_planning"
        assert "architecture" in updated_context
        
        # Verify Anthropic API call for architecture planning
        mock_anthropic_service.generate_text.assert_called_once()
        api_call = mock_anthropic_service.generate_text.call_args[1]
        assert api_call["task_type"] == "architecture_planning"
        assert "tech stack" in api_call["prompt"].lower()
        assert "component" in api_call["prompt"].lower()
        
        # Verify DynamoDB storage
        mock_dynamodb_table.batch_write_item.assert_called_once()

    def test_architecture_planner_tech_stack_selection(
        self,
        lambda_event: Dict[str, Any], 
        mock_anthropic_service: Mock,
        mock_dynamodb_table: Mock
    ):
        """Test intelligent tech stack selection based on user stories."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from lambda_function import lambda_handler
        
        result = lambda_handler(lambda_event, Mock())
        
        architecture = result["data"]["project_architecture"]
        
        # Verify tech stack choice is appropriate for user management + dashboard + tasks
        assert architecture["tech_stack"] == TechStack.REACT_FULLSTACK.value
        
        # Verify build configuration matches tech stack
        build_config = architecture["build_config"]
        assert build_config["package_manager"] == "npm"
        assert build_config["typescript"] is True
        assert build_config["bundler"] == "webpack"
        assert "eslint" in build_config["linting"]

    def test_architecture_planner_component_dependency_mapping(
        self,
        lambda_event: Dict[str, Any],
        mock_anthropic_service: Mock,
        mock_dynamodb_table: Mock
    ):
        """Test that component dependencies are correctly mapped."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from lambda_function import lambda_handler
        
        result = lambda_handler(lambda_event, Mock())
        
        components = result["data"]["project_architecture"]["components"]
        
        # Verify dependency relationships
        dashboard_component = next(comp for comp in components if comp["name"] == "DashboardPage")
        assert "task-service" in dashboard_component["dependencies"]
        
        task_service = next(comp for comp in components if comp["name"] == "TaskService") 
        assert "auth-service" in task_service["dependencies"]
        
        # Verify all dependencies exist as components
        component_ids = [comp["component_id"] for comp in components]
        for component in components:
            for dependency in component["dependencies"]:
                if not dependency.startswith("react") and not dependency.startswith("database"):
                    assert dependency in component_ids, f"Dependency {dependency} not found in components"

    def test_architecture_planner_story_to_component_mapping(
        self,
        lambda_event: Dict[str, Any],
        mock_anthropic_service: Mock,
        mock_dynamodb_table: Mock
    ):
        """Test that each user story is mapped to appropriate components."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from lambda_function import lambda_handler
        
        result = lambda_handler(lambda_event, Mock())
        
        components = result["data"]["project_architecture"]["components"]
        
        # Verify each story is mapped to at least one component
        story_ids = ["story-1", "story-2", "story-3", "story-4"]
        for story_id in story_ids:
            mapped_components = [
                comp["name"] for comp in components 
                if story_id in comp["story_ids"]
            ]
            assert len(mapped_components) > 0, f"Story {story_id} not mapped to any component"
        
        # Verify story mapping makes logical sense
        # Registration story should map to registration components
        registration_components = [
            comp["name"] for comp in components
            if "story-1" in comp["story_ids"]
        ]
        assert "RegisterPage" in registration_components
        assert "AuthenticationService" in registration_components
        
        # Dashboard story should map to dashboard components
        dashboard_components = [
            comp["name"] for comp in components
            if "story-3" in comp["story_ids"] 
        ]
        assert "DashboardPage" in dashboard_components

    def test_architecture_planner_error_handling(self):
        """Test error handling when architecture planning fails."""
        # Event with missing user stories
        event = {
            "data": {
                "pipeline_context": {
                    "execution_id": "test-error-exec",
                    "project_id": "test-project",
                    "stage": "requirements_synthesis",
                    "input_documents": [],
                    "metadata": {}
                }
            },
            "execution_id": "test-error-exec"
        }
        
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from lambda_function import lambda_handler
        
        result = lambda_handler(event, Mock())
        
        # Verify error response
        assert result["status"] == "failed"
        assert "error" in result
        assert result["stage"] == "architecture_planning"

    @patch.dict('os.environ', {
        'COMPONENT_SPECS_TABLE': 'test-component-specs-table',
        'ANTHROPIC_API_KEY': 'test-api-key'
    })
    def test_architecture_planner_handles_anthropic_failure(
        self,
        lambda_event: Dict[str, Any],
        mock_dynamodb_table: Mock
    ):
        """Test handling when Anthropic API fails."""
        with patch('shared.services.anthropic_service.AnthropicService') as mock:
            service_mock = Mock()
            service_mock.generate_text.side_effect = Exception("Anthropic API error")
            mock.return_value = service_mock
            
            import sys
            import os
            sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
            from lambda_function import lambda_handler
            
            result = lambda_handler(lambda_event, Mock())
            
            # Verify error handling
            assert result["status"] == "failed"
            assert "Anthropic API error" in result["error"]

    def test_architecture_planner_validates_component_specs(
        self,
        lambda_event: Dict[str, Any],
        mock_anthropic_service: Mock,
        mock_dynamodb_table: Mock
    ):
        """Test that generated component specs pass validation."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from lambda_function import lambda_handler
        
        result = lambda_handler(lambda_event, Mock())
        
        components = result["data"]["project_architecture"]["components"]
        
        # Verify each component has required fields
        required_fields = ["component_id", "name", "type", "file_path", "dependencies", "exports", "story_ids"]
        for component in components:
            for field in required_fields:
                assert field in component, f"Component missing required field: {field}"
                assert component[field] is not None, f"Component field '{field}' is None"
            
            # Verify file path is reasonable
            assert component["file_path"].startswith("src/")
            
            # Verify component type is valid
            valid_types = ["component", "page", "service", "model", "util"]
            assert component["type"] in valid_types
            
            # Verify exports is a list
            assert isinstance(component["exports"], list)
            assert len(component["exports"]) > 0
            
            # Verify story_ids is a list
            assert isinstance(component["story_ids"], list)
            assert len(component["story_ids"]) > 0

    def test_architecture_planner_creates_project_architecture(
        self,
        lambda_event: Dict[str, Any],
        mock_anthropic_service: Mock,
        mock_dynamodb_table: Mock
    ):
        """Test that complete project architecture is created."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from lambda_function import lambda_handler
        
        result = lambda_handler(lambda_event, Mock())
        
        # Verify project architecture structure
        architecture = result["data"]["project_architecture"]
        
        # Required fields for project architecture
        required_fields = ["project_id", "name", "tech_stack", "components", "user_stories", "build_config"]
        for field in required_fields:
            assert field in architecture, f"Architecture missing required field: {field}"
        
        # Verify project details
        assert architecture["project_id"] == "test-project-456"
        assert architecture["tech_stack"] in [stack.value for stack in TechStack]
        
        # Verify user stories are preserved
        assert len(architecture["user_stories"]) == 4
        
        # Verify components and user stories are consistent
        component_story_ids = set()
        for component in architecture["components"]:
            component_story_ids.update(component["story_ids"])
        
        architecture_story_ids = {story["story_id"] for story in architecture["user_stories"]}
        assert component_story_ids == architecture_story_ids, "Component story mapping inconsistent with user stories"