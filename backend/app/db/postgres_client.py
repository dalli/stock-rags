"""PostgreSQL client wrapper for high-level operations."""

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import AsyncSessionLocal, Conversation, Message

logger = logging.getLogger(__name__)


class PostgresClient:
    """Client for PostgreSQL operations."""

    async def save_message(
        self,
        conversation_id: str,
        message_id: str,
        role: str,
        content: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        sources: Optional[list[dict[str, Any]]] = None,
        graph_data: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Save a message to the database.

        Args:
            conversation_id: Conversation ID
            message_id: Message ID
            role: Message role (user or assistant)
            content: Message content
            provider: LLM provider used
            model: LLM model used
            sources: List of sources
            graph_data: Graph data if applicable
        """
        async with AsyncSessionLocal() as session:
            try:
                # Create or get conversation
                conv_stmt = select(Conversation).where(Conversation.id == UUID(conversation_id))
                result = await session.execute(conv_stmt)
                conversation = result.scalar_one_or_none()

                if not conversation:
                    conversation = Conversation(id=UUID(conversation_id))
                    session.add(conversation)
                    await session.flush()

                # Create message
                message = Message(
                    id=UUID(message_id),
                    conversation_id=UUID(conversation_id),
                    role=role,
                    content=content,
                    provider=provider,
                    model=model,
                    sources=sources or [],
                    graph_data=graph_data,
                )
                session.add(message)
                await session.commit()

                logger.info(f"Message saved: {message_id}")

            except Exception as e:
                logger.error(f"Failed to save message: {e}", exc_info=True)
                await session.rollback()
                raise

    async def get_conversation(self, conversation_id: str) -> Optional[dict[str, Any]]:
        """
        Get a conversation with all its messages.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation data with messages
        """
        async with AsyncSessionLocal() as session:
            try:
                # Get conversation
                conv_stmt = select(Conversation).where(Conversation.id == UUID(conversation_id))
                result = await session.execute(conv_stmt)
                conversation = result.scalar_one_or_none()

                if not conversation:
                    return None

                # Get messages
                msg_stmt = (
                    select(Message)
                    .where(Message.conversation_id == UUID(conversation_id))
                    .order_by(Message.created_at)
                )
                result = await session.execute(msg_stmt)
                messages = result.scalars().all()

                return {
                    "id": str(conversation.id),
                    "title": conversation.title,
                    "created_at": conversation.created_at.isoformat(),
                    "messages": [
                        {
                            "role": msg.role,
                            "content": msg.content,
                            "provider": msg.provider,
                            "model": msg.model,
                        }
                        for msg in messages
                    ],
                }

            except Exception as e:
                logger.error(f"Failed to get conversation: {e}", exc_info=True)
                raise

    async def get_conversations(
        self, user_id: Optional[str] = None, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        Get list of conversations.

        Args:
            user_id: Optional user ID to filter by
            limit: Number of conversations to return
            offset: Offset for pagination

        Returns:
            List of conversations
        """
        async with AsyncSessionLocal() as session:
            try:
                # For now, return all conversations (user_id filtering can be added later)
                stmt = select(Conversation).order_by(Conversation.created_at.desc()).limit(limit).offset(offset)
                result = await session.execute(stmt)
                conversations = result.scalars().all()

                return [
                    {
                        "id": str(conv.id),
                        "title": conv.title,
                        "created_at": conv.created_at.isoformat(),
                        "messages": [],
                    }
                    for conv in conversations
                ]

            except Exception as e:
                logger.error(f"Failed to get conversations: {e}", exc_info=True)
                raise

    async def delete_conversation(self, conversation_id: str) -> None:
        """
        Delete a conversation.

        Args:
            conversation_id: Conversation ID
        """
        async with AsyncSessionLocal() as session:
            try:
                # Get and delete conversation (cascade delete messages)
                stmt = select(Conversation).where(Conversation.id == UUID(conversation_id))
                result = await session.execute(stmt)
                conversation = result.scalar_one_or_none()

                if conversation:
                    await session.delete(conversation)
                    await session.commit()

                logger.info(f"Conversation deleted: {conversation_id}")

            except Exception as e:
                logger.error(f"Failed to delete conversation: {e}", exc_info=True)
                await session.rollback()
                raise


# Global client instance
_postgres_client: Optional[PostgresClient] = None


def get_postgres_client() -> PostgresClient:
    """Get global PostgreSQL client instance."""
    global _postgres_client
    if _postgres_client is None:
        _postgres_client = PostgresClient()
    return _postgres_client
