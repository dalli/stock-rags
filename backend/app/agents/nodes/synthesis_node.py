"""
Answer Synthesis Node for LangGraph Agent

Synthesizes final answers from search results.
"""

import logging
import asyncio

from app.agents.state import AgentState
from app.services.search_service import get_answer_synthesizer

logger = logging.getLogger(__name__)


async def answer_synthesis_node_async(state: AgentState) -> AgentState:
    """
    Synthesize final answer from search results (async version).

    Args:
        state: Current agent state

    Returns:
        Updated state with synthesized answer
    """
    try:
        logger.info(f"[Synthesis Node] Synthesizing answer for query: {state.query[:100]}...")

        # Get answer synthesizer
        synthesizer = get_answer_synthesizer()

        # Combine search results
        search_results = {
            "graph_results": state.graph_results,
            "vector_results": state.vector_results,
            "search_results": state.search_results,
        }

        logger.info(f"[Synthesis Node] Search results: graph={bool(state.graph_results)}, vector={bool(state.vector_results)}")

        # Synthesize answer using LLM
        result = await synthesizer.synthesize(
            query=state.query,
            search_results=search_results,
            provider=state.provider,
            model=state.model,
        )

        # Update state with synthesized answer
        state.answer = result.get("answer", "")
        state.sources = result.get("sources", [])

        logger.info(f"[Synthesis Node] Answer generated: {state.answer[:100] if state.answer else 'None'}...")
        logger.info(f"[Synthesis Node] Answer generated with {len(state.sources)} sources")

        return state

    except Exception as e:
        logger.error(f"[Synthesis Node] Error: {e}", exc_info=True)
        state.add_error(f"Answer synthesis failed: {str(e)}")
        # Fallback answer
        state.answer = f"죄송합니다. 답변을 생성하는 중 오류가 발생했습니다: {str(e)}"
        return state


def answer_synthesis_node(state: AgentState) -> AgentState:
    """
    Synthesize final answer from search results (sync wrapper for LangGraph).

    Args:
        state: Current agent state

    Returns:
        Updated state with synthesized answer
    """
    try:
        # Run async function in sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create a new event loop in a thread
                import concurrent.futures
                import threading
                
                def run_in_new_loop():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(answer_synthesis_node_async(state))
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_new_loop)
                    return future.result()
            else:
                return loop.run_until_complete(answer_synthesis_node_async(state))
        except RuntimeError:
            # No event loop exists, create a new one
            return asyncio.run(answer_synthesis_node_async(state))
    except Exception as e:
        logger.error(f"[Synthesis Node] Sync wrapper error: {e}", exc_info=True)
        state.add_error(f"Answer synthesis failed: {str(e)}")
        state.answer = f"죄송합니다. 답변을 생성하는 중 오류가 발생했습니다: {str(e)}"
        return state
