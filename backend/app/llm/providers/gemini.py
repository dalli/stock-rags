"""Google Gemini LLM provider implementation."""

import json
import re
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from app.config import get_settings
from app.llm.base import BaseEmbeddingProvider, BaseLLMProvider

settings = get_settings()


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any) -> None:
        """Initialize Gemini provider."""
        model_name = model_name or settings.default_gemini_model
        super().__init__(model_name, **kwargs)
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(self.model_name)

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "gemini"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """Generate text completion."""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        generation_config = {
            "temperature": temperature,
        }
        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens

        response = await self.model.generate_content_async(
            full_prompt, generation_config=generation_config
        )

        return response.text

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate structured output with retry logic for JSON parsing errors."""
        enhanced_prompt = f"{prompt}\n\nProvide output in the following JSON format:\n{json.dumps(schema, indent=2)}"

        if system_prompt:
            enhanced_prompt = f"{system_prompt}\n\nYou must respond with valid JSON only. Ensure all strings are properly escaped and the JSON is complete.\n\n{enhanced_prompt}"

        last_error = None
        for attempt in range(max_retries):
            try:
                response = await self.model.generate_content_async(enhanced_prompt)
                content = response.text
                
                # Remove markdown code blocks if present
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                
                content = content.strip()
                
                # Try to fix common JSON issues
                # Find the last complete JSON object/array
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    # Try to extract valid JSON from the content
                    if attempt < max_retries - 1:
                        # Try to find the last valid JSON structure
                        # Find the last closing brace or bracket
                        last_brace = content.rfind('}')
                        last_bracket = content.rfind(']')
                        last_valid = max(last_brace, last_bracket)
                        
                        if last_valid > 0:
                            # Try to find the matching opening
                            truncated = content[:last_valid + 1]
                            try:
                                return json.loads(truncated)
                            except json.JSONDecodeError:
                                pass
                        
                        # If still failing, try to fix common issues
                        # Remove trailing commas before closing braces/brackets
                        fixed = re.sub(r',(\s*[}\]])', r'\1', content)
                        try:
                            return json.loads(fixed)
                        except json.JSONDecodeError:
                            pass
                    
                    last_error = e
                    if attempt < max_retries - 1:
                        # Retry with a more explicit prompt
                        enhanced_prompt = f"{enhanced_prompt}\n\nIMPORTANT: Return ONLY valid, complete JSON. Do not truncate or leave strings unclosed."
                        continue
                    else:
                        raise
                        
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    continue
                else:
                    raise
        
        # If all retries failed, raise the last error
        if last_error:
            raise last_error
        
        raise ValueError("Failed to generate structured output after retries")

    async def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro",
        ]

    async def health_check(self) -> bool:
        """Check if provider is available."""
        try:
            response = await self.model.generate_content_async("Hi")
            return bool(response.text)
        except Exception:
            return False


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini embedding provider using embedding-001 model."""

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any) -> None:
        """Initialize Gemini embedding provider.

        Args:
            model_name: Embedding model name (defaults to embedding-001)
            **kwargs: Additional arguments
        """
        # Use embedding-001 model for embeddings
        model_name = model_name or "embedding-001"
        super().__init__(model_name, **kwargs)
        genai.configure(api_key=settings.google_api_key)
        self._dimension = 768  # embedding-001 produces 768-dimensional vectors

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "gemini"

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats
        """
        response = await genai.embed_content_async(
            model=f"models/{self.model_name}",
            content=text,
        )
        return response["embedding"]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            response = await genai.embed_content_async(
                model=f"models/{self.model_name}",
                content=text,
            )
            embeddings.append(response["embedding"])
        return embeddings

    async def get_available_models(self) -> List[str]:
        """Get list of available embedding models.

        Returns:
            List of model names
        """
        return [
            "embedding-001",
        ]

    async def health_check(self) -> bool:
        """Check if provider is available.

        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            response = await genai.embed_content_async(
                model="models/embedding-001",
                content="test",
            )
            return bool(response.get("embedding"))
        except Exception:
            return False
