"""Chat and Query API endpoints."""

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.graph_builder import get_agent_builder
from app.db.postgres_client import get_postgres_client

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str  # "user" or "assistant"
    content: str
    provider: Optional[str] = None
    model: Optional[str] = None


class ChatRequest(BaseModel):
    """Chat query request."""

    query: str
    conversation_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat query response."""

    conversation_id: str
    message: dict


class ConversationResponse(BaseModel):
    """Conversation model."""

    id: str
    title: Optional[str] = None
    messages: list[ChatMessage]
    created_at: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Submit a query and get an answer.

    Args:
        request: Chat request with query and optional conversation context

    Returns:
        Chat response with answer and sources
    """
    try:
        # Create or use existing conversation
        conversation_id = request.conversation_id or str(uuid4())

        logger.info(f"Processing chat query: {request.query[:100]}...")

        # Get agent
        agent = get_agent_builder()

        # Process query
        state = await agent.process_query(
            query=request.query,
            conversation_id=conversation_id,
            user_id=request.user_id,
            provider=request.provider,
            model=request.model,
        )

        logger.info(f"Agent state after processing - answer: {state.answer[:100] if state.answer else 'None'}, is_error: {state.is_error}")

        # Check for errors
        if state.is_error:
            raise HTTPException(status_code=500, detail=f"Query processing failed: {state.errors[0]}")
        
        # Ensure answer is not empty
        if not state.answer:
            logger.warning("Agent returned empty answer, setting default message")
            state.answer = "죄송합니다. 답변을 생성하는 중 문제가 발생했습니다. 다시 시도해주세요."

        # Save to database
        db = get_postgres_client()
        message_id = str(uuid4())

        # Store conversation message (save both user message and assistant response)
        try:
            # Save user message
            await db.save_message(
                conversation_id=conversation_id,
                message_id=str(uuid4()),
                role="user",
                content=request.query,
                provider=request.provider,
                model=request.model,
            )

            # Save assistant response
            await db.save_message(
                conversation_id=conversation_id,
                message_id=message_id,
                role="assistant",
                content=state.answer or "",
                provider=request.provider,
                model=request.model,
                sources=state.sources,
            )
        except Exception as e:
            logger.warning(f"Failed to save message to database: {e}")

        # Create message object for frontend (matching frontend ChatResponse type)
        from datetime import datetime
        message_dict = {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": state.answer or "",
            "provider": request.provider,
            "model": request.model,
            "sources": state.sources or [],
            "created_at": datetime.utcnow().isoformat(),
        }
        
        return ChatResponse(
            conversation_id=conversation_id,
            message=message_dict,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/conversations")
async def list_conversations(
    user_id: Optional[str] = None, limit: int = 20, offset: int = 0
) -> list[ConversationResponse]:
    """
    List conversations for a user.

    Args:
        user_id: Optional user ID to filter by
        limit: Number of conversations to return
        offset: Offset for pagination

    Returns:
        List of conversations
    """
    try:
        logger.info(f"Listing conversations for user: {user_id}")

        db = get_postgres_client()

        # Get conversations from database
        conversations = await db.get_conversations(user_id=user_id, limit=limit, offset=offset)

        return conversations

    except Exception as e:
        logger.error(f"Failed to list conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> ConversationResponse:
    """
    Get conversation with all messages.

    Args:
        conversation_id: Conversation ID

    Returns:
        Conversation with all messages
    """
    try:
        logger.info(f"Getting conversation: {conversation_id}")

        db = get_postgres_client()

        # Get conversation from database
        conversation = await db.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return conversation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str) -> dict[str, str]:
    """
    Delete a conversation.

    Args:
        conversation_id: Conversation ID

    Returns:
        Success message
    """
    try:
        logger.info(f"Deleting conversation: {conversation_id}")

        db = get_postgres_client()

        # Delete conversation from database
        await db.delete_conversation(conversation_id)

        return {"message": "Conversation deleted"}

    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
