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

IMPORTANT: Use this EXACT format for each file (no variations):

FILE: path/to/file.ext
TYPE: component|service|config|test|route|model|style|util
LANGUAGE: typescript|javascript|python|vue|css|json|yaml|html
---
[complete file content goes here]
---
END_FILE

Examples:
FILE: src/components/UserLogin.tsx
TYPE: component
LANGUAGE: typescript
---
import React, {{ useState }} from 'react';

export const UserLogin: React.FC = () => {{
  const [email, setEmail] = useState('');
  // ... component implementation
  return <div>Login component</div>;
}};
---
END_FILE

FILE: src/services/AuthService.ts
TYPE: service
LANGUAGE: typescript
---
export class AuthService {{
  async login(email: string, password: string) {{
    // ... service implementation
  }}
}}
---
END_FILE

Make sure the code is production-ready with proper error handling, loading states, and follows best practices for {tech_stack}.

CRITICAL: Each file MUST start with "FILE:" and end with "END_FILE" for proper parsing."""
    
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
        Enhanced with multiple parsing strategies and better error handling.
        
        Args:
            response: The complete response text from Claude
            story: The user story being implemented
            
        Returns:
            List of file dictionaries with path and content
        """
        files = []
        
        # Strategy 1: Try new structured format first
        structured_files = self._parse_structured_format(response, story)
        if structured_files:
            files.extend(structured_files)
            logger.info(f"Successfully parsed {len(structured_files)} files using structured format")
        
        # Strategy 2: Fallback to enhanced filepath format
        if not files:
            filepath_files = self._parse_filepath_format(response, story)
            if filepath_files:
                files.extend(filepath_files)
                logger.info(f"Successfully parsed {len(filepath_files)} files using enhanced filepath format")
        
        # Strategy 3: Fallback to original format
        if not files:
            original_files = self._parse_original_format(response, story)
            if original_files:
                files.extend(original_files)
                logger.info(f"Successfully parsed {len(original_files)} files using original format")
        
        # Strategy 4: Last resort - try to extract any code blocks
        if not files:
            code_block_files = self._parse_generic_code_blocks(response, story)
            if code_block_files:
                files.extend(code_block_files)
                logger.warning(f"Fallback parsing extracted {len(code_block_files)} generic code blocks")
        
        if not files:
            logger.error(f"Failed to parse any files from response. Response length: {len(response)} chars")
            logger.debug(f"Response preview: {response[:500]}...")
        
        return files
    
    def _parse_structured_format(self, response: str, story: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse the new structured format with FILE:/TYPE:/LANGUAGE: headers."""
        files = []
        
        # Pattern to match structured format: FILE: ... TYPE: ... LANGUAGE: ... --- content --- END_FILE
        pattern = r'FILE:\s*([^\n]+)\s*\nTYPE:\s*([^\n]+)\s*\nLANGUAGE:\s*([^\n]+)\s*\n---\s*\n(.*?)\n---\s*\nEND_FILE'
        matches = re.findall(pattern, response, re.DOTALL | re.MULTILINE)
        
        for filepath, file_type, language, content in matches:
            filepath = filepath.strip()
            file_type = file_type.strip()
            language = language.strip()
            content = content.strip()
            
            # Skip empty files
            if not content:
                logger.warning(f"Skipping empty file: {filepath}")
                continue
            
            files.append({
                'file_path': filepath,
                'content': content,
                'file_type': file_type,
                'language': language,
                'story_id': story.get('story_id', 'unknown'),
                'generated_by': 'claude_code_sdk_structured'
            })
            
            logger.debug(f"Parsed structured file: {filepath} (type: {file_type}, lang: {language}, {len(content)} chars)")
        
        return files
    
    def _parse_filepath_format(self, response: str, story: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse enhanced filepath format with better error handling."""
        files = []
        
        # Multiple patterns for filepath format variations
        patterns = [
            r'```filepath:\s*([^\n]+)\n(.*?)```',  # Original format
            r'```file:\s*([^\n]+)\n(.*?)```',      # Alternative file: header
            r'```path:\s*([^\n]+)\n(.*?)```',      # Alternative path: header
            r'```([^\n]+\.(?:tsx?|jsx?|vue|py|css|json|ya?ml|html?))\n(.*?)```'  # Extension-based detection
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for filepath, content in matches:
                filepath = filepath.strip()
                content = content.strip()
                
                # Skip empty files
                if not content:
                    continue
                
                # Infer file type and language from path
                file_type, language = self._infer_file_metadata(filepath)
                
                files.append({
                    'file_path': filepath,
                    'content': content,
                    'file_type': file_type,
                    'language': language,
                    'story_id': story.get('story_id', 'unknown'),
                    'generated_by': 'claude_code_sdk_filepath'
                })
                
                logger.debug(f"Parsed filepath file: {filepath} ({len(content)} chars)")
            
            # If we found files with this pattern, don't try other patterns
            if files:
                break
        
        return files
    
    def _parse_original_format(self, response: str, story: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse original simple format for backward compatibility."""
        files = []
        
        # Original pattern
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
                'generated_by': 'claude_code_sdk_original'
            })
            
            logger.debug(f"Parsed original format file: {filepath} ({len(content)} chars)")
        
        return files
    
    def _parse_generic_code_blocks(self, response: str, story: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Last resort: try to parse any code blocks and infer file paths."""
        files = []
        
        # Find all code blocks with language hints
        pattern = r'```(\w+)\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for i, (language_hint, content) in enumerate(matches):
            content = content.strip()
            if not content or len(content) < 50:  # Skip very short blocks
                continue
            
            # Try to infer filename from content or use generic name
            filename = self._infer_filename_from_content(content, language_hint, i)
            file_type, language = self._infer_file_metadata(filename)
            
            files.append({
                'file_path': filename,
                'content': content,
                'file_type': file_type,
                'language': language,
                'story_id': story.get('story_id', 'unknown'),
                'generated_by': 'claude_code_sdk_generic'
            })
            
            logger.warning(f"Generic parsing created file: {filename} ({len(content)} chars)")
        
        return files
    
    def _infer_file_metadata(self, filepath: str) -> tuple[str, str]:
        """Infer file type and language from file path."""
        path_lower = filepath.lower()
        
        # Determine file type
        if 'test' in path_lower or 'spec' in path_lower:
            file_type = 'test'
        elif 'component' in path_lower or filepath.endswith(('.tsx', '.jsx', '.vue')):
            file_type = 'component'
        elif 'service' in path_lower or 'api' in path_lower:
            file_type = 'service'
        elif 'route' in path_lower or 'router' in path_lower:
            file_type = 'route'
        elif 'model' in path_lower or 'schema' in path_lower:
            file_type = 'model'
        elif 'config' in path_lower or filepath.endswith(('.json', '.yaml', '.yml', '.toml')):
            file_type = 'config'
        elif filepath.endswith(('.css', '.scss', '.sass', '.less')):
            file_type = 'style'
        elif 'util' in path_lower or 'helper' in path_lower:
            file_type = 'util'
        else:
            file_type = 'source'
        
        # Determine language
        ext = filepath.split('.')[-1].lower() if '.' in filepath else ''
        language_map = {
            'ts': 'typescript', 'tsx': 'typescript',
            'js': 'javascript', 'jsx': 'javascript',
            'py': 'python', 'vue': 'vue',
            'css': 'css', 'scss': 'scss', 'sass': 'sass', 'less': 'less',
            'json': 'json', 'yaml': 'yaml', 'yml': 'yaml',
            'html': 'html', 'md': 'markdown'
        }
        language = language_map.get(ext, 'text')
        
        return file_type, language
    
    def _infer_filename_from_content(self, content: str, language_hint: str, index: int) -> str:
        """Try to infer filename from content or create a reasonable default."""
        # Look for common patterns that suggest filenames
        import_patterns = [
            r'export\s+(?:default\s+)?(?:class|function|const)\s+(\w+)',
            r'class\s+(\w+)',
            r'function\s+(\w+)',
            r'const\s+(\w+)\s*=',
            r'interface\s+(\w+)',
            r'type\s+(\w+)\s*='
        ]
        
        for pattern in import_patterns:
            match = re.search(pattern, content)
            if match:
                name = match.group(1)
                ext = self._get_extension_for_language(language_hint)
                return f"src/generated/{name}{ext}"
        
        # Fallback to generic names
        ext = self._get_extension_for_language(language_hint)
        return f"src/generated/generated_file_{index}{ext}"
    
    def _get_extension_for_language(self, language_hint: str) -> str:
        """Get file extension for language hint."""
        extension_map = {
            'typescript': '.ts',
            'javascript': '.js',
            'python': '.py',
            'vue': '.vue',
            'css': '.css',
            'json': '.json',
            'yaml': '.yml',
            'html': '.html'
        }
        return extension_map.get(language_hint.lower(), '.txt')


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