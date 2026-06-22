"""
Unified LLM Service - Provider-Agnostic

Abstracts LLM calls to work with ANY provider:
- OpenAI-compatible: OpenAI, Ollama, Groq, Together, Fireworks, etc.
- Native adapters: Anthropic
- Configurable at runtime via provider_config

All Agentco components use this service instead of hardcoding providers.
"""

import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.base_agent.provider_config import (
    resolve_tier_config,
    OPENAI_COMPATIBLE_PROVIDERS,
    NATIVE_ADAPTER_PROVIDERS,
    ConfigurationError,
)


class LLMService:
    """
    Provider-agnostic LLM service.

    Detects provider type and routes to appropriate client:
    - OpenAI SDK for OpenAI, Groq, Ollama, etc.
    - Anthropic SDK for Claude models

    Usage:
        service = LLMService(tier="standard")
        response = service.complete("Analyze this: ...", temperature=0.7)
    """

    def __init__(self, tier: str = "standard"):
        """Initialize LLM service for given tier."""
        self.tier = tier
        self.config = resolve_tier_config(tier)

        # Initialize appropriate client based on provider
        if self.config.provider in OPENAI_COMPATIBLE_PROVIDERS:
            self._init_openai_client()
        elif self.config.provider in NATIVE_ADAPTER_PROVIDERS:
            self._init_anthropic_client()
        else:
            raise ConfigurationError(
                f"Provider '{self.config.provider}' not supported. "
                f"Supported: {OPENAI_COMPATIBLE_PROVIDERS | NATIVE_ADAPTER_PROVIDERS}"
            )

    def _init_openai_client(self):
        """Initialize OpenAI-compatible client."""
        try:
            from openai import OpenAI
        except ImportError:
            raise ConfigurationError(
                "OpenAI SDK not installed. Install with: pip install openai"
            )

        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url if self.config.base_url else None,
        )
        self.provider_type = "openai_compatible"

    def _init_anthropic_client(self):
        """Initialize Anthropic client."""
        try:
            import anthropic
        except ImportError:
            raise ConfigurationError(
                "Anthropic SDK not installed. Install with: pip install anthropic"
            )

        self.client = anthropic.Anthropic(api_key=self.config.api_key)
        self.provider_type = "anthropic"

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        timeout: float = 30.0,
    ) -> str:
        """
        Get completion from LLM (provider-agnostic).

        Args:
            prompt: User prompt
            system: System message (optional)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum response tokens
            timeout: Request timeout in seconds

        Returns:
            Generated text from model
        """
        if self.provider_type == "openai_compatible":
            return self._complete_openai(
                prompt, system, temperature, max_tokens, timeout
            )
        elif self.provider_type == "anthropic":
            return self._complete_anthropic(
                prompt, system, temperature, max_tokens, timeout
            )

    def _complete_openai(
        self, prompt: str, system: Optional[str], temperature: float, max_tokens: int, timeout: float
    ) -> str:
        """Call OpenAI-compatible API."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

        return response.choices[0].message.content

    def _complete_anthropic(
        self, prompt: str, system: Optional[str], temperature: float, max_tokens: int, timeout: float
    ) -> str:
        """Call Anthropic API."""
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=max_tokens,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )

        return response.content[0].text

    def batch_complete(
        self,
        prompts: list[str],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> list[str]:
        """
        Get completions for multiple prompts.

        Args:
            prompts: List of user prompts
            system: System message (shared for all)
            temperature: Sampling temperature
            max_tokens: Maximum response tokens

        Returns:
            List of generated texts
        """
        results = []
        for prompt in prompts:
            try:
                result = self.complete(
                    prompt, system, temperature, max_tokens, timeout=30.0
                )
                results.append(result)
            except Exception as e:
                results.append(f"Error: {str(e)}")

        return results

    def get_provider_info(self) -> dict:
        """Get information about configured provider."""
        return {
            "tier": self.tier,
            "provider": self.config.provider,
            "model": self.config.model,
            "base_url": self.config.base_url,
            "provider_type": self.provider_type,
            "is_local": self.config.provider in ("ollama",),
        }


class LLMServiceFactory:
    """Factory for creating LLM services."""

    _instances = {}

    @staticmethod
    def get_service(tier: str = "standard") -> LLMService:
        """Get or create LLM service for tier (singleton per tier)."""
        if tier not in LLMServiceFactory._instances:
            LLMServiceFactory._instances[tier] = LLMService(tier)
        return LLMServiceFactory._instances[tier]

    @staticmethod
    def reset():
        """Reset all cached instances (useful for testing)."""
        LLMServiceFactory._instances.clear()


# Global convenience function
def get_llm(tier: str = "standard") -> LLMService:
    """Get LLM service for specified tier."""
    return LLMServiceFactory.get_service(tier)
