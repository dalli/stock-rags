"""LM Studio LLM provider implementation (OpenAI-compatible API)."""

from typing import Any, Optional

from openai import AsyncOpenAI

from app.config import get_settings
from app.llm.providers.openai import OpenAIProvider

settings = get_settings()


class LMStudioProvider(OpenAIProvider):
    """LM Studio LLM provider (OpenAI-compatible)."""

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any) -> None:
        """Initialize LM Studio provider."""
        model_name = model_name or settings.default_lmstudio_model
        super().__init__(model_name, **kwargs)
        self.client = AsyncOpenAI(
            api_key="not-needed",
            base_url=settings.lmstudio_base_url,
        )

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "lmstudio"
