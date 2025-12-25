"""
LangGraph Agent Builder

Constructs the agent workflow graph for query processing.
"""

import logging
from typing import Optional

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    # Fallback for older versions
    from langgraph.graph import StateGraph, START, END

from app.agents.state import AgentState
from app.agents.nodes import (
    intent_classification_node,
)
from app.agents.nodes.search_nodes import hybrid_search_node_async
from app.agents.nodes.synthesis_node import answer_synthesis_node_async
from app.agents.nodes.search_nodes import select_search_node

logger = logging.getLogger(__name__)


class QueryAgentBuilder:
    """Builder for the query processing agent graph."""

    def __init__(self) -> None:
        self.graph: Optional[StateGraph] = None

    def build(self) -> StateGraph:
        """
        Build the agent graph.

        Returns:
            Compiled StateGraph
        """
        # Create graph
        graph = StateGraph(AgentState)

        # Add nodes - use async versions directly when using ainvoke
        graph.add_node("intent_classification", intent_classification_node)
        graph.add_node("hybrid_search", hybrid_search_node_async)
        graph.add_node("answer_synthesis", answer_synthesis_node_async)

        # Add edges
        graph.add_edge(START, "intent_classification")

        # Always use hybrid search (combines graph + vector search in parallel)
        # This ensures we always get both graph and vector results for better answers
        graph.add_edge("intent_classification", "hybrid_search")
        
        # Hybrid search leads to answer synthesis
        graph.add_edge("hybrid_search", "answer_synthesis")

        # Answer synthesis ends the graph
        graph.add_edge("answer_synthesis", END)

        # Compile graph
        self.graph = graph.compile()

        logger.info("Query agent graph built and compiled")

        return self.graph

    async def process_query(
        self,
        query: str,
        conversation_id: str,
        user_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AgentState:
        """
        Process a user query through the agent.

        Args:
            query: User query string
            conversation_id: Conversation ID for context
            user_id: Optional user ID
            provider: LLM provider to use
            model: LLM model to use

        Returns:
            Final agent state with answer
        """
        if self.graph is None:
            self.build()

        # Create initial state
        state = AgentState(
            query=query,
            conversation_id=conversation_id,
            user_id=user_id,
            provider=provider,
            model=model,
        )

        try:
            logger.info(f"Processing query: {query[:100]}...")

            # Process through graph using ainvoke method (async version)
            # This ensures proper async handling and event loop management
            result = await self.graph.ainvoke(state)

            logger.info(f"Query processing completed, result type: {type(result)}")

            # Return the result (should be AgentState)
            if isinstance(result, AgentState):
                logger.info(f"Answer generated: {result.answer[:100] if result.answer else 'None'}...")
                return result
            elif isinstance(result, dict):
                # If result is a dict, reconstruct AgentState from it
                logger.info(f"Result is dict, reconstructing state. Answer: {result.get('answer', 'None')}")
                # Update state with result values
                if 'answer' in result:
                    state.answer = result['answer']
                if 'sources' in result:
                    state.sources = result['sources']
                if 'errors' in result:
                    state.errors = result['errors']
                    state.is_error = result.get('is_error', False)
                logger.info(f"Reconstructed state answer: {state.answer[:100] if state.answer else 'None'}...")
                return state
            else:
                logger.warning(f"Unexpected result type: {type(result)}, returning original state")
                return state

        except Exception as e:
            logger.error(f"Query processing failed: {e}", exc_info=True)
            state.add_error(f"Query processing failed: {str(e)}")
            return state


# Global agent instance
_agent_builder: Optional[QueryAgentBuilder] = None


def get_agent_builder() -> QueryAgentBuilder:
    """Get global agent builder instance."""
    global _agent_builder
    if _agent_builder is None:
        _agent_builder = QueryAgentBuilder()
        _agent_builder.build()
    return _agent_builder


def get_agent() -> StateGraph:
    """Get compiled agent graph."""
    return get_agent_builder().graph
