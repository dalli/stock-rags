"""PostgreSQL database connection and models."""

from datetime import datetime
from typing import AsyncGenerator
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


# Models
class Report(Base):
    """Report model."""

    __tablename__ = "reports"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), unique=True, nullable=False)
    title = Column(String(500))
    report_type = Column(String(50))
    publish_date = Column(DateTime)
    security_firm = Column(String(100))
    analyst_name = Column(String(100))
    status = Column(String(50), default="pending")
    page_count = Column(Integer)
    entity_count = Column(Integer, default=0)
    vector_chunks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Entity(Base):
    """Entity model."""

    __tablename__ = "entities"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    report_id = Column(PG_UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"))
    entity_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255))
    properties = Column(JSONB, default={})
    confidence_score = Column(Float, default=1.0)
    neo4j_node_id = Column(String(100))


class Conversation(Base):
    """Conversation model."""

    __tablename__ = "conversations"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    """Message model."""

    __tablename__ = "messages"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    provider = Column(String(50))
    model = Column(String(100))
    sources = Column(JSONB, default=[])
    graph_data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


class LLMSetting(Base):
    """LLM settings model."""

    __tablename__ = "llm_settings"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    default_provider = Column(String(50), default="openai")
    default_model = Column(String(100), default="gpt-4o")
    provider_settings = Column(JSONB, default={})


# Database engine and session
engine = create_async_engine(
    settings.postgres_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.debug,
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db_health() -> bool:
    """Check database health."""
    try:
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
