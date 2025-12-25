"""
Search Nodes for LangGraph Agent

Handles graph, vector, and hybrid search operations.
"""

import logging
import asyncio

from app.agents.state import AgentState
from app.services.search_service import (
    QueryIntent,
    get_graph_querier,
    get_vector_searcher,
    get_hybrid_searcher,
)

logger = logging.getLogger(__name__)


async def graph_search_node_async(state: AgentState) -> AgentState:
    """
    Execute graph-based search (async version).

    Args:
        state: Current agent state

    Returns:
        Updated state with graph search results
    """
    try:
        logger.info(f"[Graph Search Node] Executing graph search for: {state.query[:100]}...")

        graph_querier = get_graph_querier()

        # Generate Cypher query
        cypher_query = await graph_querier.generate_cypher(
            query=state.query,
            provider=state.provider,
            model=state.model,
        )

        # Execute Cypher query
        graph_data = await graph_querier.execute_cypher(cypher_query)

        results = {
            "query": state.query,
            "cypher_query": cypher_query,
            "results": graph_data.get("results", []),
            "search_type": "graph",
        }

        state.graph_results = results
        state.search_results = results

        logger.info(f"[Graph Search Node] Found {len(results.get('results', []))} graph results")

        return state

    except Exception as e:
        logger.error(f"[Graph Search Node] Error: {e}", exc_info=True)
        state.add_error(f"Graph search failed: {str(e)}")
        # Return empty results on error
        state.graph_results = {"query": state.query, "results": [], "search_type": "graph"}
        return state


def graph_search_node(state: AgentState) -> AgentState:
    """
    Execute graph-based search (sync wrapper).

    Args:
        state: Current agent state

    Returns:
        Updated state with graph search results
    """
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                
                def run_in_new_loop():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(graph_search_node_async(state))
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_new_loop)
                    return future.result()
            else:
                return loop.run_until_complete(graph_search_node_async(state))
        except RuntimeError:
            return asyncio.run(graph_search_node_async(state))
    except Exception as e:
        logger.error(f"[Graph Search Node] Sync wrapper error: {e}", exc_info=True)
        state.graph_results = {"query": state.query, "results": [], "search_type": "graph"}
        return state


async def vector_search_node_async(state: AgentState) -> AgentState:
    """
    Execute vector-based search (async version).

    Args:
        state: Current agent state

    Returns:
        Updated state with vector search results
    """
    try:
        logger.info(f"[Vector Search Node] Executing vector search for: {state.query[:100]}...")

        vector_searcher = get_vector_searcher()

        # Execute vector search
        search_data = await vector_searcher.search(
            query=state.query,
            provider=state.provider,
            model=state.model,
        )

        results = {
            "query": state.query,
            "results": search_data.get("results", []),
            "search_type": "vector",
        }

        state.vector_results = results
        state.search_results = results

        logger.info(f"[Vector Search Node] Found {len(results.get('results', []))} vector results")

        return state

    except Exception as e:
        logger.error(f"[Vector Search Node] Error: {e}", exc_info=True)
        state.add_error(f"Vector search failed: {str(e)}")
        # Return empty results on error
        state.vector_results = {"query": state.query, "results": [], "search_type": "vector"}
        return state


def vector_search_node(state: AgentState) -> AgentState:
    """
    Execute vector-based search (sync wrapper).

    Args:
        state: Current agent state

    Returns:
        Updated state with vector search results
    """
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                
                def run_in_new_loop():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(vector_search_node_async(state))
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_new_loop)
                    return future.result()
            else:
                return loop.run_until_complete(vector_search_node_async(state))
        except RuntimeError:
            return asyncio.run(vector_search_node_async(state))
    except Exception as e:
        logger.error(f"[Vector Search Node] Sync wrapper error: {e}", exc_info=True)
        state.vector_results = {"query": state.query, "results": [], "search_type": "vector"}
        return state


async def hybrid_search_node_async(state: AgentState) -> AgentState:
    """
    Execute hybrid search combining graph and vector approaches (async version).

    Args:
        state: Current agent state

    Returns:
        Updated state with hybrid search results
    """
    try:
        logger.info(f"[Hybrid Search Node] Executing hybrid search for: {state.query[:100]}...")

        hybrid_searcher = get_hybrid_searcher()

        # Execute hybrid search
        search_data = await hybrid_searcher.search(
            query=state.query,
            provider=state.provider,
            model=state.model,
        )

        results = {
            "query": state.query,
            "search_type": "hybrid",
            "graph_results": search_data.get("graph_results", {"results": []}),
            "vector_results": search_data.get("vector_results", {"results": []}),
        }

        state.graph_results = results.get("graph_results", {})
        state.vector_results = results.get("vector_results", {})
        state.search_results = results

        logger.info(
            f"[Hybrid Search Node] Found {len(state.graph_results.get('results', []))} graph "
            f"and {len(state.vector_results.get('results', []))} vector results"
        )

        return state

    except Exception as e:
        logger.error(f"[Hybrid Search Node] Error: {e}", exc_info=True)
        state.add_error(f"Hybrid search failed: {str(e)}")
        # Return empty results on error
        state.graph_results = {"results": []}
        state.vector_results = {"results": []}
        state.search_results = {"query": state.query, "search_type": "hybrid", "graph_results": {"results": []}, "vector_results": {"results": []}}
        return state


def hybrid_search_node(state: AgentState) -> AgentState:
    """
    Execute hybrid search combining graph and vector approaches (sync wrapper).

    Args:
        state: Current agent state

    Returns:
        Updated state with hybrid search results
    """
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                
                def run_in_new_loop():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(hybrid_search_node_async(state))
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_new_loop)
                    return future.result()
            else:
                return loop.run_until_complete(hybrid_search_node_async(state))
        except RuntimeError:
            return asyncio.run(hybrid_search_node_async(state))
    except Exception as e:
        logger.error(f"[Hybrid Search Node] Sync wrapper error: {e}", exc_info=True)
        state.graph_results = {"results": []}
        state.vector_results = {"results": []}
        state.search_results = {"query": state.query, "search_type": "hybrid", "graph_results": {"results": []}, "vector_results": {"results": []}}
        return state


def select_search_node(state: AgentState) -> str:
    """
    Conditional routing function to select search node based on intent.

    Args:
        state: Current agent state

    Returns:
        Node name to execute
    """
    if state.is_error:
        return "end"

    if state.intent is None:
        return "vector_search"  # Default to vector search

    if state.intent == QueryIntent.GRAPH:
        return "graph_search"
    elif state.intent == QueryIntent.VECTOR:
        return "vector_search"
    else:  # QueryIntent.HYBRID
        return "hybrid_search"
