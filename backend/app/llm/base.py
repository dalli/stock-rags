"""Base LLM provider abstraction."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model_name: str, **kwargs: Any) -> None:
        """Initialize provider.

        Args:
            model_name: Name of the model to use
            **kwargs: Additional provider-specific arguments
        """
        self.model_name = model_name
        self.kwargs = kwargs

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get provider name."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """Generate text completion.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific arguments

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate structured output matching schema.

        Args:
            prompt: User prompt
            schema: JSON schema for output validation
            system_prompt: Optional system prompt
            **kwargs: Additional provider-specific arguments

        Returns:
            Structured output as dictionary
        """
        pass

    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """Get list of available models.

        Returns:
            List of model names
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available and working.

        Returns:
            True if healthy, False otherwise
        """
        pass


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    def __init__(self, model_name: str, **kwargs: Any) -> None:
        """Initialize embedding provider.

        Args:
            model_name: Name of the embedding model
            **kwargs: Additional provider-specific arguments
        """
        self.model_name = model_name
        self.kwargs = kwargs

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get provider name."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Get embedding dimension."""
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text.

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        pass

    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """Get list of available models.

        Returns:
            List of model names
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available and working.

        Returns:
            True if healthy, False otherwise
        """
        pass
