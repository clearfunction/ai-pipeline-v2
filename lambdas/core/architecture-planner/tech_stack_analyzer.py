"""
Tech Stack Analyzer - Intelligent technology stack selection based on user stories.
Provides detailed analysis and recommendations for optimal tech stack choices.
"""

import json
from typing import Dict, Any, List
from shared.models.pipeline_models import UserStory, TechStack
from shared.services.anthropic_service import AnthropicService
from shared.utils.logger import get_logger

logger = get_logger()


class TechStackAnalyzer:
    """Analyzes user stories to recommend optimal technology stacks."""
    
    def __init__(self):
        """Initialize the tech stack analyzer.""" 
        self.anthropic_service = AnthropicService()
    
    def analyze_tech_stack(
        self, 
        user_stories: List[UserStory], 
        project_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze user stories and recommend optimal tech stack.
        
        Args:
            user_stories: List of user stories to analyze
            project_metadata: Additional project context
            
        Returns:
            Tech stack recommendation with reasoning
        """
        if project_metadata is None:
            project_metadata = {}
        
        # Calculate complexity metrics
        complexity_score = self._calculate_complexity_score(user_stories)
        story_patterns = self._analyze_story_patterns(user_stories)
        
        # Simple rule-based decisions for common patterns
        if complexity_score <= 10 and not story_patterns.get("has_dashboard", False):
            # Check for team preference on simple SPAs
            team_pref = project_metadata.get("team_preference", "").lower()
            if team_pref == "vue":
                return self._recommend_vue_spa(story_patterns)
            return self._recommend_simple_spa(story_patterns)
        
        elif story_patterns.get("api_only", False):
            if story_patterns.get("data_processing", False) or project_metadata.get("machine_learning", False):
                return self._recommend_python_api()
            else:
                return self._recommend_node_api()
        
        elif project_metadata.get("seo_important", False) or story_patterns.get("content_heavy", False):
            return self._recommend_nextjs(story_patterns)
        
        elif complexity_score > 30 or story_patterns.get("has_realtime", False):
            # Use Anthropic for complex decisions
            try:
                import asyncio
                return asyncio.run(self._get_anthropic_recommendation(user_stories, project_metadata))
            except Exception as e:
                logger.warning(f"Anthropic recommendation failed: {e}, using React fullstack fallback")
                return self._recommend_react_fullstack(story_patterns)
        
        else:
            # Check for team preference before defaulting to React fullstack
            team_pref = project_metadata.get("team_preference", "").lower()
            if team_pref == "vue" and complexity_score <= 15:  # Allow Vue for moderate complexity
                return self._recommend_vue_spa(story_patterns)
            return self._recommend_react_fullstack(story_patterns)
    
    def _calculate_complexity_score(self, user_stories: List[UserStory]) -> int:
        """Calculate overall complexity score from user stories."""
        total_effort = sum(story.estimated_effort for story in user_stories)
        story_count = len(user_stories)
        
        # Complexity factors
        complexity_score = total_effort
        
        # Additional complexity for dependencies
        total_dependencies = sum(len(story.dependencies) for story in user_stories)
        complexity_score += total_dependencies * 2
        
        # Complexity for high-effort individual stories
        high_effort_stories = [s for s in user_stories if s.estimated_effort > 13]
        complexity_score += len(high_effort_stories) * 5
        
        return complexity_score
    
    def _analyze_story_patterns(self, user_stories: List[UserStory]) -> Dict[str, bool]:
        """Analyze patterns in user stories to inform tech stack choice."""
        patterns = {
            "has_ui": False,
            "has_dashboard": False,
            "has_forms": False, 
            "has_auth": False,
            "has_realtime": False,
            "api_only": True,
            "data_processing": False,
            "content_heavy": False,
            "has_charts": False
        }
        
        all_text = " ".join([
            f"{story.title} {story.description} {' '.join(story.acceptance_criteria)}"
            for story in user_stories
        ]).lower()
        
        # UI indicators
        ui_keywords = ["page", "form", "button", "component", "interface", "dashboard", "view", "screen"]
        if any(keyword in all_text for keyword in ui_keywords):
            patterns["has_ui"] = True
            patterns["api_only"] = False
        
        # Dashboard indicators
        dashboard_keywords = ["dashboard", "analytics", "chart", "graph", "report", "widget"]
        if any(keyword in all_text for keyword in dashboard_keywords):
            patterns["has_dashboard"] = True
        
        # Form indicators
        form_keywords = ["form", "input", "register", "login", "create", "edit", "submit"]
        if any(keyword in all_text for keyword in form_keywords):
            patterns["has_forms"] = True
        
        # Authentication indicators
        auth_keywords = ["login", "register", "authentication", "auth", "user", "account", "password"]
        if any(keyword in all_text for keyword in auth_keywords):
            patterns["has_auth"] = True
        
        # Real-time indicators
        realtime_keywords = ["real-time", "live", "instant", "websocket", "notification", "chat", "collaboration"]
        if any(keyword in all_text for keyword in realtime_keywords):
            patterns["has_realtime"] = True
        
        # Data processing indicators
        data_keywords = ["data", "analytics", "processing", "pipeline", "batch", "ml", "machine learning"]
        if any(keyword in all_text for keyword in data_keywords):
            patterns["data_processing"] = True
        
        # Content heavy indicators
        content_keywords = ["blog", "cms", "content", "article", "seo", "marketing", "page"]
        if any(keyword in all_text for keyword in content_keywords):
            patterns["content_heavy"] = True
        
        # Charts/visualization indicators  
        chart_keywords = ["chart", "graph", "visualization", "plot", "analytics", "metrics"]
        if any(keyword in all_text for keyword in chart_keywords):
            patterns["has_charts"] = True
        
        return patterns
    
    def _recommend_simple_spa(self, patterns: Dict[str, bool]) -> Dict[str, Any]:
        """Recommend React SPA for simple applications."""
        return {
            "primary_stack": TechStack.REACT_SPA.value,
            "reasoning": "Simple CRUD application with basic UI requirements. React SPA provides sufficient functionality with minimal complexity.",
            "frontend": "React with TypeScript",
            "backend": "REST API (separate deployment)",
            "database": "PostgreSQL" if patterns.get("has_auth") else "MongoDB",
            "authentication": "JWT tokens" if patterns.get("has_auth") else "None required"
        }
    
    def _recommend_vue_spa(self, patterns: Dict[str, bool]) -> Dict[str, Any]:
        """Recommend Vue SPA for simple applications with Vue preference."""
        return {
            "primary_stack": TechStack.VUE_SPA.value,
            "reasoning": "Simple CRUD application with team preference for Vue. Vue SPA provides clean, reactive development experience.",
            "frontend": "Vue 3 with TypeScript",
            "backend": "REST API (separate deployment)",
            "database": "PostgreSQL" if patterns.get("has_auth") else "MongoDB",
            "authentication": "JWT tokens" if patterns.get("has_auth") else "None required",
            "routing": "Vue Router"
        }
    
    def _recommend_react_fullstack(self, patterns: Dict[str, bool]) -> Dict[str, Any]:
        """Recommend React Fullstack for balanced applications."""
        recommendation = {
            "primary_stack": TechStack.REACT_FULLSTACK.value,
            "reasoning": "Balanced application with frontend and backend requirements. React fullstack provides integrated development experience.",
            "frontend": "React with TypeScript",
            "backend": "Node.js with Express",
            "database": "PostgreSQL",
            "authentication": "JWT with bcrypt"
        }
        
        if patterns.get("has_realtime"):
            recommendation["real_time"] = "Socket.io"
            
        return recommendation
    
    def _recommend_node_api(self) -> Dict[str, Any]:
        """Recommend Node.js API for backend-only applications."""
        return {
            "primary_stack": TechStack.NODE_API.value,
            "reasoning": "API-focused application with no frontend requirements. Node.js provides fast development for REST APIs.",
            "frontend": "None",
            "backend": "Node.js with Express or Fastify",
            "database": "PostgreSQL",
            "additional_services": "Redis for caching, Queue system for background jobs"
        }
    
    def _recommend_python_api(self) -> Dict[str, Any]:
        """Recommend Python API for data-intensive applications."""
        return {
            "primary_stack": TechStack.PYTHON_API.value,
            "reasoning": "Data processing and machine learning requirements make Python the optimal choice with its rich ecosystem.",
            "frontend": "None",
            "backend": "FastAPI or Django REST Framework",
            "database": "PostgreSQL",
            "additional_libraries": "pandas, NumPy, scikit-learn for data processing"
        }
    
    def _recommend_nextjs(self, patterns: Dict[str, bool]) -> Dict[str, Any]:
        """Recommend Next.js for SEO-critical applications."""
        return {
            "primary_stack": TechStack.NEXTJS.value, 
            "reasoning": "SEO and content-heavy requirements need server-side rendering. Next.js provides optimal performance and SEO.",
            "frontend": "Next.js with TypeScript",
            "backend": "Next.js API routes",
            "database": "PostgreSQL",
            "rendering": "SSR and Static Generation",
            "deployment": "Vercel or self-hosted"
        }
    
    async def _get_anthropic_recommendation(
        self, 
        user_stories: List[UserStory], 
        project_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use Anthropic for complex tech stack decisions."""
        try:
            system_prompt = """You are a senior technical architect. Analyze the user stories and project requirements to recommend the optimal technology stack.
            
Consider:
1. Technical complexity and requirements
2. Development team capabilities
3. Scalability and performance needs
4. Time to market constraints
5. Long-term maintainability

Available stacks:
- react_spa: React SPA (frontend only)
- react_fullstack: React + Node.js fullstack
- vue_spa: Vue.js SPA  
- angular_spa: Angular SPA
- node_api: Node.js API only
- python_api: Python API (FastAPI/Django)
- nextjs: Next.js fullstack framework

Respond with JSON in this format:
{
  "recommendation": "react_fullstack",
  "reasoning": "Detailed explanation of why this stack is optimal"
}"""
            
            stories_text = "\n".join([
                f"Story: {story.title}\nDescription: {story.description}\nEffort: {story.estimated_effort} points"
                for story in user_stories
            ])
            
            metadata_text = "\n".join([
                f"{key}: {value}" for key, value in project_metadata.items()
            ])
            
            prompt = f"""Analyze these requirements and recommend the optimal tech stack:

USER STORIES:
{stories_text}

PROJECT METADATA:
{metadata_text}

Total estimated effort: {sum(s.estimated_effort for s in user_stories)} story points
Number of stories: {len(user_stories)}

Provide detailed technical recommendation with reasoning."""
            
            response = await self.anthropic_service.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                task_type="architecture_planning",
                max_tokens=1000,
                temperature=0.1,
                enable_cache=False  # Don't cache complex decisions
            )
            
            # Parse JSON response
            return json.loads(response)
            
        except Exception as e:
            logger.warning(f"Anthropic recommendation failed: {e}, using fallback")
            # Fallback to React Fullstack
            return self._recommend_react_fullstack({})
    
    def generate_build_config(self, tech_stack: TechStack) -> Dict[str, Any]:
        """Generate build configuration for the specified tech stack."""
        configs = {
            TechStack.REACT_SPA: {
                "package_manager": "npm",
                "bundler": "vite",
                "typescript": True,
                "linting": "eslint",
                "testing": "jest",
                "dev_tools": "vite-dev-server",
                "build_output": "dist/"
            },
            TechStack.REACT_FULLSTACK: {
                "package_manager": "npm", 
                "bundler": "vite",
                "monorepo": True,
                "workspaces": ["client", "server", "shared"],
                "typescript": True,
                "linting": "eslint",
                "testing": "vitest+jest",
                "dev_tools": "concurrently for frontend/backend",
                "build_output": "dist/"
            },
            TechStack.NODE_API: {
                "package_manager": "npm",
                "typescript": True,
                "linting": "eslint",
                "testing": "jest",
                "dev_tools": "nodemon",
                "build_output": "dist/"
            },
            TechStack.PYTHON_API: {
                "dependency_manager": "pip",
                "dependency_file": "requirements.txt",
                "linting": "flake8",
                "testing": "pytest",
                "dev_tools": "uvicorn reload",
                "build_output": "N/A"
            },
            TechStack.NEXTJS: {
                "package_manager": "npm",
                "framework": "Next.js",
                "typescript": True,
                "linting": "eslint",
                "testing": "jest",
                "ssr": True,
                "build_output": ".next/"
            },
            TechStack.VUE_SPA: {
                "package_manager": "npm",
                "bundler": "vite", 
                "typescript": True,
                "linting": "eslint",
                "testing": "vitest",
                "routing": "Vue Router",
                "build_output": "dist/"
            }
        }
        
        return configs.get(tech_stack, {})