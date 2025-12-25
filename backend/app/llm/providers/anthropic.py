"""Anthropic LLM provider implementation."""

import json
from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic

from app.config import get_settings
from app.llm.base import BaseLLMProvider

settings = get_settings()


class AnthropicProvider(BaseLLMProvider):
    """Anthropic LLM provider."""

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any) -> None:
        """Initialize Anthropic provider."""
        model_name = model_name or settings.default_anthropic_model
        super().__init__(model_name, **kwargs)
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "anthropic"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """Generate text completion."""
        max_tokens = max_tokens or 4096

        response = await self.client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )

        return response.content[0].text

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate structured output."""
        # Add schema to prompt
        enhanced_prompt = f"{prompt}\n\nProvide output in the following JSON format:\n{json.dumps(schema, indent=2)}"

        enhanced_system = (
            f"{system_prompt or ''}\n\nYou must respond with valid JSON only. "
            "Do not include any explanatory text outside the JSON structure."
        )

        response = await self.client.messages.create(
            model=self.model_name,
            max_tokens=4096,
            system=enhanced_system,
            messages=[{"role": "user", "content": enhanced_prompt}],
            **kwargs,
        )

        content = response.content[0].text
        return json.loads(content)

    async def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ]

    async def health_check(self) -> bool:
        """Check if provider is available."""
        try:
            # Simple test message
            await self.client.messages.create(
                model=self.model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except Exception:
            return False
