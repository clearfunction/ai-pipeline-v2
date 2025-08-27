"""
Unit tests for intelligent code generation logic.
Tests the core code generation functionality with component awareness.
"""

import pytest
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from shared.models.pipeline_models import (
    UserStory, StoryStatus, ComponentSpec, TechStack, GeneratedCode
)


class TestCodeGenerator:
    """Unit tests for code generation logic."""
    
    @pytest.fixture
    def login_component(self) -> ComponentSpec:
        """Sample login page component."""
        return ComponentSpec(
            component_id="comp_001",
            name="LoginPage",
            type="page",
            file_path="src/pages/LoginPage.tsx",
            dependencies=["AuthService", "Button"],
            exports=["LoginPage"],
            story_ids=["story-1"]
        )
    
    @pytest.fixture 
    def auth_service_component(self) -> ComponentSpec:
        """Sample authentication service component."""
        return ComponentSpec(
            component_id="comp_002",
            name="AuthService",
            type="service",
            file_path="src/services/AuthService.ts",
            dependencies=["ApiClient"],
            exports=["AuthService"],
            story_ids=["story-1"]
        )
    
    @pytest.fixture
    def user_auth_story(self) -> UserStory:
        """Sample user authentication story."""
        return UserStory(
            story_id="story-1",
            title="User Authentication",
            description="As a user, I want to login with email and password",
            acceptance_criteria=[
                "User can enter email and password",
                "System validates credentials", 
                "User is redirected to dashboard on success",
                "Error messages are displayed for invalid credentials"
            ],
            priority=1,
            estimated_effort=8,
            dependencies=[],
            status=StoryStatus.PENDING,
            assigned_components=["comp_001", "comp_002"]
        )
    
    def test_react_component_generation(self, login_component: ComponentSpec, user_auth_story: UserStory):
        """Test generation of React functional components."""
        # Import after creating directory structure
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from code_generator import CodeGenerator
        
        generator = CodeGenerator(TechStack.REACT_SPA)
        
        # Generate login page component
        generated_code = generator.generate_component_code(
            login_component, user_auth_story, [login_component]
        )
        
        # Verify basic React structure
        assert generated_code.file_path == "src/pages/LoginPage.tsx"
        assert "import React" in generated_code.content
        assert "export const LoginPage" in generated_code.content or "export default" in generated_code.content
        assert "React.FC" in generated_code.content or ": FC" in generated_code.content
        
        # Verify functional requirements from story
        assert "email" in generated_code.content.lower()
        assert "password" in generated_code.content.lower()
        assert "form" in generated_code.content.lower() or "input" in generated_code.content.lower()
        assert "useState" in generated_code.content
        
        # Verify TypeScript typing
        assert "interface" in generated_code.content or "type" in generated_code.content
    
    def test_service_class_generation(self, auth_service_component: ComponentSpec, user_auth_story: UserStory):
        """Test generation of TypeScript service classes."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from code_generator import CodeGenerator
        
        generator = CodeGenerator(TechStack.REACT_SPA)
        
        # Generate auth service
        generated_code = generator.generate_component_code(
            auth_service_component, user_auth_story, [auth_service_component]
        )
        
        # Verify service structure
        assert generated_code.file_path == "src/services/AuthService.ts"
        assert "export class AuthService" in generated_code.content or "export const AuthService" in generated_code.content
        assert "login" in generated_code.content
        assert "async" in generated_code.content
        
        # Verify API integration patterns
        assert "fetch" in generated_code.content or "axios" in generated_code.content or "ApiClient" in generated_code.content
        assert "Promise" in generated_code.content or "async" in generated_code.content
        
        # Verify error handling
        assert "try" in generated_code.content or "catch" in generated_code.content or "throw" in generated_code.content

    def test_dependency_aware_imports(self, login_component: ComponentSpec, auth_service_component: ComponentSpec):
        """Test that generated code includes correct dependency imports."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from code_generator import CodeGenerator
        
        generator = CodeGenerator(TechStack.REACT_SPA)
        
        story = UserStory(
            story_id="story-1",
            title="Login with Service",
            description="Login page using auth service",
            acceptance_criteria=["Uses AuthService for login"],
            priority=1,
            estimated_effort=5,
            dependencies=[],
            status=StoryStatus.PENDING
        )
        
        # Generate login page with AuthService dependency
        generated_code = generator.generate_component_code(
            login_component, story, [login_component, auth_service_component]
        )
        
        # Should import AuthService
        assert "import" in generated_code.content and "AuthService" in generated_code.content
        assert "../services/AuthService" in generated_code.content or "services/AuthService" in generated_code.content
        
        # Should use AuthService in component logic
        assert "AuthService.login" in generated_code.content or "authService.login" in generated_code.content

    def test_node_api_generation(self):
        """Test generation of Node.js API endpoints."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from code_generator import CodeGenerator
        
        api_component = ComponentSpec(
            component_id="comp_001",
            name="AuthController",
            type="controller",
            file_path="src/controllers/AuthController.ts",
            dependencies=["AuthService", "express"],
            exports=["AuthController"],
            story_ids=["story-1"]
        )
        
        api_story = UserStory(
            story_id="story-1", 
            title="Authentication API",
            description="As a developer, I want REST endpoints for user authentication",
            acceptance_criteria=[
                "POST /auth/login endpoint",
                "JWT token generation",
                "Password validation",
                "Error handling for invalid credentials"
            ],
            priority=1,
            estimated_effort=8,
            dependencies=[],
            status=StoryStatus.PENDING
        )
        
        generator = CodeGenerator(TechStack.NODE_API)
        
        generated_code = generator.generate_component_code(
            api_component, api_story, [api_component]
        )
        
        # Verify Express.js patterns
        assert "express" in generated_code.content
        assert "Router" in generated_code.content or "app." in generated_code.content
        assert "POST" in generated_code.content or "post" in generated_code.content
        assert "/auth/login" in generated_code.content
        
        # Verify JWT and authentication patterns
        assert "jwt" in generated_code.content.lower() or "token" in generated_code.content.lower()
        assert "password" in generated_code.content.lower()
        assert "req.body" in generated_code.content
        assert "res.json" in generated_code.content or "res.send" in generated_code.content

    def test_python_api_generation(self):
        """Test generation of Python FastAPI endpoints."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from code_generator import CodeGenerator
        
        python_component = ComponentSpec(
            component_id="comp_001",
            name="AuthRouter",
            type="router",
            file_path="app/routers/auth.py",
            dependencies=["FastAPI", "Pydantic"],
            exports=["router"],
            story_ids=["story-1"]
        )
        
        python_story = UserStory(
            story_id="story-1",
            title="Python Authentication API", 
            description="As a developer, I want FastAPI endpoints for authentication",
            acceptance_criteria=[
                "POST /auth/login endpoint",
                "Pydantic models for validation",
                "JWT token generation", 
                "Async endpoint handlers"
            ],
            priority=1,
            estimated_effort=8,
            dependencies=[],
            status=StoryStatus.PENDING
        )
        
        generator = CodeGenerator(TechStack.PYTHON_API)
        
        generated_code = generator.generate_component_code(
            python_component, python_story, [python_component]
        )
        
        # Verify FastAPI patterns
        assert "from fastapi import" in generated_code.content
        assert "APIRouter" in generated_code.content or "FastAPI" in generated_code.content
        assert "@router.post" in generated_code.content or "@app.post" in generated_code.content
        assert "/auth/login" in generated_code.content
        
        # Verify Python async patterns
        assert "async def" in generated_code.content
        assert "await" in generated_code.content
        
        # Verify Pydantic models
        assert "BaseModel" in generated_code.content or "pydantic" in generated_code.content
        assert "class" in generated_code.content

    def test_template_customization_by_tech_stack(self):
        """Test that templates are customized based on technology stack."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from code_generator import CodeGenerator
        
        component = ComponentSpec(
            component_id="comp_001",
            name="UserList",
            type="component",
            file_path="src/components/UserList.vue",  # Note: .vue extension
            dependencies=[],
            exports=["UserList"],
            story_ids=["story-1"]
        )
        
        story = UserStory(
            story_id="story-1",
            title="User List Display",
            description="Display list of users",
            acceptance_criteria=["Show user names and emails"],
            priority=1,
            estimated_effort=3,
            dependencies=[],
            status=StoryStatus.PENDING
        )
        
        # Test Vue.js generation
        vue_generator = CodeGenerator(TechStack.VUE_SPA)
        vue_code = vue_generator.generate_component_code(component, story, [component])
        
        # Should use Vue patterns
        assert "<template>" in vue_code.content
        assert "<script" in vue_code.content 
        assert "export default" in vue_code.content
        assert "defineComponent" in vue_code.content or "Vue.extend" in vue_code.content
        
        # Test React generation for comparison
        react_generator = CodeGenerator(TechStack.REACT_SPA)
        component.file_path = "src/components/UserList.tsx"  # Change to .tsx
        react_code = react_generator.generate_component_code(component, story, [component])
        
        # Should use React patterns
        assert "import React" in react_code.content
        assert "export const" in react_code.content or "export default" in react_code.content
        assert "React.FC" in react_code.content or ": FC" in react_code.content

    @patch('shared.services.anthropic_service.AnthropicService')
    def test_anthropic_enhanced_code_generation(self, mock_anthropic):
        """Test that complex components use Anthropic for intelligent code generation."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from code_generator import CodeGenerator
        
        # Mock Anthropic response
        service_mock = Mock()
        service_mock.generate_text = AsyncMock(return_value="""
        import React, { useState, useEffect } from 'react';
        import { User } from '../types/User';
        import { UserService } from '../services/UserService';
        
        export const UserDashboard: React.FC = () => {
            const [users, setUsers] = useState<User[]>([]);
            const [loading, setLoading] = useState(true);
            const [filter, setFilter] = useState('');
            
            useEffect(() => {
                const fetchUsers = async () => {
                    try {
                        const userData = await UserService.getUsers();
                        setUsers(userData);
                    } catch (error) {
                        console.error('Failed to fetch users:', error);
                    } finally {
                        setLoading(false);
                    }
                };
                
                fetchUsers();
            }, []);
            
            const filteredUsers = users.filter(user => 
                user.name.toLowerCase().includes(filter.toLowerCase())
            );
            
            return (
                <div className="user-dashboard">
                    <input 
                        type="text"
                        placeholder="Filter users..."
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                    />
                    {loading ? (
                        <div>Loading...</div>
                    ) : (
                        <div className="user-list">
                            {filteredUsers.map(user => (
                                <div key={user.id} className="user-card">
                                    <h3>{user.name}</h3>
                                    <p>{user.email}</p>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            );
        };
        """)
        mock_anthropic.return_value = service_mock
        
        complex_component = ComponentSpec(
            component_id="comp_001",
            name="UserDashboard",
            type="page",
            file_path="src/pages/UserDashboard.tsx",
            dependencies=["UserService"],
            exports=["UserDashboard"],
            story_ids=["story-1"]
        )
        
        complex_story = UserStory(
            story_id="story-1",
            title="Advanced User Dashboard",
            description="As an admin, I want a comprehensive dashboard to manage users with filtering and real-time updates",
            acceptance_criteria=[
                "Display all users in a responsive grid",
                "Filter users by name, email, or role",
                "Real-time updates when users are added/modified", 
                "Pagination for large user lists",
                "Sorting by multiple columns",
                "Export user data to CSV",
                "Bulk operations (activate/deactivate users)"
            ],
            priority=1,
            estimated_effort=21,  # High complexity should trigger Anthropic
            dependencies=[],
            status=StoryStatus.PENDING
        )
        
        generator = CodeGenerator(TechStack.REACT_SPA)
        
        generated_code = generator.generate_component_code(
            complex_component, complex_story, [complex_component]
        )
        
        # Verify Anthropic was used for complex generation
        service_mock.generate_text.assert_called_once()
        call_args = service_mock.generate_text.call_args[1]
        assert call_args["task_type"] == "code_generation"
        assert "UserDashboard" in call_args["prompt"]
        assert "React" in call_args["prompt"]
        
        # Verify advanced generated code features
        assert "useState" in generated_code.content
        assert "useEffect" in generated_code.content  
        assert "filter" in generated_code.content.lower()
        assert "loading" in generated_code.content.lower()
        assert "map" in generated_code.content  # Array mapping
        assert "async" in generated_code.content  # Async operations

    def test_code_generation_with_tests(self):
        """Test that generated code includes basic test structure."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from code_generator import CodeGenerator
        
        component = ComponentSpec(
            component_id="comp_001",
            name="Calculator",
            type="component",
            file_path="src/components/Calculator.tsx",
            dependencies=[],
            exports=["Calculator"],
            story_ids=["story-1"]
        )
        
        story = UserStory(
            story_id="story-1",
            title="Simple Calculator",
            description="As a user, I want a calculator for basic math operations",
            acceptance_criteria=[
                "Addition, subtraction, multiplication, division",
                "Clear button to reset",
                "Display current calculation"
            ],
            priority=1,
            estimated_effort=8,
            dependencies=[],
            status=StoryStatus.PENDING
        )
        
        generator = CodeGenerator(TechStack.REACT_SPA)
        
        # Generate component with tests
        result = generator.generate_component_with_tests(component, story, [component])
        
        # Should generate both component and test files
        assert len(result.files) >= 2
        
        component_file = next(f for f in result.files if f.file_path.endswith('.tsx'))
        test_file = next(f for f in result.files if f.file_path.endswith('.test.tsx'))
        
        # Verify component file
        assert "Calculator" in component_file.content
        assert "export" in component_file.content
        
        # Verify test file
        assert "import" in test_file.content
        assert "Calculator" in test_file.content
        assert "test(" in test_file.content or "it(" in test_file.content
        assert "render" in test_file.content
        assert "expect" in test_file.content

    def test_error_handling_in_code_generation(self):
        """Test that code generation handles errors gracefully."""
        import sys
        import os  
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))
        from code_generator import CodeGenerator, CodeGenerationError
        
        generator = CodeGenerator(TechStack.REACT_SPA)
        
        # Test with invalid component specification
        invalid_component = ComponentSpec(
            component_id="",  # Empty component ID
            name="",  # Empty name
            type="invalid_type",  # Invalid type
            file_path="",  # Empty file path
            dependencies=[],
            exports=[],
            story_ids=[]
        )
        
        invalid_story = UserStory(
            story_id="story-1",
            title="",  # Empty title
            description="",  # Empty description  
            acceptance_criteria=[],  # Empty criteria
            priority=0,  # Invalid priority
            estimated_effort=0,  # Zero effort
            dependencies=[],
            status=StoryStatus.PENDING
        )
        
        # Should raise appropriate error
        with pytest.raises(CodeGenerationError):
            generator.generate_component_code(invalid_component, invalid_story, [])
        
        # Test with unsupported tech stack
        with pytest.raises(ValueError):
            unsupported_generator = CodeGenerator("unsupported_stack")
            
    def test_incremental_code_updates(self):
        """Test that code generation can update existing components incrementally."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'story-executor'))  
        from code_generator import CodeGenerator
        
        generator = CodeGenerator(TechStack.REACT_SPA)
        
        # Initial component
        component = ComponentSpec(
            component_id="comp_001",
            name="LoginPage", 
            type="page",
            file_path="src/pages/LoginPage.tsx",
            dependencies=[],
            exports=["LoginPage"],
            story_ids=["story-1"]
        )
        
        # Initial story - basic login
        initial_story = UserStory(
            story_id="story-1",
            title="Basic Login",
            description="User can login with email/password",
            acceptance_criteria=["Login form", "Submit button"],
            priority=1,
            estimated_effort=5,
            dependencies=[],
            status=StoryStatus.PENDING
        )
        
        # Generate initial code
        initial_code = generator.generate_component_code(component, initial_story, [component])
        
        # Enhanced story - add remember me feature
        enhanced_story = UserStory(
            story_id="story-2", 
            title="Remember Me Login",
            description="User can choose to stay logged in",
            acceptance_criteria=[
                "Remember me checkbox",
                "Store login preference",
                "Auto-login on return visits"
            ],
            priority=1,
            estimated_effort=3,
            dependencies=["Basic Login"],
            status=StoryStatus.PENDING
        )
        
        # Generate incremental update
        updated_code = generator.update_component_code(
            component, enhanced_story, [component], existing_code=initial_code.content
        )
        
        # Should preserve existing functionality and add new features
        assert "email" in updated_code.content and "password" in updated_code.content  # Existing
        assert "remember" in updated_code.content.lower()  # New feature
        assert "checkbox" in updated_code.content.lower() or "input" in updated_code.content  # New UI
        
        # Should maintain code structure
        assert "export" in updated_code.content
        assert "LoginPage" in updated_code.content