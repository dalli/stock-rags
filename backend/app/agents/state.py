"""
LangGraph Agent State Definition

Defines the shared state structure for the query processing agent.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from app.services.search_service import QueryIntent


@dataclass
class AgentState:
    """
    Agent state for query processing workflow.

    Tracks query progression through intent classification, search, and answer synthesis.
    """

    # Query information
    query: str
    conversation_id: str
    user_id: Optional[str] = None

    # LLM provider settings
    provider: Optional[str] = None
    model: Optional[str] = None

    # Intent classification
    intent: Optional[QueryIntent] = None
    intent_confidence: float = 0.0

    # Search results
    search_results: dict[str, Any] = field(default_factory=dict)
    graph_results: dict[str, Any] = field(default_factory=dict)
    vector_results: dict[str, Any] = field(default_factory=dict)

    # Generated answer
    answer: Optional[str] = None
    sources: list[dict[str, Any]] = field(default_factory=list)

    # Error handling
    errors: list[str] = field(default_factory=list)
    is_error: bool = False

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_error(self, error: str) -> None:
        """Add error message to state."""
        self.errors.append(error)
        self.is_error = True

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "query": self.query,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "provider": self.provider,
            "model": self.model,
            "intent": self.intent.value if self.intent else None,
            "intent_confidence": self.intent_confidence,
            "search_results": self.search_results,
            "graph_results": self.graph_results,
            "vector_results": self.vector_results,
            "answer": self.answer,
            "sources": self.sources,
            "errors": self.errors,
            "is_error": self.is_error,
            "metadata": self.metadata,
        }
