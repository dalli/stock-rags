"""LLM and Embedding router for provider management."""

from typing import Any, Dict, List, Optional, Tuple

from app.llm.base import BaseEmbeddingProvider, BaseLLMProvider


class LLMRouter:
    """Router for managing multiple LLM providers."""

    def __init__(self) -> None:
        """Initialize LLM router."""
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.default_provider: Optional[str] = None

    def register_provider(self, name: str, provider: BaseLLMProvider) -> None:
        """Register an LLM provider.

        Args:
            name: Provider name (e.g., 'openai', 'anthropic')
            provider: Provider instance
        """
        self.providers[name] = provider
        if self.default_provider is None:
            self.default_provider = name

    def get_provider(
        self, name: Optional[str] = None, model: Optional[str] = None
    ) -> BaseLLMProvider:
        """Get LLM provider by name or model.

        Args:
            name: Provider name
            model: Model name (will search across providers)

        Returns:
            Provider instance

        Raises:
            ValueError: If provider not found
        """
        if name:
            if name not in self.providers:
                raise ValueError(f"Provider '{name}' not found")
            return self.providers[name]

        if model:
            # Search for provider that supports this model
            for provider in self.providers.values():
                # This is a simple check - in production you'd want to
                # maintain a model->provider mapping
                if model == provider.model_name:
                    return provider

        # Return default provider
        if self.default_provider and self.default_provider in self.providers:
            return self.providers[self.default_provider]

        raise ValueError("No provider available")

    async def list_all_models(self) -> Dict[str, List[str]]:
        """List all available models from all providers.

        Returns:
            Dictionary mapping provider names to model lists
        """
        models: Dict[str, List[str]] = {}
        for name, provider in self.providers.items():
            try:
                models[name] = await provider.get_available_models()
            except Exception:
                models[name] = []
        return models

    def set_default_provider(self, name: str) -> None:
        """Set default provider.

        Args:
            name: Provider name

        Raises:
            ValueError: If provider not found
        """
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' not found")
        self.default_provider = name

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all providers.

        Returns:
            Dictionary mapping provider names to health status
        """
        health: Dict[str, bool] = {}
        for name, provider in self.providers.items():
            try:
                health[name] = await provider.health_check()
            except Exception:
                health[name] = False
        return health

    def get_embedding_provider(
        self, name: Optional[str] = None, model: Optional[str] = None
    ) -> BaseEmbeddingProvider:
        """Get embedding provider from embedding router.

        Args:
            name: Provider name
            model: Model name

        Returns:
            Embedding provider instance
        """
        return embedding_router.get_provider(name, model)


class EmbeddingRouter:
    """Router for managing multiple embedding providers."""

    def __init__(self) -> None:
        """Initialize embedding router."""
        self.providers: Dict[str, BaseEmbeddingProvider] = {}
        self.default_provider: Optional[str] = None

    def register_provider(self, name: str, provider: BaseEmbeddingProvider) -> None:
        """Register an embedding provider.

        Args:
            name: Provider name (e.g., 'openai', 'ollama')
            provider: Provider instance
        """
        self.providers[name] = provider
        if self.default_provider is None:
            self.default_provider = name

    def get_provider(
        self, name: Optional[str] = None, model: Optional[str] = None
    ) -> BaseEmbeddingProvider:
        """Get embedding provider by name or model.

        Args:
            name: Provider name
            model: Model name

        Returns:
            Provider instance

        Raises:
            ValueError: If provider not found
        """
        if name:
            if name not in self.providers:
                raise ValueError(f"Provider '{name}' not found")
            return self.providers[name]

        if model:
            for provider in self.providers.values():
                if model == provider.model_name:
                    return provider

        if self.default_provider and self.default_provider in self.providers:
            return self.providers[self.default_provider]

        raise ValueError("No provider available")

    async def list_all_models(self) -> Dict[str, List[str]]:
        """List all available models from all providers.

        Returns:
            Dictionary mapping provider names to model lists
        """
        models: Dict[str, List[str]] = {}
        for name, provider in self.providers.items():
            try:
                models[name] = await provider.get_available_models()
            except Exception:
                models[name] = []
        return models

    def set_default_provider(self, name: str) -> None:
        """Set default provider.

        Args:
            name: Provider name

        Raises:
            ValueError: If provider not found
        """
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' not found")
        self.default_provider = name


# Global router instances
llm_router = LLMRouter()
embedding_router = EmbeddingRouter()


def get_llm_router() -> LLMRouter:
    """Get LLM router instance."""
    return llm_router


def get_embedding_router() -> EmbeddingRouter:
    """Get embedding router instance."""
    return embedding_router
