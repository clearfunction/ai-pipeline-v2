"""Shared data models for the AI Pipeline Orchestrator v2."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Supported document types for intake."""
    PDF = "pdf"
    JSON_TRANSCRIPT = "json_transcript"
    EMAIL = "email"
    CHAT_LOG = "chat_log"
    CODE_REPO = "code_repo"
    TEXT = "text"


class StoryStatus(str, Enum):
    """Status of a user story in the pipeline."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    COMPLETED = "completed"
    FAILED = "failed"


class TechStack(str, Enum):
    """Supported technology stacks."""
    REACT_SPA = "react_spa"
    REACT_FULLSTACK = "react_fullstack"
    VUE_SPA = "vue_spa"
    ANGULAR_SPA = "angular_spa"
    NODE_API = "node_api"
    PYTHON_API = "python_api"
    NEXTJS = "nextjs"


class LLMProvider(str, Enum):
    """Available LLM providers."""
    BEDROCK = "bedrock"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class DocumentMetadata(BaseModel):
    """Metadata for processed documents."""
    document_id: str
    document_type: DocumentType
    source_path: str
    processed_at: datetime
    version_hash: str
    size_bytes: int
    lineage: List[str] = Field(default_factory=list)


class UserStory(BaseModel):
    """A single user story for development."""
    story_id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    priority: int
    estimated_effort: int  # Story points
    dependencies: List[str] = Field(default_factory=list)
    status: StoryStatus = StoryStatus.PENDING
    assigned_components: List[str] = Field(default_factory=list)


class ComponentSpec(BaseModel):
    """Specification for a code component."""
    component_id: str
    name: str
    type: str  # "component", "page", "service", "util", etc.
    file_path: str
    dependencies: List[str] = Field(default_factory=list)
    exports: List[str] = Field(default_factory=list)
    story_ids: List[str] = Field(default_factory=list)


class ProjectArchitecture(BaseModel):
    """Overall project architecture definition."""
    project_id: str
    name: str
    tech_stack: TechStack
    components: List[ComponentSpec]
    user_stories: List[UserStory]
    dependencies: Dict[str, str] = Field(default_factory=dict)
    build_config: Dict[str, Any] = Field(default_factory=dict)


class PipelineContext(BaseModel):
    """Context passed between pipeline stages."""
    execution_id: str
    project_id: str
    stage: str
    input_documents: List[DocumentMetadata]
    architecture: Optional[ProjectArchitecture] = None
    current_story: Optional[UserStory] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)




class ReviewRequest(BaseModel):
    """Request for human review."""
    review_id: str
    story_id: str
    pr_url: str
    components_changed: List[str]
    description: str
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GeneratedCode(BaseModel):
    """Represents generated code file."""
    file_path: str
    content: str
    component_id: str
    story_id: str
    file_type: str  # "component", "service", "test", "config", etc.
    language: str  # "typescript", "javascript", "python", etc.
    content_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LLMConfig(BaseModel):
    """Configuration for LLM providers."""
    primary_provider: LLMProvider
    fallback_providers: List[LLMProvider]
    model_configs: Dict[str, Dict[str, Any]]
    cost_optimization: bool = True
    max_retries: int = 3


class ValidationResult(BaseModel):
    """Result of a validation check."""
    validation_type: str
    passed: bool
    issues: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class GitHubWorkflowConfig(BaseModel):
    """Configuration for GitHub Actions workflows."""
    tech_stack: str
    workflow_name: str
    workflow_file: str
    template_path: str
    project_name: str
    triggers: List[str] = Field(default_factory=list)
    node_version: Optional[str] = None
    python_version: Optional[str] = None
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    secrets: List[str] = Field(default_factory=list)


class LambdaResponse(BaseModel):
    """Standard response format for all lambdas."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_context: Dict[str, Any] = Field(default_factory=dict)
    project_context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)