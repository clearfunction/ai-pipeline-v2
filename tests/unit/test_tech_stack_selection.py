"""
Unit tests for intelligent tech stack selection logic.
Tests the decision-making process for choosing optimal technology stacks.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, patch

from shared.models.pipeline_models import UserStory, StoryStatus, TechStack
from shared.services.anthropic_service import AnthropicService


class TestTechStackSelection:
    """Unit tests for tech stack selection logic."""
    
    @pytest.fixture
    def simple_crud_stories(self) -> List[UserStory]:
        """Simple CRUD application stories."""
        return [
            UserStory(
                story_id="story-1",
                title="User Registration",
                description="As a user, I want to register with email/password",
                acceptance_criteria=["User can create account", "Email validation"],
                priority=1,
                estimated_effort=3,
                dependencies=[],
                status=StoryStatus.PENDING
            ),
            UserStory(
                story_id="story-2", 
                title="View User List",
                description="As an admin, I want to view all users",
                acceptance_criteria=["Display user table", "Pagination support"],
                priority=2,
                estimated_effort=5,
                dependencies=["User Registration"],
                status=StoryStatus.PENDING
            )
        ]
    
    @pytest.fixture
    def complex_dashboard_stories(self) -> List[UserStory]:
        """Complex dashboard application stories.""" 
        return [
            UserStory(
                story_id="story-1",
                title="User Authentication",
                description="As a user, I want secure login with 2FA",
                acceptance_criteria=["Login form", "2FA integration", "Session management"],
                priority=1,
                estimated_effort=8,
                dependencies=[],
                status=StoryStatus.PENDING
            ),
            UserStory(
                story_id="story-2",
                title="Interactive Dashboard",
                description="As a user, I want a dynamic dashboard with real-time data",
                acceptance_criteria=["Live data updates", "Interactive charts", "Drag-and-drop widgets"],
                priority=1,
                estimated_effort=13,
                dependencies=["User Authentication"], 
                status=StoryStatus.PENDING
            ),
            UserStory(
                story_id="story-3",
                title="Data Analytics",
                description="As a user, I want to analyze my data with custom queries",
                acceptance_criteria=["Query builder", "Custom reports", "Data export"],
                priority=2,
                estimated_effort=21,
                dependencies=["Interactive Dashboard"],
                status=StoryStatus.PENDING
            )
        ]
    
    @pytest.fixture
    def api_only_stories(self) -> List[UserStory]:
        """API-only service stories."""
        return [
            UserStory(
                story_id="story-1",
                title="REST API Endpoints", 
                description="As a developer, I want REST API for user management",
                acceptance_criteria=["CRUD endpoints", "Authentication middleware", "Rate limiting"],
                priority=1,
                estimated_effort=8,
                dependencies=[],
                status=StoryStatus.PENDING
            ),
            UserStory(
                story_id="story-2",
                title="Background Task Service",
                description="As a system, I want to handle background tasks efficiently",
                acceptance_criteria=["Job scheduling", "Queue management", "Error handling"],
                priority=1, 
                estimated_effort=13,
                dependencies=[],
                status=StoryStatus.PENDING
            )
        ]

    def test_react_spa_selection_for_simple_ui(self, simple_crud_stories: List[UserStory]):
        """Test that React SPA is selected for simple UI applications."""
        # Import the tech stack analyzer
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from tech_stack_analyzer import TechStackAnalyzer
        
        analyzer = TechStackAnalyzer()
        
        # Analyze stories
        recommendation = analyzer.analyze_tech_stack(
            user_stories=simple_crud_stories,
            project_metadata={
                "project_type": "web_application",
                "complexity": "low",
                "user_count": "small"
            }
        )
        
        # Should recommend React SPA for simple CRUD
        assert recommendation["primary_stack"] == TechStack.REACT_SPA.value
        assert "simple" in recommendation["reasoning"].lower()
        assert "crud" in recommendation["reasoning"].lower()
        
        # Verify stack components
        assert recommendation["frontend"] == "React with TypeScript"
        assert "API" in recommendation["backend"]
        assert recommendation["database"] in ["PostgreSQL", "MongoDB"]

    def test_react_fullstack_selection_for_complex_dashboard(self, complex_dashboard_stories: List[UserStory]):
        """Test that React Fullstack is selected for complex dashboard applications."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from tech_stack_analyzer import TechStackAnalyzer
        
        analyzer = TechStackAnalyzer()
        
        recommendation = analyzer.analyze_tech_stack(
            user_stories=complex_dashboard_stories,
            project_metadata={
                "project_type": "web_application", 
                "complexity": "high",
                "real_time": True,
                "analytics": True
            }
        )
        
        # Should recommend React Fullstack for complex interactive features
        assert recommendation["primary_stack"] == TechStack.REACT_FULLSTACK.value
        assert "complex" in recommendation["reasoning"].lower() or "fullstack" in recommendation["reasoning"].lower()
        
        # Verify advanced stack components
        assert "Next.js" in recommendation["frontend"] or "React" in recommendation["frontend"]
        assert "Node.js" in recommendation["backend"]
        assert recommendation["database"] == "PostgreSQL"  # More robust for analytics
        assert "WebSocket" in recommendation.get("real_time", "") or "Socket.io" in recommendation.get("real_time", "")

    def test_node_api_selection_for_backend_only(self, api_only_stories: List[UserStory]):
        """Test that Node API is selected for backend-only applications."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from tech_stack_analyzer import TechStackAnalyzer
        
        analyzer = TechStackAnalyzer()
        
        recommendation = analyzer.analyze_tech_stack(
            user_stories=api_only_stories,
            project_metadata={
                "project_type": "api_service",
                "complexity": "medium", 
                "frontend": False
            }
        )
        
        # Should recommend Node API for backend-only services
        assert recommendation["primary_stack"] == TechStack.NODE_API.value
        assert "api" in recommendation["reasoning"].lower()
        
        # Verify API-focused stack
        assert recommendation["frontend"] == "None" or "frontend" not in recommendation
        assert "Express" in recommendation["backend"] or "Fastify" in recommendation["backend"]
        assert "Queue" in recommendation.get("additional_services", "") or "Redis" in recommendation.get("additional_services", "")

    def test_python_api_selection_for_data_processing(self):
        """Test that Python API is selected for data-intensive applications."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from tech_stack_analyzer import TechStackAnalyzer
        
        data_stories = [
            UserStory(
                story_id="story-1",
                title="Machine Learning Pipeline",
                description="As a data scientist, I want to train ML models on large datasets",
                acceptance_criteria=["Data preprocessing", "Model training", "Prediction API"],
                priority=1,
                estimated_effort=21,
                dependencies=[],
                status=StoryStatus.PENDING
            ),
            UserStory(
                story_id="story-2", 
                title="Data Analytics API",
                description="As a developer, I want APIs for statistical analysis",
                acceptance_criteria=["Statistical functions", "Data aggregation", "Report generation"],
                priority=2,
                estimated_effort=13,
                dependencies=["Machine Learning Pipeline"],
                status=StoryStatus.PENDING
            )
        ]
        
        analyzer = TechStackAnalyzer()
        
        recommendation = analyzer.analyze_tech_stack(
            user_stories=data_stories,
            project_metadata={
                "project_type": "data_service",
                "complexity": "high",
                "machine_learning": True,
                "data_processing": True
            }
        )
        
        # Should recommend Python API for data/ML workloads
        assert recommendation["primary_stack"] == TechStack.PYTHON_API.value
        assert any(keyword in recommendation["reasoning"].lower() 
                  for keyword in ["data", "ml", "machine learning", "analytics"])
        
        # Verify Python-specific stack
        assert "FastAPI" in recommendation["backend"] or "Django" in recommendation["backend"]
        assert "pandas" in recommendation.get("additional_libraries", "") or "NumPy" in recommendation.get("additional_libraries", "")

    def test_nextjs_selection_for_seo_requirements(self):
        """Test that Next.js is selected when SEO is important."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from tech_stack_analyzer import TechStackAnalyzer
        
        seo_stories = [
            UserStory(
                story_id="story-1",
                title="Public Marketing Pages",
                description="As a visitor, I want fast-loading marketing pages that rank well in search",
                acceptance_criteria=["SEO optimization", "Server-side rendering", "Fast page load"],
                priority=1,
                estimated_effort=8,
                dependencies=[],
                status=StoryStatus.PENDING
            ),
            UserStory(
                story_id="story-2",
                title="Blog Platform", 
                description="As a content creator, I want to publish blog posts with SEO",
                acceptance_criteria=["Content management", "SEO meta tags", "Social sharing"],
                priority=2,
                estimated_effort=13,
                dependencies=["Public Marketing Pages"],
                status=StoryStatus.PENDING
            )
        ]
        
        analyzer = TechStackAnalyzer()
        
        recommendation = analyzer.analyze_tech_stack(
            user_stories=seo_stories,
            project_metadata={
                "project_type": "web_application",
                "seo_important": True,
                "public_facing": True,
                "content_heavy": True
            }
        )
        
        # Should recommend Next.js for SEO requirements
        assert recommendation["primary_stack"] == TechStack.NEXTJS.value
        assert any(keyword in recommendation["reasoning"].lower() 
                  for keyword in ["seo", "server-side", "ssr", "performance"])
        
        # Verify Next.js specific features
        assert "Next.js" in recommendation["frontend"]
        assert "SSR" in recommendation.get("rendering", "") or "Static Generation" in recommendation.get("rendering", "")

    def test_vue_spa_selection_alternative(self):
        """Test that Vue SPA can be selected as alternative to React."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from tech_stack_analyzer import TechStackAnalyzer
        
        vue_preference_stories = [
            UserStory(
                story_id="story-1",
                title="Admin Dashboard",
                description="As an admin, I want a clean dashboard with form-heavy interfaces",
                acceptance_criteria=["Form validation", "Data tables", "Simple routing"],
                priority=1,
                estimated_effort=8,
                dependencies=[],
                status=StoryStatus.PENDING
            )
        ]
        
        analyzer = TechStackAnalyzer()
        
        recommendation = analyzer.analyze_tech_stack(
            user_stories=vue_preference_stories,
            project_metadata={
                "project_type": "admin_panel",
                "complexity": "medium",
                "team_preference": "vue"  # Team prefers Vue
            }
        )
        
        # Should respect team preference for Vue when appropriate
        assert recommendation["primary_stack"] in [TechStack.VUE_SPA.value, TechStack.REACT_SPA.value]
        
        # If Vue is selected, verify Vue-specific components
        if recommendation["primary_stack"] == TechStack.VUE_SPA.value:
            assert "Vue" in recommendation["frontend"]
            assert "Vue Router" in recommendation.get("routing", "")

    def test_stack_selection_considers_story_complexity(self):
        """Test that tech stack selection considers total story complexity."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from tech_stack_analyzer import TechStackAnalyzer
        
        # Low complexity stories
        simple_stories = [
            UserStory(
                story_id="story-1",
                title="Simple Form",
                description="Basic contact form",
                acceptance_criteria=["Form submission"],
                priority=1,
                estimated_effort=2,
                dependencies=[],
                status=StoryStatus.PENDING
            )
        ]
        
        # High complexity stories 
        complex_stories = [
            UserStory(
                story_id="story-1",
                title="Enterprise Dashboard",
                description="Multi-tenant analytics dashboard with real-time collaboration",
                acceptance_criteria=["Real-time updates", "Multi-user editing", "Advanced permissions"],
                priority=1,
                estimated_effort=34,
                dependencies=[],
                status=StoryStatus.PENDING
            )
        ]
        
        analyzer = TechStackAnalyzer()
        
        simple_rec = analyzer.analyze_tech_stack(simple_stories, {"project_type": "web_application"})
        complex_rec = analyzer.analyze_tech_stack(complex_stories, {"project_type": "web_application"})
        
        # Simple stories should get simpler stack
        assert simple_rec["primary_stack"] in [TechStack.REACT_SPA.value, TechStack.VUE_SPA.value]
        
        # Complex stories should get more robust stack
        assert complex_rec["primary_stack"] in [TechStack.REACT_FULLSTACK.value, TechStack.NEXTJS.value]

    def test_build_configuration_matches_tech_stack(self):
        """Test that build configuration is generated correctly for each tech stack."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from tech_stack_analyzer import TechStackAnalyzer
        
        analyzer = TechStackAnalyzer()
        
        # Test different stacks
        stacks_to_test = [
            (TechStack.REACT_SPA, "React SPA build config"),
            (TechStack.REACT_FULLSTACK, "React Fullstack build config"), 
            (TechStack.NODE_API, "Node API build config"),
            (TechStack.PYTHON_API, "Python API build config"),
            (TechStack.NEXTJS, "Next.js build config")
        ]
        
        for stack, description in stacks_to_test:
            build_config = analyzer.generate_build_config(stack)
            
            # Verify common fields exist
            assert "package_manager" in build_config or "dependency_manager" in build_config
            assert "linting" in build_config
            assert "testing" in build_config
            
            # Verify stack-specific configurations
            if stack == TechStack.REACT_SPA:
                assert build_config["package_manager"] == "npm"
                assert build_config["bundler"] in ["webpack", "vite"]
                assert build_config["typescript"] is True
            
            elif stack == TechStack.NODE_API:
                assert build_config["package_manager"] == "npm"
                assert "nodemon" in build_config.get("dev_tools", "")
                assert build_config["testing"] == "jest"
            
            elif stack == TechStack.PYTHON_API:
                assert build_config["dependency_manager"] == "pip"
                assert "requirements.txt" in build_config.get("dependency_file", "")
                assert build_config["testing"] in ["pytest", "unittest"]
            
            elif stack == TechStack.NEXTJS:
                assert "next" in build_config.get("framework", "").lower()
                assert build_config.get("ssr", True) is True

    def test_anthropic_integration_for_complex_decisions(self):
        """Test that complex tech stack decisions use Anthropic for analysis."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'lambdas', 'core', 'architecture-planner'))
        from tech_stack_analyzer import TechStackAnalyzer
        from unittest.mock import AsyncMock, patch
        
        # Create analyzer with mocked service
        with patch('tech_stack_analyzer.AnthropicService') as mock_anthropic_cls:
            service_mock = Mock()
            service_mock.generate_text = AsyncMock(return_value='{"primary_stack": "react_fullstack", "reasoning": "Complex requirements need full-stack solution"}')
            mock_anthropic_cls.return_value = service_mock
            
            analyzer = TechStackAnalyzer()
        
            complex_mixed_stories = [
                UserStory(
                    story_id="story-1",
                    title="Hybrid Mobile/Web App",
                    description="Cross-platform app with offline sync and real-time collaboration",
                    acceptance_criteria=["Offline mode", "Real-time sync", "Mobile responsive"],
                    priority=1,
                    estimated_effort=55,  # Very complex
                    dependencies=[],
                    status=StoryStatus.PENDING
                )
            ]
            
            recommendation = analyzer.analyze_tech_stack(
                complex_mixed_stories,
                {"project_type": "hybrid_application", "platforms": ["web", "mobile"]}
            )
            
            # Verify Anthropic was called for complex decision
            service_mock.generate_text.assert_called_once()
            call_args = service_mock.generate_text.call_args[1]
            assert call_args["task_type"] == "architecture_planning"
            assert "tech stack" in call_args["prompt"].lower()
            
            # Verify recommendation was processed
            assert recommendation["primary_stack"] == "react_fullstack"
            assert "complex" in recommendation["reasoning"].lower()