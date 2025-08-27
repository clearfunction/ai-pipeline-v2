"""Shared LLM service with configurable providers."""

import os
import json
from typing import Dict, Any, List, Optional
from enum import Enum
import boto3
from botocore.exceptions import ClientError

from shared.models.pipeline_models import LLMProvider, LLMConfig
from shared.utils.logger import get_logger

logger = get_logger()


class LLMService:
    """Unified LLM service supporting multiple providers."""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize LLM service with configuration."""
        self.config = config or self._load_default_config()
        self._bedrock_client = None
        self._setup_clients()
    
    def _load_default_config(self) -> LLMConfig:
        """Load default LLM configuration from environment."""
        return LLMConfig(
            primary_provider=LLMProvider(
                os.environ.get("PRIMARY_LLM_PROVIDER", "bedrock")
            ),
            fallback_providers=[
                LLMProvider.OPENAI,
                LLMProvider.ANTHROPIC
            ],
            model_configs={
                "bedrock": {
                    "model_id": os.environ.get(
                        "BEDROCK_MODEL_ID", 
                        "anthropic.claude-3-sonnet-20240229-v1:0"
                    ),
                    "region": os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
                },
                "openai": {
                    "model": "gpt-4",
                    "api_key": os.environ.get("OPENAI_API_KEY")
                },
                "anthropic": {
                    "model": "claude-3-sonnet-20240229",
                    "api_key": os.environ.get("ANTHROPIC_API_KEY")
                }
            },
            cost_optimization=True,
            max_retries=3
        )
    
    def _setup_clients(self) -> None:
        """Initialize provider clients."""
        if LLMProvider.BEDROCK in [self.config.primary_provider] + self.config.fallback_providers:
            try:
                self._bedrock_client = boto3.client(
                    'bedrock-runtime',
                    region_name=self.config.model_configs["bedrock"]["region"]
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Bedrock client: {e}")
    
    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.1,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate text using the configured LLM provider.
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: Optional system prompt
            
        Returns:
            Generated text
        """
        providers_to_try = [self.config.primary_provider] + self.config.fallback_providers
        
        for provider in providers_to_try:
            try:
                if provider == LLMProvider.BEDROCK:
                    return await self._generate_bedrock(
                        prompt, max_tokens, temperature, system_prompt
                    )
                elif provider == LLMProvider.OPENAI:
                    return await self._generate_openai(
                        prompt, max_tokens, temperature, system_prompt
                    )
                elif provider == LLMProvider.ANTHROPIC:
                    return await self._generate_anthropic(
                        prompt, max_tokens, temperature, system_prompt
                    )
            except Exception as e:
                logger.warning(f"Provider {provider} failed: {e}")
                continue
        
        raise Exception("All LLM providers failed")
    
    async def _generate_bedrock(
        self, 
        prompt: str, 
        max_tokens: int, 
        temperature: float,
        system_prompt: Optional[str]
    ) -> str:
        """Generate text using AWS Bedrock."""
        if not self._bedrock_client:
            raise Exception("Bedrock client not initialized")
        
        # Format for Claude on Bedrock
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        try:
            response = self._bedrock_client.invoke_model(
                modelId=self.config.model_configs["bedrock"]["model_id"],
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            raise
    
    async def _generate_openai(
        self, 
        prompt: str, 
        max_tokens: int, 
        temperature: float,
        system_prompt: Optional[str]
    ) -> str:
        """Generate text using OpenAI API."""
        # Implementation would use openai library
        # Placeholder for now
        raise NotImplementedError("OpenAI provider not implemented yet")
    
    async def _generate_anthropic(
        self, 
        prompt: str, 
        max_tokens: int, 
        temperature: float,
        system_prompt: Optional[str]
    ) -> str:
        """Generate text using Anthropic API."""
        # Implementation would use anthropic library
        # Placeholder for now
        raise NotImplementedError("Anthropic provider not implemented yet")
    
    def estimate_cost(self, prompt: str, max_tokens: int) -> float:
        """
        Estimate cost for the request.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum output tokens
            
        Returns:
            Estimated cost in USD
        """
        if not self.config.cost_optimization:
            return 0.0
        
        # Rough token estimation (4 chars per token)
        input_tokens = len(prompt) // 4
        
        # Cost estimates per 1K tokens (approximate)
        costs = {
            LLMProvider.BEDROCK: {"input": 0.003, "output": 0.015},  # Claude-3 Sonnet
            LLMProvider.OPENAI: {"input": 0.01, "output": 0.03},     # GPT-4
            LLMProvider.ANTHROPIC: {"input": 0.003, "output": 0.015}  # Claude-3 Sonnet
        }
        
        provider_costs = costs.get(self.config.primary_provider, costs[LLMProvider.BEDROCK])
        
        input_cost = (input_tokens / 1000) * provider_costs["input"]
        output_cost = (max_tokens / 1000) * provider_costs["output"]
        
        return input_cost + output_cost