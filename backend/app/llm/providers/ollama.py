"""Ollama LLM and Embedding provider implementation."""

import json
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings
from app.llm.base import BaseEmbeddingProvider, BaseLLMProvider

settings = get_settings()


class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider."""

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any) -> None:
        """Initialize Ollama provider."""
        model_name = model_name or settings.default_ollama_model
        super().__init__(model_name, **kwargs)
        self.base_url = settings.ollama_base_url

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "ollama"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """Generate text completion."""
        async with httpx.AsyncClient() as client:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                },
            }

            if system_prompt:
                payload["system"] = system_prompt

            if max_tokens:
                payload["options"]["num_predict"] = max_tokens

            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            return response.json()["response"]

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate structured output."""
        enhanced_prompt = f"{prompt}\n\nProvide output in the following JSON format:\n{json.dumps(schema, indent=2)}"

        enhanced_system = (
            f"{system_prompt or ''}\n\nYou must respond with valid JSON only. "
            "Do not include any explanatory text outside the JSON structure."
        )

        async with httpx.AsyncClient() as client:
            payload = {
                "model": self.model_name,
                "prompt": enhanced_prompt,
                "system": enhanced_system,
                "stream": False,
                "format": "json",
            }

            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            content = response.json()["response"]
            return json.loads(content)

    async def get_available_models(self) -> List[str]:
        """Get list of available models."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = response.json().get("models", [])
                return [model["name"] for model in models]
        except Exception:
            return []

    async def health_check(self) -> bool:
        """Check if provider is available."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Ollama embedding provider."""

    def __init__(self, model_name: str = "nomic-embed-text", **kwargs: Any) -> None:
        """Initialize Ollama embedding provider."""
        super().__init__(model_name, **kwargs)
        self.base_url = settings.ollama_base_url
        self._dimension = 768  # Default for nomic-embed-text

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "ollama"

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()["embedding"]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embedding = await self.embed_text(text)
            embeddings.append(embedding)
        return embeddings

    async def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return ["nomic-embed-text", "mxbai-embed-large"]

    async def health_check(self) -> bool:
        """Check if provider is available."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False
