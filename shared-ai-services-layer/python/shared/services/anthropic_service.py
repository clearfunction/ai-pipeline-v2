"""
Direct Anthropic API service with connection pooling and intelligent model routing.
Replaces multi-provider LLM service with Anthropic-only implementation.
"""

import os
import json
import asyncio
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import anthropic
from anthropic import AsyncAnthropic

from shared.utils.logger import get_logger

logger = get_logger()


class ModelType(str, Enum):
    """Model types for different use cases."""
    FAST = "fast"           # Claude 3 Haiku - Quick processing
    PRIMARY = "primary"     # Claude 3.5 Sonnet - Balanced performance
    POWERFUL = "powerful"   # Claude 3 Opus - Complex reasoning


class AnthropicService:
    """Direct Anthropic API service with intelligent routing and optimization."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Anthropic service.
        
        Args:
            config: Service configuration, uses environment defaults if None
        """
        self.config = config or self._load_default_config()
        self.api_key = self._get_api_key()
        
        # Validate configuration
        self._validate_config()
        
        # Initialize client and connection pool
        self.client = AsyncAnthropic(
            api_key=self.api_key,
            timeout=self.config["connection_config"]["timeout"]
        )
        
        # Usage tracking
        self.usage_stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "requests_by_model": {},
            "start_time": datetime.utcnow()
        }
        
        # Simple in-memory cache for development
        self._cache = {}
        
        logger.info("AnthropicService initialized with intelligent model routing")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration from environment and PLAN.md specifications."""
        return {
            "models": {
                "fast": "claude-3-haiku-20240307",
                "primary": "claude-3-5-sonnet-20241022", 
                "powerful": "claude-3-opus-20240229"
            },
            "intelligent_routing": {
                "document_processing": "fast",
                "requirements_synthesis": "primary",
                "architecture_planning": "powerful", 
                "component_generation": "primary",
                "code_review": "primary"
            },
            "connection_config": {
                "timeout": 120,
                "max_retries": 3,
                "retry_delay": [1, 2, 4],
                "connection_pool_size": 50
            },
            "cost_optimization": {
                "enable_caching": True,
                "cache_ttl_minutes": 60,
                "batch_processing": True,
                "usage_monitoring": True
            }
        }
    
    def _get_api_key(self) -> str:
        """Get API key from config or environment."""
        api_key = self.config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API key is required")
        return api_key
    
    def _validate_config(self) -> None:
        """Validate required configuration."""
        if not self.config.get("models"):
            raise ValueError("Models configuration is required")
        
        required_models = ["fast", "primary", "powerful"]
        for model_type in required_models:
            if model_type not in self.config["models"]:
                raise ValueError(f"Model configuration missing for: {model_type}")
    
    def get_model_for_task(self, task_type: str) -> str:
        """
        Get optimal model for specific task type.
        
        Args:
            task_type: Type of task (document_processing, requirements_synthesis, etc.)
            
        Returns:
            Model identifier for the task
        """
        routing = self.config.get("intelligent_routing", {})
        model_type = routing.get(task_type, "primary")  # Default to primary
        
        models = self.config["models"]
        return models.get(model_type, models["primary"])
    
    async def generate_text(
        self,
        prompt: str,
        task_type: str = "general",
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.1,
        enable_cache: bool = True
    ) -> str:
        """
        Generate text using Anthropic API with intelligent model routing.
        
        Args:
            prompt: User prompt
            task_type: Type of task for model selection
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            enable_cache: Whether to use response caching
            
        Returns:
            Generated text response
        """
        # Check cache first
        if enable_cache and self.config["cost_optimization"]["enable_caching"]:
            cache_key = self._get_cache_key(prompt, task_type, system_prompt, max_tokens, temperature)
            if cache_key in self._cache:
                cached_response, timestamp = self._cache[cache_key]
                if self._is_cache_valid(timestamp):
                    logger.debug(f"Cache hit for task_type: {task_type}")
                    return cached_response
        
        # Select appropriate model
        model = self.get_model_for_task(task_type)
        
        # Prepare request
        messages = [{"role": "user", "content": prompt}]
        request_params = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system_prompt:
            request_params["system"] = system_prompt
        
        # Execute with retry logic
        response = await self._execute_with_retry(request_params)
        
        # Extract text from response
        text = response.content[0].text
        
        # Update usage stats
        self._update_usage_stats(task_type, model, len(prompt), len(text))
        
        # Cache response
        if enable_cache and self.config["cost_optimization"]["enable_caching"]:
            self._cache[cache_key] = (text, datetime.utcnow())
        
        return text
    
    async def batch_generate_text(
        self,
        prompts: List[str],
        task_type: str = "general",
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.1
    ) -> List[str]:
        """
        Generate text for multiple prompts in batch.
        
        Args:
            prompts: List of prompts to process
            task_type: Type of task for model selection
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens per generation
            temperature: Sampling temperature
            
        Returns:
            List of generated text responses
        """
        tasks = []
        for prompt in prompts:
            task = self.generate_text(
                prompt=prompt,
                task_type=task_type,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            tasks.append(task)
        
        return await asyncio.gather(*tasks)
    
    async def _execute_with_retry(self, request_params: Dict[str, Any]) -> Any:
        """
        Execute API request with retry logic.
        
        Args:
            request_params: Parameters for the API request
            
        Returns:
            API response
        """
        max_retries = self.config["connection_config"]["max_retries"]
        retry_delays = self.config["connection_config"]["retry_delay"]
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                response = await self.client.messages.create(**request_params)
                return response
            except Exception as e:
                last_exception = e
                
                if attempt < max_retries:
                    delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                    logger.warning(f"API call failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"API call failed after {max_retries + 1} attempts: {e}")
        
        raise last_exception
    
    def estimate_cost(
        self, 
        prompt: str, 
        max_tokens: int, 
        model_type: ModelType = ModelType.PRIMARY
    ) -> float:
        """
        Estimate cost for a request.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum output tokens
            model_type: Model type to use
            
        Returns:
            Estimated cost in USD
        """
        # Rough token estimation (4 characters per token)
        input_tokens = len(prompt) / 4
        
        # Cost per 1K tokens (as of December 2024)
        model_costs = {
            ModelType.FAST: {"input": 0.00025, "output": 0.00125},      # Haiku
            ModelType.PRIMARY: {"input": 0.003, "output": 0.015},       # Sonnet 3.5
            ModelType.POWERFUL: {"input": 0.015, "output": 0.075}       # Opus
        }
        
        costs = model_costs.get(model_type, model_costs[ModelType.PRIMARY])
        
        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (max_tokens / 1000) * costs["output"]
        
        return input_cost + output_cost
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        return self.usage_stats.copy()
    
    def reset_usage_stats(self) -> None:
        """Reset usage statistics."""
        self.usage_stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "requests_by_model": {},
            "start_time": datetime.utcnow()
        }
    
    def _get_cache_key(
        self, 
        prompt: str, 
        task_type: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Generate cache key for request."""
        cache_data = {
            "prompt": prompt,
            "task_type": task_type,
            "system_prompt": system_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cached response is still valid."""
        ttl_minutes = self.config["cost_optimization"]["cache_ttl_minutes"]
        expiry = timestamp + timedelta(minutes=ttl_minutes)
        return datetime.utcnow() < expiry
    
    def _update_usage_stats(
        self, 
        task_type: str, 
        model: str, 
        input_length: int, 
        output_length: int
    ) -> None:
        """Update usage statistics."""
        self.usage_stats["total_requests"] += 1
        
        # Rough token estimation
        input_tokens = input_length / 4
        output_tokens = output_length / 4
        total_tokens = input_tokens + output_tokens
        
        self.usage_stats["total_tokens"] += total_tokens
        
        # Estimate cost based on model
        if "haiku" in model.lower():
            model_type = ModelType.FAST
        elif "opus" in model.lower():
            model_type = ModelType.POWERFUL
        else:
            model_type = ModelType.PRIMARY
        
        cost = self.estimate_cost("", int(output_tokens), model_type)
        self.usage_stats["total_cost"] += cost
        
        # Track by model
        if model not in self.usage_stats["requests_by_model"]:
            self.usage_stats["requests_by_model"][model] = 0
        self.usage_stats["requests_by_model"][model] += 1