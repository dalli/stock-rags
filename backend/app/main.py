"""FastAPI main application."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import models, reports, chat, graph
from app.config import get_settings
from app.db.neo4j import neo4j_client
from app.db.postgres import init_db
from app.db.qdrant import qdrant_client
from app.llm.providers import (
    AnthropicProvider,
    GeminiEmbeddingProvider,
    GeminiProvider,
    LMStudioProvider,
    OllamaEmbeddingProvider,
    OllamaProvider,
    OpenAIEmbeddingProvider,
    OpenAIProvider,
)
from app.llm.router import embedding_router, llm_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    await init_db()
    await neo4j_client.connect()
    await neo4j_client.create_indexes()
    await qdrant_client.connect()
    await qdrant_client.create_collection()

    # Register LLM providers
    if settings.openai_api_key:
        llm_router.register_provider("openai", OpenAIProvider())
        llm_router.set_default_provider("openai")

    if settings.anthropic_api_key:
        llm_router.register_provider("anthropic", AnthropicProvider())

    if settings.google_api_key:
        llm_router.register_provider("gemini", GeminiProvider())

    # Always register local providers (they may not be available)
    llm_router.register_provider("ollama", OllamaProvider())
    llm_router.register_provider("lmstudio", LMStudioProvider())

    # Register embedding providers
    if settings.google_api_key:
        embedding_router.register_provider("gemini", GeminiEmbeddingProvider())
        embedding_router.set_default_provider("gemini")
    
    if settings.openai_api_key:
        embedding_router.register_provider("openai", OpenAIEmbeddingProvider())
        if not settings.google_api_key:
            embedding_router.set_default_provider("openai")

    embedding_router.register_provider("ollama", OllamaEmbeddingProvider())

    yield

    # Shutdown
    await neo4j_client.close()
    await qdrant_client.close()


app = FastAPI(
    title="Stock RAGs API",
    description="GraphRAG Stock Report Analysis Service",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(models.router, prefix="/api/v1", tags=["models"])
app.include_router(reports.router, prefix="/api/v1", tags=["reports"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(graph.router, prefix="/api/v1", tags=["graph"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Stock RAGs API", "version": "0.1.0"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Basic health check."""
    return {"status": "healthy"}
