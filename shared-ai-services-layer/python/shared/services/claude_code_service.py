"""
Claude Code SDK service for AI-powered code generation.
Lightweight implementation without pydantic dependencies.
"""

import os
import re
import logging
import json
import boto3
from typing import Dict, Any, List, Optional
import anyio
from claude_code_sdk import query, ClaudeCodeOptions, AssistantMessage, TextBlock

logger = logging.getLogger(__name__)


class ClaudeCodeService:
    """Service wrapper for Claude Code SDK for dynamic code generation."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude Code service.
        
        Args:
            api_key: Optional API key, defaults to environment variable or Secrets Manager
        """
        self.api_key = api_key or self._get_api_key()
        if not self.api_key:
            raise ValueError("Unable to retrieve Anthropic API key from environment or Secrets Manager")
        
        # Set the API key in environment for SDK to use
        os.environ['ANTHROPIC_API_KEY'] = self.api_key
        
        logger.info("Claude Code Service initialized")
    
    def _get_api_key(self) -> Optional[str]:
        """
        Get Anthropic API key from environment variable or AWS Secrets Manager.
        
        Returns:
            API key string or None if not found
        """
        # First try direct environment variable
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if api_key:
            return api_key
        
        # Then try to get from Secrets Manager
        secret_arn = os.environ.get('ANTHROPIC_API_KEY_SECRET_ARN')
        if not secret_arn:
            logger.warning("Neither ANTHROPIC_API_KEY nor ANTHROPIC_API_KEY_SECRET_ARN found in environment")
            return None
        
        try:
            secrets_client = boto3.client('secretsmanager')
            response = secrets_client.get_secret_value(SecretId=secret_arn)
            
            secret_value = response['SecretString']
            if secret_value.startswith('{'):
                # JSON format
                secret_data = json.loads(secret_value)
                # Try different key names that might be used
                return secret_data.get('apiKey') or secret_data.get('api_key') or secret_data.get('ANTHROPIC_API_KEY')
            else:
                # Plain text format
                return secret_value
        
        except Exception as e:
            logger.error(f"Failed to retrieve API key from Secrets Manager: {e}")
            return None
    
    async def generate_story_code(
        self,
        story: Dict[str, Any],
        architecture: Dict[str, Any],
        existing_files: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate code for a user story using Claude Code SDK.
        
        Args:
            story: User story with title, description, and acceptance criteria
            architecture: Project architecture with tech_stack and configuration
            existing_files: List of existing files in the project
            
        Returns:
            List of generated files with path and content
        """
        tech_stack = architecture.get('tech_stack', 'react_fullstack')
        
        # Build context from existing files (limit to prevent context overflow)
        file_tree = self._build_file_tree(existing_files[:50])
        
        # Create the prompt
        prompt = self._create_generation_prompt(story, tech_stack, file_tree)
        
        # Configure Claude Code options
        options = ClaudeCodeOptions(
            system_prompt=self._get_system_prompt(tech_stack),
            max_turns=1,  # Single response for efficiency
            temperature=0.2  # Low temperature for consistent code
        )
        
        logger.info(f"Generating code for story: {story.get('title', 'Unknown')}")
        
        try:
            # Collect the complete response
            full_response = await self._collect_response(prompt, options)
            
            # Parse generated files from response
            generated_files = self._parse_generated_files(full_response, story)
            
            logger.info(f"Generated {len(generated_files)} files for story")
            return generated_files
            
        except Exception as e:
            logger.error(f"Failed to generate code: {e}")
            raise
    
    def _build_file_tree(self, existing_files: List[Dict[str, Any]]) -> str:
        """Build a file tree representation from existing files."""
        if not existing_files:
            return "Empty project"
        
        paths = []
        for file_info in existing_files:
            if isinstance(file_info, dict):
                path = file_info.get('path', file_info.get('file_path', ''))
                if path:
                    paths.append(f"- {path}")
        
        return "\n".join(paths) if paths else "Empty project"
    
    def _create_generation_prompt(
        self,
        story: Dict[str, Any],
        tech_stack: str,
        file_tree: str
    ) -> str:
        """Create the prompt for code generation."""
        # Extract story details
        title = story.get('title', 'Implementation Task')
        description = story.get('description', '')
        acceptance_criteria = story.get('acceptance_criteria', [])
        
        # Format acceptance criteria
        criteria_text = "\n".join([f"- {ac}" for ac in acceptance_criteria])
        
        return f"""I'm working on a {tech_stack} project.

Current project structure:
{file_tree}

Please implement this user story:
Title: {title}
Description: {description}
Acceptance Criteria:
{criteria_text}

Generate the necessary files to fully implement this story. Include:
1. React/Vue components with proper TypeScript types
2. Routing configuration (update or create route files)
3. API endpoints if backend functionality is needed
4. Database models/schemas if data persistence is required
5. Basic tests for critical functionality
6. Any configuration or utility files needed

Format each file as:
```filepath: path/to/file.ext
file content here
```

Make sure the code is production-ready with proper error handling, loading states, and follows best practices for {tech_stack}."""
    
    def _get_system_prompt(self, tech_stack: str) -> str:
        """Get system prompt based on tech stack."""
        base_prompt = "You are an expert full-stack developer. Generate clean, maintainable, production-ready code."
        
        stack_prompts = {
            'react_spa': "Focus on React with TypeScript, React Router v6, and modern hooks patterns.",
            'react_fullstack': "Use React with TypeScript for frontend, Express.js for backend, and proper API integration.",
            'vue_spa': "Use Vue 3 with Composition API, TypeScript, and Vue Router 4.",
            'vue_fullstack': "Use Vue 3 for frontend and Express.js for backend with TypeScript throughout.",
            'node_api': "Focus on Node.js with Express or Fastify, proper middleware, and RESTful design.",
            'python_api': "Use FastAPI or Flask with proper type hints and async support where appropriate."
        }
        
        specific_prompt = stack_prompts.get(tech_stack, "")
        return f"{base_prompt} {specific_prompt}".strip()
    
    async def _collect_response(self, prompt: str, options: ClaudeCodeOptions) -> str:
        """Collect the complete response from Claude Code SDK."""
        full_response = ""
        
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                # Extract text content from message
                for block in message.content:
                    if isinstance(block, TextBlock):
                        full_response += block.text
        
        return full_response
    
    def _parse_generated_files(self, response: str, story: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse generated code from Claude's response into file objects.
        
        Args:
            response: The complete response text from Claude
            story: The user story being implemented
            
        Returns:
            List of file dictionaries with path and content
        """
        files = []
        
        # Pattern to match code blocks with filepath markers
        pattern = r'```filepath:\s*([^\n]+)\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for filepath, content in matches:
            filepath = filepath.strip()
            content = content.strip()
            
            # Skip empty files
            if not content:
                continue
            
            files.append({
                'file_path': filepath,
                'content': content,
                'story_id': story.get('story_id', 'unknown'),
                'generated_by': 'claude_code_sdk'
            })
            
            logger.debug(f"Parsed file: {filepath} ({len(content)} chars)")
        
        return files


def create_sync_wrapper(claude_service: ClaudeCodeService):
    """
    Create a synchronous wrapper for the async Claude Code service.
    This is needed for Lambda handlers that aren't async.
    
    Args:
        claude_service: Instance of ClaudeCodeService
        
    Returns:
        Function that can be called synchronously
    """
    def sync_generate_story_code(
        story: Dict[str, Any],
        architecture: Dict[str, Any],
        existing_files: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for generate_story_code."""
        return anyio.run(
            claude_service.generate_story_code,
            story,
            architecture,
            existing_files
        )
    
    return sync_generate_story_code