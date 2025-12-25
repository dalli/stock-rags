"""OpenAI LLM and Embedding provider implementation."""

import json
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.config import get_settings
from app.llm.base import BaseEmbeddingProvider, BaseLLMProvider

settings = get_settings()


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider."""

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any) -> None:
        """Initialize OpenAI provider."""
        model_name = model_name or settings.default_openai_model
        super().__init__(model_name, **kwargs)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "openai"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """Generate text completion."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        return response.choices[0].message.content or ""

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate structured output."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add schema to prompt
        enhanced_prompt = f"{prompt}\n\nProvide output in the following JSON format:\n{json.dumps(schema, indent=2)}"
        messages.append({"role": "user", "content": enhanced_prompt})

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            response_format={"type": "json_object"},
            **kwargs,
        )

        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    async def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]

    async def health_check(self) -> bool:
        """Check if provider is available."""
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider."""

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any) -> None:
        """Initialize OpenAI embedding provider."""
        model_name = model_name or settings.embedding_model
        super().__init__(model_name, **kwargs)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._dimension = settings.embedding_dimension

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "openai"

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        response = await self.client.embeddings.create(
            model=self.model_name,
            input=text,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        response = await self.client.embeddings.create(
            model=self.model_name,
            input=texts,
        )
        return [item.embedding for item in response.data]

    async def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return [
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002",
        ]

    async def health_check(self) -> bool:
        """Check if provider is available."""
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
