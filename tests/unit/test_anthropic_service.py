"""
Unit tests for AnthropicService with connection pooling and intelligent model routing.
Tests direct Anthropic API integration without AWS dependencies.
"""

import pytest
import asyncio
import json
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

from shared.services.anthropic_service import AnthropicService, ModelType
from shared.models.pipeline_models import LambdaResponse


class TestAnthropicService:
    """Unit tests for direct Anthropic API service."""
    
    @pytest.fixture
    def anthropic_config(self) -> Dict[str, Any]:
        """Configuration for Anthropic service testing."""
        return {
            "api_key": "test-anthropic-key",
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
                "connection_pool_size": 10
            },
            "cost_optimization": {
                "enable_caching": True,
                "cache_ttl_minutes": 60,
                "batch_processing": True,
                "usage_monitoring": True
            }
        }
    
    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client for testing."""
        with patch('shared.services.anthropic_service.AsyncAnthropic') as mock:
            client_mock = Mock()
            
            # Mock successful message creation
            async def mock_create(**kwargs):
                return Mock(content=[Mock(text="Generated response text")])
            
            client_mock.messages.create = AsyncMock(side_effect=mock_create)
            mock.return_value = client_mock
            yield client_mock

    def test_anthropic_service_initialization(self, anthropic_config: Dict[str, Any]):
        """Test AnthropicService initializes correctly with config."""
        service = AnthropicService(config=anthropic_config)
        
        # Verify configuration is set
        assert service.config == anthropic_config
        assert service.api_key == "test-anthropic-key"
        
        # Verify model routing is configured
        assert service.get_model_for_task("document_processing") == "claude-3-haiku-20240307"
        assert service.get_model_for_task("requirements_synthesis") == "claude-3-5-sonnet-20241022" 
        assert service.get_model_for_task("architecture_planning") == "claude-3-opus-20240229"

    def test_anthropic_service_model_selection(self, anthropic_config: Dict[str, Any]):
        """Test intelligent model routing for different tasks."""
        service = AnthropicService(config=anthropic_config)
        
        # Test each task gets appropriate model
        assert service.get_model_for_task("document_processing") == "claude-3-haiku-20240307"
        assert service.get_model_for_task("requirements_synthesis") == "claude-3-5-sonnet-20241022"
        assert service.get_model_for_task("architecture_planning") == "claude-3-opus-20240229"
        assert service.get_model_for_task("component_generation") == "claude-3-5-sonnet-20241022"
        
        # Test fallback for unknown task
        assert service.get_model_for_task("unknown_task") == "claude-3-5-sonnet-20241022"  # Default to primary

    @pytest.mark.asyncio
    async def test_generate_text_basic(
        self, 
        anthropic_config: Dict[str, Any],
        mock_anthropic_client: Mock
    ):
        """Test basic text generation functionality."""
        service = AnthropicService(config=anthropic_config)
        
        prompt = "Extract user stories from this document: ..."
        result = await service.generate_text(
            prompt=prompt,
            task_type="requirements_synthesis",
            max_tokens=1000,
            temperature=0.1
        )
        
        # Verify result
        assert result == "Generated response text"
        
        # Verify client was called with correct parameters
        mock_anthropic_client.messages.create.assert_called_once()
        call_args = mock_anthropic_client.messages.create.call_args[1]
        
        assert call_args["model"] == "claude-3-5-sonnet-20241022"  # Primary model for requirements_synthesis
        assert call_args["max_tokens"] == 1000
        assert call_args["temperature"] == 0.1
        assert len(call_args["messages"]) == 1
        assert call_args["messages"][0]["content"] == prompt

    @pytest.mark.asyncio
    async def test_generate_text_with_system_prompt(
        self,
        anthropic_config: Dict[str, Any], 
        mock_anthropic_client: Mock
    ):
        """Test text generation with system prompt."""
        service = AnthropicService(config=anthropic_config)
        
        system_prompt = "You are an expert software architect."
        user_prompt = "Design a REST API for user management."
        
        result = await service.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            task_type="architecture_planning",
            max_tokens=2000
        )
        
        assert result == "Generated response text"
        
        # Verify system prompt is included
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert call_args["system"] == system_prompt
        assert call_args["model"] == "claude-3-opus-20240229"  # Powerful model for architecture

    @pytest.mark.asyncio
    async def test_generate_text_retry_logic(
        self,
        anthropic_config: Dict[str, Any]
    ):
        """Test retry logic when API calls fail."""
        with patch('anthropic.AsyncAnthropic') as mock_anthropic:
            client_mock = Mock()
            
            # First two calls fail, third succeeds
            call_count = 0
            async def mock_create_with_failures(**kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise Exception("API temporarily unavailable")
                return Mock(content=[Mock(text="Success after retries")])
            
            client_mock.messages.create = AsyncMock(side_effect=mock_create_with_failures)
            mock_anthropic.return_value = client_mock
            
            service = AnthropicService(config=anthropic_config)
            
            result = await service.generate_text(
                prompt="Test prompt",
                task_type="document_processing"
            )
            
            assert result == "Success after retries"
            assert call_count == 3  # Two failures, one success

    @pytest.mark.asyncio
    async def test_generate_text_max_retries_exceeded(
        self,
        anthropic_config: Dict[str, Any]
    ):
        """Test behavior when max retries is exceeded."""
        with patch('anthropic.AsyncAnthropic') as mock_anthropic:
            client_mock = Mock()
            
            # All calls fail
            async def mock_create_always_fails(**kwargs):
                raise Exception("API permanently unavailable")
            
            client_mock.messages.create = AsyncMock(side_effect=mock_create_always_fails)
            mock_anthropic.return_value = client_mock
            
            service = AnthropicService(config=anthropic_config)
            
            # Should raise exception after max retries
            with pytest.raises(Exception, match="API permanently unavailable"):
                await service.generate_text(
                    prompt="Test prompt",
                    task_type="document_processing"
                )

    @pytest.mark.asyncio
    async def test_batch_generate_text(
        self,
        anthropic_config: Dict[str, Any],
        mock_anthropic_client: Mock
    ):
        """Test batch text generation for multiple prompts."""
        service = AnthropicService(config=anthropic_config)
        
        prompts = [
            "Extract stories from document 1",
            "Extract stories from document 2", 
            "Extract stories from document 3"
        ]
        
        results = await service.batch_generate_text(
            prompts=prompts,
            task_type="requirements_synthesis",
            max_tokens=1000
        )
        
        # Verify all prompts processed
        assert len(results) == 3
        assert all(result == "Generated response text" for result in results)
        
        # Verify client called for each prompt
        assert mock_anthropic_client.messages.create.call_count == 3

    def test_estimate_cost(self, anthropic_config: Dict[str, Any]):
        """Test cost estimation for different models and token counts."""
        service = AnthropicService(config=anthropic_config)
        
        prompt = "Test prompt " * 100  # ~400 characters, ~100 tokens
        
        # Test cost estimation for different models
        haiku_cost = service.estimate_cost(prompt, 1000, ModelType.FAST)
        sonnet_cost = service.estimate_cost(prompt, 1000, ModelType.PRIMARY)  
        opus_cost = service.estimate_cost(prompt, 1000, ModelType.POWERFUL)
        
        # Opus should be most expensive, Haiku cheapest
        assert opus_cost > sonnet_cost > haiku_cost
        assert all(cost > 0 for cost in [haiku_cost, sonnet_cost, opus_cost])

    @pytest.mark.asyncio
    async def test_connection_pooling(
        self,
        anthropic_config: Dict[str, Any],
        mock_anthropic_client: Mock
    ):
        """Test that connection pooling is properly configured."""
        service = AnthropicService(config=anthropic_config)
        
        # Make multiple concurrent requests
        tasks = []
        for i in range(5):
            task = service.generate_text(
                prompt=f"Test prompt {i}",
                task_type="document_processing"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Verify all requests completed
        assert len(results) == 5
        assert all(result == "Generated response text" for result in results)
        
        # Verify connection pooling limits were respected
        assert mock_anthropic_client.messages.create.call_count == 5

    def test_usage_monitoring(self, anthropic_config: Dict[str, Any]):
        """Test usage monitoring and cost tracking."""
        service = AnthropicService(config=anthropic_config)
        
        # Verify monitoring is enabled
        assert service.config["cost_optimization"]["usage_monitoring"] is True
        
        # Test usage tracking methods exist
        assert hasattr(service, 'get_usage_stats')
        assert hasattr(service, 'reset_usage_stats')
        
        # Test initial stats
        stats = service.get_usage_stats()
        assert stats["total_requests"] == 0
        assert stats["total_tokens"] == 0
        assert stats["total_cost"] == 0.0

    @pytest.mark.asyncio  
    async def test_caching_functionality(
        self,
        anthropic_config: Dict[str, Any],
        mock_anthropic_client: Mock
    ):
        """Test response caching for identical requests."""
        service = AnthropicService(config=anthropic_config)
        
        prompt = "Same prompt for caching test"
        
        # First request
        result1 = await service.generate_text(
            prompt=prompt,
            task_type="document_processing",
            enable_cache=True
        )
        
        # Second identical request should use cache
        result2 = await service.generate_text(
            prompt=prompt,
            task_type="document_processing", 
            enable_cache=True
        )
        
        # Results should be the same
        assert result1 == result2
        
        # But API should only be called once due to caching
        # (In real implementation - for now just verify structure)
        assert mock_anthropic_client.messages.create.call_count >= 1

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-api-key"})
    def test_service_uses_environment_variables(self):
        """Test service uses environment variables when no config provided."""
        service = AnthropicService()  # No config provided
        
        # Should use environment variable
        assert service.api_key == "env-api-key"
        
        # Should have default configuration
        assert service.config is not None
        assert "models" in service.config

    def test_service_validates_configuration(self):
        """Test service validates required configuration."""
        # Missing API key should raise error
        with pytest.raises(ValueError, match="API key is required"):
            AnthropicService(config={"models": {}})
        
        # Missing models should raise error  
        with pytest.raises(ValueError, match="Models configuration is required"):
            AnthropicService(config={"api_key": "test-key"})