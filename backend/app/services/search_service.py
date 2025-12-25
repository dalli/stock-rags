"""
Search Service for Query Execution

Handles intent classification, graph queries, vector search, and result synthesis.
"""

import json
import logging
from enum import Enum
from typing import Any, Optional

from app.db.neo4j import get_neo4j, neo4j_client
from app.db.qdrant import get_qdrant, qdrant_client
from app.llm.router import get_llm_router
from app.prompts.loader import get_prompt_loader

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    """Enum for different types of query intents."""

    GRAPH = "graph"  # Structured graph query (Cypher)
    VECTOR = "vector"  # Semantic search query
    HYBRID = "hybrid"  # Combined graph + vector search


class IntentClassifier:
    """Classify user queries into intent types."""

    def __init__(self) -> None:
        self.prompt_loader = get_prompt_loader()
        self.llm_router = get_llm_router()

    async def classify(
        self,
        query: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> QueryIntent:
        """
        Classify user query intent.

        Args:
            query: User query string
            provider: LLM provider to use
            model: LLM model to use

        Returns:
            QueryIntent enum value
        """
        try:
            # Load intent classification prompt
            template = self.prompt_loader.load("reasoning/intent_classification.yaml")
            system_prompt, user_prompt = template.render(query=query)

            # Get LLM provider
            llm = self.llm_router.get_provider(provider, model)

            logger.info(f"Classifying query intent: {query[:100]}...")

            # Get output schema for structured generation
            output_schema = template.output_schema

            # Generate intent classification
            result = await llm.generate_structured(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=output_schema,
            )

            # Extract intent from result
            intent_str = result.get("intent", "hybrid").lower()
            intent = QueryIntent(intent_str)

            logger.info(f"Classified intent: {intent} (confidence: {result.get('confidence', 0)})")

            return intent

        except Exception as e:
            logger.error(f"Intent classification failed: {e}", exc_info=True)
            # Default to hybrid search if classification fails
            return QueryIntent.HYBRID


class GraphQuerier:
    """Execute Cypher queries against Neo4j."""

    def __init__(self) -> None:
        # Use global neo4j_client instance directly
        self.neo4j = neo4j_client
        self.prompt_loader = get_prompt_loader()
        self.llm_router = get_llm_router()

    async def generate_cypher(
        self,
        query: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Generate Cypher query from natural language.

        Args:
            query: Natural language query
            provider: LLM provider to use
            model: LLM model to use

        Returns:
            Generated Cypher query string
        """
        try:
            # Load Cypher generation prompt
            template = self.prompt_loader.load("reasoning/cypher_generation.yaml")
            system_prompt, user_prompt = template.render(query=query)

            # Get LLM provider
            llm = self.llm_router.get_provider(provider, model)

            logger.info(f"Generating Cypher for: {query[:100]}...")

            # Generate Cypher query
            result = await llm.generate(prompt=user_prompt, system_prompt=system_prompt)

            # Extract Cypher from result - remove markdown code blocks if present
            cypher_query = result.strip()
            
            # Remove markdown code blocks (```cypher ... ``` or ``` ... ```)
            import re
            # Match ```cypher or ``` followed by code and closing ```
            cypher_query = re.sub(r'```(?:cypher)?\s*\n?(.*?)\n?```', r'\1', cypher_query, flags=re.DOTALL)
            # Also remove any leading/trailing whitespace
            cypher_query = cypher_query.strip()

            logger.info(f"Generated Cypher: {cypher_query[:200]}...")

            return cypher_query

        except Exception as e:
            logger.error(f"Cypher generation failed: {e}", exc_info=True)
            raise

    async def execute_cypher(self, cypher_query: str) -> dict[str, Any]:
        """
        Execute Cypher query against Neo4j.

        Args:
            cypher_query: Cypher query string

        Returns:
            Query results with nodes and relationships
        """
        try:
            logger.info(f"Executing Cypher query...")

            # Ensure connection is established
            if not self.neo4j.driver:
                await self.neo4j.connect()

            # Execute query using execute_query method
            results = await self.neo4j.execute_query(cypher_query)

            logger.info(f"Cypher query returned {len(results)} results")

            return {"results": results, "query": cypher_query}

        except Exception as e:
            logger.error(f"Cypher execution failed: {e}", exc_info=True)
            raise

    async def query(
        self,
        query: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Execute graph-based query.

        Args:
            query: Natural language query
            provider: LLM provider to use
            model: LLM model to use

        Returns:
            Query results
        """
        # Generate Cypher query
        cypher = await self.generate_cypher(query, provider, model)

        # Execute Cypher
        results = await self.execute_cypher(cypher)

        return results


class VectorSearcher:
    """Execute vector similarity searches in Qdrant."""

    def __init__(self) -> None:
        # Use global qdrant_client instance directly
        self.qdrant = qdrant_client
        self.llm_router = get_llm_router()

    async def search(
        self,
        query: str,
        limit: int = 10,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Perform semantic search on report chunks.

        Args:
            query: Query text
            limit: Number of results to return
            provider: Embedding provider to use
            model: Embedding model to use

        Returns:
            Search results with scores and source information
        """
        try:
            logger.info(f"Performing vector search: {query[:100]}...")

            # Get embedding
            embedding_provider = self.llm_router.get_embedding_provider(provider, model)
            query_embedding = await embedding_provider.embed_text(query)

            # Ensure connection is established
            if not self.qdrant.client:
                await self.qdrant.connect()

            # Search in Qdrant
            results = await self.qdrant.search(
                query_vector=query_embedding,
                limit=limit,
            )

            logger.info(f"Vector search returned {len(results)} results")

            return {
                "results": results,
                "query": query,
                "search_type": "vector",
            }

        except Exception as e:
            logger.error(f"Vector search failed: {e}", exc_info=True)
            raise


class HybridSearcher:
    """Execute hybrid search combining graph and vector approaches."""

    def __init__(self) -> None:
        self.graph_querier = GraphQuerier()
        self.vector_searcher = VectorSearcher()
        self.llm_router = get_llm_router()

    async def search(
        self,
        query: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Execute hybrid search.

        Args:
            query: Query text
            provider: LLM provider to use
            model: LLM model to use

        Returns:
            Combined search results
        """
        try:
            logger.info(f"Performing hybrid search: {query[:100]}...")

            # Execute both searches in parallel
            graph_results = await self.graph_querier.query(query, provider, model)
            vector_results = await self.vector_searcher.search(query, limit=10, provider=provider, model=model)

            # Combine results
            combined = {
                "query": query,
                "search_type": "hybrid",
                "graph_results": graph_results,
                "vector_results": vector_results,
            }

            logger.info("Hybrid search completed")

            return combined

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}", exc_info=True)
            raise


class AnswerSynthesizer:
    """Synthesize final answers from search results."""

    def __init__(self) -> None:
        self.prompt_loader = get_prompt_loader()
        self.llm_router = get_llm_router()

    async def synthesize(
        self,
        query: str,
        search_results: dict[str, Any],
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Synthesize final answer from search results.

        Args:
            query: Original user query
            search_results: Results from graph/vector/hybrid search
            provider: LLM provider to use
            model: LLM model to use

        Returns:
            Synthesized answer with sources
        """
        try:
            # Load answer synthesis prompt
            template = self.prompt_loader.load("reasoning/answer_synthesis.yaml")

            # Format search results for context
            # Convert non-serializable objects (like DateTime) to strings
            def json_serializer(obj):
                """JSON serializer for objects not serializable by default json code"""
                from datetime import datetime, date
                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")
            
            results_context = json.dumps(search_results, indent=2, ensure_ascii=False, default=json_serializer)

            # Render prompt
            system_prompt, user_prompt = template.render(
                query=query,
                search_results=results_context,
            )

            # Get LLM provider
            llm = self.llm_router.get_provider(provider, model)

            logger.info(f"Synthesizing answer for: {query[:100]}...")

            # Generate answer
            answer = await llm.generate(prompt=user_prompt, system_prompt=system_prompt)

            # Extract sources from search results
            sources = self._extract_sources(search_results)

            logger.info(f"Answer synthesized with {len(sources)} sources")

            return {
                "answer": answer,
                "sources": sources,
                "query": query,
                "search_results": search_results,
            }

        except Exception as e:
            logger.error(f"Answer synthesis failed: {e}", exc_info=True)
            raise

    def _extract_sources(self, search_results: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract source information from search results."""
        sources = []

        # Extract from vector search results
        if "vector_results" in search_results:
            vector_results = search_results["vector_results"]
            if vector_results and isinstance(vector_results, dict):
                for result in vector_results.get("results", []):
                    if result and isinstance(result, dict):
                        payload = result.get("payload") or {}
                        sources.append({
                            "type": "report_chunk",
                            "report_id": payload.get("report_id") if isinstance(payload, dict) else None,
                            "page_number": payload.get("page_number") if isinstance(payload, dict) else None,
                            "score": result.get("score"),
                        })

        # Extract from graph results
        if "graph_results" in search_results:
            for result in search_results["graph_results"].get("results", []):
                if isinstance(result, dict):
                    sources.append({
                        "type": "graph_node",
                        "data": result,
                    })

        return sources


# Global service instances
_intent_classifier: Optional[IntentClassifier] = None
_graph_querier: Optional[GraphQuerier] = None
_vector_searcher: Optional[VectorSearcher] = None
_hybrid_searcher: Optional[HybridSearcher] = None
_answer_synthesizer: Optional[AnswerSynthesizer] = None


def get_intent_classifier() -> IntentClassifier:
    """Get global intent classifier instance."""
    global _intent_classifier
    if _intent_classifier is None:
        _intent_classifier = IntentClassifier()
    return _intent_classifier


def get_graph_querier() -> GraphQuerier:
    """Get global graph querier instance."""
    global _graph_querier
    if _graph_querier is None:
        _graph_querier = GraphQuerier()
    return _graph_querier


def get_vector_searcher() -> VectorSearcher:
    """Get global vector searcher instance."""
    global _vector_searcher
    if _vector_searcher is None:
        _vector_searcher = VectorSearcher()
    return _vector_searcher


def get_hybrid_searcher() -> HybridSearcher:
    """Get global hybrid searcher instance."""
    global _hybrid_searcher
    if _hybrid_searcher is None:
        _hybrid_searcher = HybridSearcher()
    return _hybrid_searcher


def get_answer_synthesizer() -> AnswerSynthesizer:
    """Get global answer synthesizer instance."""
    global _answer_synthesizer
    if _answer_synthesizer is None:
        _answer_synthesizer = AnswerSynthesizer()
    return _answer_synthesizer
