"""
Abstract base class for template generators.
Defines the common interface and shared functionality.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GeneratedCode:
    """Represents a generated code file."""
    
    def __init__(self, file_path: str, content: str, component_id: str, story_id: str, 
                 file_type: str, language: str):
        self.file_path = file_path
        self.content = content
        self.component_id = component_id
        self.story_id = story_id
        self.file_type = file_type
        self.language = language
        self.content_hash = hash(content)
        self.size_bytes = len(content.encode('utf-8'))
        self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'file_path': self.file_path,
            'content': self.content,
            'component_id': self.component_id,
            'story_id': self.story_id,
            'file_type': self.file_type,
            'language': self.language,
            'content_hash': self.content_hash,
            'size_bytes': self.size_bytes,
            'created_at': self.created_at
        }


class BaseTemplateGenerator(ABC):
    """Abstract base class for template generators."""
    
    def __init__(self, tech_stack: str):
        self.tech_stack = tech_stack
        self.logger = logger
    
    @abstractmethod
    def generate_project_scaffold(self, project_name: str, architecture: Any) -> List[GeneratedCode]:
        """Generate complete project scaffold for the tech stack."""
        pass
    
    @abstractmethod
    def get_supported_runtime(self) -> str:
        """Return the runtime this generator supports (node, python, etc.)."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return human-readable description of this template generator."""
        pass
    
    def _sanitize_project_name(self, project_name: str) -> str:
        """Sanitize project name to be filesystem and URL safe."""
        import re
        # Remove special characters, convert to lowercase
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '-', project_name)
        sanitized = sanitized.lower().strip('-')
        
        # Ensure it starts with a letter or number
        if sanitized and not sanitized[0].isalnum():
            sanitized = 'project-' + sanitized
        
        return sanitized or 'generated-project'
    
    def _create_generated_code(self, file_path: str, content: str, component_id: str = "project_scaffold", 
                             story_id: str = "scaffold", file_type: str = "file") -> GeneratedCode:
        """Helper method to create GeneratedCode objects."""
        # Determine language from file extension
        language = self._get_language_from_path(file_path)
        
        return GeneratedCode(
            file_path=file_path,
            content=content,
            component_id=component_id,
            story_id=story_id,
            file_type=file_type,
            language=language
        )
    
    def _get_language_from_path(self, file_path: str) -> str:
        """Determine programming language from file path."""
        extension = file_path.split('.')[-1].lower()
        
        language_map = {
            'ts': 'typescript',
            'tsx': 'typescript',
            'js': 'javascript',
            'jsx': 'javascript',
            'vue': 'vue',
            'py': 'python',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'yml': 'yaml',
            'yaml': 'yaml',
            'md': 'markdown',
            'txt': 'text'
        }
        
        return language_map.get(extension, 'text')