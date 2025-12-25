"""
Vector Storage Service for Embeddings

Handles document chunking, embedding generation, and vector storage.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from app.db.qdrant import QdrantClient, get_qdrant
from app.llm.router import get_embedding_router
from app.parsers.pdf_parser import PDFDocument

logger = logging.getLogger(__name__)


class VectorService:
    """
    Service for vector embedding and storage operations.

    Handles chunking text, generating embeddings, and storing
    in Qdrant vector database for semantic search.
    """

    def __init__(
        self,
        qdrant_client: Optional[QdrantClient] = None,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> None:
        self.qdrant_client = qdrant_client
        self.embedding_router = get_embedding_router()
        self.chunk_size = chunk_size
        self.overlap = overlap

    async def _get_client(self) -> QdrantClient:
        """Get Qdrant client, initializing if needed"""
        if self.qdrant_client is None:
            self.qdrant_client = await get_qdrant()
        return self.qdrant_client

    async def generate_embedding(
        self, text: str, provider: Optional[str] = None, model: Optional[str] = None
    ) -> list[float]:
        """
        Generate embedding vector for text.

        Args:
            text: Text to embed
            provider: Embedding provider (None = default)
            model: Embedding model (None = default)

        Returns:
            Embedding vector as list of floats
        """
        # Get embedding provider
        embedding_provider = self.embedding_router.get_provider(provider, model)

        # Generate embedding
        vector = await embedding_provider.embed_text(text)
        return vector

    async def generate_embeddings_batch(
        self, texts: list[str], provider: Optional[str] = None, model: Optional[str] = None
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed
            provider: Embedding provider
            model: Embedding model

        Returns:
            List of embedding vectors
        """
        embedding_provider = self.embedding_router.get_provider(provider, model)
        vectors = await embedding_provider.embed_batch(texts)
        return vectors

    async def store_document(
        self,
        report_id: UUID,
        pdf_document: PDFDocument,
        company_ticker: Optional[str] = None,
        report_type: str = "stock_analysis",
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> int:
        """
        Process PDF document and store embeddings.

        Args:
            report_id: Report UUID
            pdf_document: Parsed PDF document
            company_ticker: Primary company ticker
            report_type: Type of report
            provider: Embedding provider
            model: Embedding model

        Returns:
            Number of chunks stored
        """
        try:
            client = await self._get_client()

            # Chunk the full text
            from app.parsers.pdf_parser import pdf_parser

            chunks = pdf_parser.chunk_text(
                pdf_document.full_text, self.chunk_size, self.overlap
            )

            if not chunks:
                logger.warning(f"No chunks extracted from report {report_id}")
                return 0

            # Extract texts for embedding
            texts = [chunk["text"] for chunk in chunks]

            logger.info(
                f"Generating embeddings for {len(chunks)} chunks from report {report_id}"
            )

            # Generate embeddings in batch
            vectors = await self.generate_embeddings_batch(texts, provider, model)

            # Prepare payloads with metadata
            payloads = []
            for i, chunk in enumerate(chunks):
                payload = {
                    "report_id": str(report_id),
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "page_number": self._estimate_page_number(
                        chunk["start_char"], pdf_document
                    ),
                    "report_type": report_type,
                }

                if company_ticker:
                    payload["company_ticker"] = company_ticker

                payloads.append(payload)

            # Store in Qdrant
            await client.insert_vectors(vectors=vectors, payloads=payloads)

            logger.info(f"Stored {len(chunks)} chunks for report {report_id}")
            return len(chunks)

        except Exception as e:
            logger.error(f"Failed to store document embeddings: {e}", exc_info=True)
            raise

    def _estimate_page_number(self, char_position: int, pdf_document: PDFDocument) -> int:
        """Estimate page number from character position in full text"""
        cumulative_length = 0
        for page in pdf_document.pages:
            cumulative_length += len(page.text)
            if char_position < cumulative_length:
                return page.page_number
        return pdf_document.metadata.page_count

    async def search_similar(
        self,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.7,
        report_id: Optional[UUID] = None,
        company_ticker: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar text chunks.

        Args:
            query: Search query text
            limit: Maximum results to return
            score_threshold: Minimum similarity score
            report_id: Filter by report ID
            company_ticker: Filter by company ticker
            provider: Embedding provider
            model: Embedding model

        Returns:
            List of search results with scores and payloads
        """
        try:
            client = await self._get_client()

            # Generate query embedding
            query_vector = await self.generate_embedding(query, provider, model)

            # Build filters
            filters = None
            if report_id or company_ticker:
                filters = {}
                if report_id:
                    filters["report_id"] = str(report_id)
                if company_ticker:
                    filters["company_ticker"] = company_ticker

            # Search
            results = await client.search(
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                filters=filters,
            )

            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}", exc_info=True)
            raise


# Global service instance
_vector_service: Optional[VectorService] = None


async def get_vector_service() -> VectorService:
    """Get global vector service instance."""
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service
