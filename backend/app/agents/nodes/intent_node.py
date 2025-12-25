"""
Intent Classification Node for LangGraph Agent

Classifies user queries into graph, vector, or hybrid search intents.
"""

import logging

from app.agents.state import AgentState
from app.services.search_service import get_intent_classifier

logger = logging.getLogger(__name__)


def intent_classification_node(state: AgentState) -> AgentState:
    """
    Classify query intent.

    Args:
        state: Current agent state

    Returns:
        Updated state with intent classification
    """
    try:
        logger.info(f"[Intent Node] Processing: {state.query[:100]}...")

        classifier = get_intent_classifier()

        # For now, default to hybrid search
        # In a real implementation, this would be async LLM call
        from app.services.search_service import QueryIntent
        state.intent = QueryIntent.HYBRID
        state.intent_confidence = 0.7

        logger.info(f"[Intent Node] Classified as: {state.intent}")

        return state

    except Exception as e:
        logger.error(f"[Intent Node] Error: {e}", exc_info=True)
        state.add_error(f"Intent classification failed: {str(e)}")
        return state
