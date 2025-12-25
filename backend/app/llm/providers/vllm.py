"""vLLM provider implementation (OpenAI-compatible API)."""

from typing import Any, Optional

from openai import AsyncOpenAI

from app.config import get_settings
from app.llm.providers.openai import OpenAIProvider

settings = get_settings()


class VLLMProvider(OpenAIProvider):
    """vLLM provider (OpenAI-compatible)."""

    def __init__(self, model_name: str = "local-model", **kwargs: Any) -> None:
        """Initialize vLLM provider."""
        super().__init__(model_name, **kwargs)
        self.client = AsyncOpenAI(
            api_key="not-needed",
            base_url=settings.vllm_base_url,
        )

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "vllm"
