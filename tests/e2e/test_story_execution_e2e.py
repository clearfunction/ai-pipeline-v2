"""
End-to-end tests for story-to-code generation workflow.
Tests the complete journey from user stories to generated code files.
"""

import pytest
import tempfile
import os
from typing import List, Dict, Any
from unittest.mock import Mock, patch
import json

from shared.models.pipeline_models import (
    UserStory, StoryStatus, ComponentSpec, ProjectArchitecture, 
    TechStack, GeneratedCode, PipelineContext
)


class TestStoryExecutionE2E:
    """End-to-end tests for story execution and code generation."""
    
    @pytest.fixture
    def react_spa_architecture(self) -> ProjectArchitecture:
        """Sample React SPA architecture for testing."""
        components = [
            ComponentSpec(
                component_id="comp_001",
                name="App",
                type="component",
                file_path="src/App.tsx",
                dependencies=[],
                exports=["App"],
                story_ids=["story-1"]
            ),
            ComponentSpec(
                component_id="comp_002", 
                name="LoginPage",
                type="page",
                file_path="src/pages/LoginPage.tsx",
                dependencies=["AuthService", "Button"],
                exports=["LoginPage"],
                story_ids=["story-1"]
            ),
            ComponentSpec(
                component_id="comp_003",
                name="AuthService",
                type="service", 
                file_path="src/services/AuthService.ts",
                dependencies=["ApiClient"],
                exports=["AuthService"],
                story_ids=["story-1"]
            )
        ]
        
        user_stories = [
            UserStory(
                story_id="story-1",
                title="User Authentication",
                description="As a user, I want to login with email and password",
                acceptance_criteria=[
                    "User can enter email and password",
                    "System validates credentials",
                    "User is redirected to dashboard on success"
                ],
                priority=1,
                estimated_effort=8,
                dependencies=[],
                status=StoryStatus.PENDING,
                assigned_components=["comp_001", "comp_002", "comp_003"]
            )
        ]
        
        return ProjectArchitecture(
            project_id="test-project-001",
            name="React Authentication App",
            tech_stack=TechStack.REACT_SPA,
            components=components,
            user_stories=user_stories,
            dependencies={"react": "^18.2.0", "typescript": "^5.0.0"},
            build_config={
                "package_manager": "npm",
                "bundler": "vite",
                "dev_command": "npm run dev"
            }
        )
    
    def test_story_execution_generates_working_code(self, react_spa_architecture: ProjectArchitecture):
        """Test that story execution generates working, compilable code."""
        from lambdas.core.story_executor.lambda_function import lambda_handler
        
        # Create event with architecture and stories
        event = {
            "data": {
                "pipeline_context": {
                    "execution_id": "exec-001", 
                    "project_id": "test-project-001",
                    "stage": "story_execution",
                    "architecture": react_spa_architecture.dict(),
                    "metadata": {"tech_stack": "react_spa"}
                },
                "stories_to_execute": [story.dict() for story in react_spa_architecture.user_stories]
            }
        }
        
        # Mock context
        context = Mock()
        context.aws_request_id = "req-123"
        
        # Execute story executor lambda
        result = lambda_handler(event, context)
        
        # Verify successful execution
        assert result["status"] == "success"
        assert result["stage"] == "story_execution"
        
        # Verify generated code structure
        generated_code = result["data"]["generated_code"]
        assert len(generated_code) >= 3  # App, LoginPage, AuthService
        
        # Verify each component has valid code
        for code_file in generated_code:
            assert code_file["file_path"]
            assert code_file["content"]
            assert len(code_file["content"].strip()) > 0
            
            # Verify TypeScript/JSX syntax basics
            if code_file["file_path"].endswith('.tsx'):
                assert "import React" in code_file["content"]
                assert "export" in code_file["content"]
            elif code_file["file_path"].endswith('.ts'):
                assert "export" in code_file["content"]
    
    def test_story_execution_handles_dependencies_correctly(self, react_spa_architecture: ProjectArchitecture):
        """Test that story execution respects component dependencies."""
        from lambdas.core.story_executor.code_generator import CodeGenerator
        
        generator = CodeGenerator(react_spa_architecture.tech_stack)
        
        # Generate code for all components
        generated_files = []
        for component in react_spa_architecture.components:
            code = generator.generate_component_code(
                component, 
                react_spa_architecture.user_stories[0],
                react_spa_architecture.components
            )
            generated_files.append(code)
        
        # Verify dependency imports
        login_page = next(f for f in generated_files if "LoginPage" in f.file_path)
        auth_service = next(f for f in generated_files if "AuthService" in f.file_path)
        
        # LoginPage should import AuthService
        assert "AuthService" in login_page.content
        assert "services/AuthService" in login_page.content or "../services/AuthService" in login_page.content
        
        # AuthService should import ApiClient (implied dependency)
        assert "ApiClient" in auth_service.content or "axios" in auth_service.content

    def test_story_execution_generates_project_structure(self, react_spa_architecture: ProjectArchitecture):
        """Test that story execution creates proper project file structure."""
        from lambdas.core.story_executor.project_initializer import ProjectInitializer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            initializer = ProjectInitializer(react_spa_architecture)
            
            # Initialize project structure
            project_path = initializer.create_project_structure(temp_dir)
            
            # Verify directory structure
            assert os.path.exists(os.path.join(project_path, "src"))
            assert os.path.exists(os.path.join(project_path, "src", "pages"))
            assert os.path.exists(os.path.join(project_path, "src", "services"))
            assert os.path.exists(os.path.join(project_path, "src", "components"))
            
            # Verify configuration files
            assert os.path.exists(os.path.join(project_path, "package.json"))
            assert os.path.exists(os.path.join(project_path, "tsconfig.json"))
            assert os.path.exists(os.path.join(project_path, "vite.config.ts"))
            
            # Verify package.json has correct dependencies
            with open(os.path.join(project_path, "package.json"), "r") as f:
                package_json = json.load(f)
                assert "react" in package_json["dependencies"]
                assert "typescript" in package_json["devDependencies"]

    def test_incremental_story_execution(self, react_spa_architecture: ProjectArchitecture):
        """Test that stories can be executed incrementally without breaking existing code."""
        from lambdas.core.story_executor.incremental_executor import IncrementalExecutor
        
        # Add a second story
        second_story = UserStory(
            story_id="story-2",
            title="User Profile",  
            description="As a user, I want to view and edit my profile",
            acceptance_criteria=[
                "User can view profile information",
                "User can edit profile fields", 
                "Changes are saved automatically"
            ],
            priority=2,
            estimated_effort=5,
            dependencies=["User Authentication"],
            status=StoryStatus.PENDING,
            assigned_components=["comp_002"]  # Reuse LoginPage, add ProfilePage
        )
        
        # Add ProfilePage component
        profile_component = ComponentSpec(
            component_id="comp_004",
            name="ProfilePage",
            type="page",
            file_path="src/pages/ProfilePage.tsx", 
            dependencies=["AuthService", "UserService"],
            exports=["ProfilePage"],
            story_ids=["story-2"]
        )
        
        react_spa_architecture.components.append(profile_component)
        react_spa_architecture.user_stories.append(second_story)
        
        executor = IncrementalExecutor(react_spa_architecture)
        
        # Execute first story
        first_result = executor.execute_story(react_spa_architecture.user_stories[0])
        assert len(first_result.generated_files) == 3  # App, LoginPage, AuthService
        
        # Execute second story incrementally
        second_result = executor.execute_story(react_spa_architecture.user_stories[1])
        
        # Should generate additional files without breaking existing ones
        assert len(second_result.generated_files) >= 1  # At least ProfilePage
        
        # Verify no conflicts in routing or imports
        profile_file = next(f for f in second_result.generated_files if "ProfilePage" in f.file_path)
        assert "import" in profile_file.content
        assert "export" in profile_file.content

    def test_code_quality_and_standards_compliance(self, react_spa_architecture: ProjectArchitecture):
        """Test that generated code follows quality standards and best practices."""
        from lambdas.core.story_executor.code_quality_validator import CodeQualityValidator
        from lambdas.core.story_executor.code_generator import CodeGenerator
        
        generator = CodeGenerator(react_spa_architecture.tech_stack)
        validator = CodeQualityValidator()
        
        # Generate code for LoginPage component
        login_component = react_spa_architecture.components[1]  # LoginPage
        story = react_spa_architecture.user_stories[0]
        
        generated_code = generator.generate_component_code(
            login_component, story, react_spa_architecture.components
        )
        
        # Validate code quality
        quality_report = validator.validate_code(generated_code)
        
        # Assert quality standards
        assert quality_report.is_valid
        assert quality_report.typescript_compliance
        assert quality_report.react_best_practices
        assert len(quality_report.lint_errors) == 0
        assert quality_report.test_coverage_estimate > 0.7  # Good test coverage potential
        
        # Verify specific code patterns
        assert "useState" in generated_code.content or "useEffect" in generated_code.content
        assert "interface" in generated_code.content or "type" in generated_code.content
        assert "export default" in generated_code.content or "export const" in generated_code.content

    def test_story_execution_with_error_handling(self, react_spa_architecture: ProjectArchitecture):
        """Test story execution handles errors gracefully with proper rollback."""
        from lambdas.core.story_executor.lambda_function import lambda_handler
        
        # Create event with invalid story (missing required fields)
        invalid_story = {
            "story_id": "invalid-story",
            "title": "",  # Empty title should cause validation error
            "description": "Invalid story for testing error handling",
            "acceptance_criteria": [],
            "priority": 1,
            "estimated_effort": 0,  # Zero effort should be invalid
            "dependencies": [],
            "status": "pending",
            "assigned_components": ["nonexistent-component"]  # Invalid component ID
        }
        
        event = {
            "data": {
                "pipeline_context": {
                    "execution_id": "exec-error-001",
                    "project_id": "test-project-001", 
                    "stage": "story_execution",
                    "architecture": react_spa_architecture.dict(),
                    "metadata": {"tech_stack": "react_spa"}
                },
                "stories_to_execute": [invalid_story]
            }
        }
        
        context = Mock()
        context.aws_request_id = "req-error-123"
        
        # Execute with invalid story
        result = lambda_handler(event, context)
        
        # Verify error handling
        assert result["status"] == "failed"
        assert "error" in result
        assert "validation" in result["error"].lower() or "invalid" in result["error"].lower()
        
        # Verify no partial files were created
        assert result["data"].get("generated_code", []) == []

    @patch('shared.services.anthropic_service.AnthropicService')
    def test_story_execution_uses_anthropic_for_complex_logic(self, mock_anthropic, react_spa_architecture: ProjectArchitecture):
        """Test that complex business logic uses Anthropic for intelligent code generation."""
        from lambdas.core.story_executor.code_generator import CodeGenerator
        
        # Mock Anthropic response for complex component generation
        service_mock = Mock()
        service_mock.generate_text.return_value = """
        import React, { useState } from 'react';
        import { AuthService } from '../services/AuthService';
        
        export const LoginPage: React.FC = () => {
            const [email, setEmail] = useState('');
            const [password, setPassword] = useState('');
            
            const handleLogin = async (e: React.FormEvent) => {
                e.preventDefault();
                try {
                    await AuthService.login(email, password);
                    // Redirect logic here
                } catch (error) {
                    console.error('Login failed:', error);
                }
            };
            
            return (
                <div className="login-page">
                    <form onSubmit={handleLogin}>
                        <input 
                            type="email" 
                            value={email} 
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="Email"
                        />
                        <input 
                            type="password" 
                            value={password} 
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Password"
                        />
                        <button type="submit">Login</button>
                    </form>
                </div>
            );
        };
        """
        mock_anthropic.return_value = service_mock
        
        generator = CodeGenerator(react_spa_architecture.tech_stack)
        
        # Generate complex login component
        login_component = react_spa_architecture.components[1]  # LoginPage
        story = react_spa_architecture.user_stories[0]
        
        generated_code = generator.generate_component_code(
            login_component, story, react_spa_architecture.components
        )
        
        # Verify Anthropic was used for complex logic
        service_mock.generate_text.assert_called_once()
        call_args = service_mock.generate_text.call_args[1]
        assert call_args["task_type"] == "code_generation"
        assert "React" in call_args["prompt"]
        assert "LoginPage" in call_args["prompt"]
        
        # Verify generated code quality
        assert "useState" in generated_code.content
        assert "handleLogin" in generated_code.content
        assert "form" in generated_code.content.lower()
        assert "AuthService" in generated_code.content