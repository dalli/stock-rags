"""Models API endpoints."""

from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.neo4j import neo4j_client
from app.db.postgres import check_db_health
from app.db.qdrant import qdrant_client
from app.db.redis import redis_client
from app.llm.router import embedding_router, llm_router

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    databases: Dict[str, bool]
    llm_providers: Dict[str, bool]


class ModelsResponse(BaseModel):
    """Available models response."""

    llm_models: Dict[str, List[str]]
    embedding_models: Dict[str, List[str]]


class SetDefaultRequest(BaseModel):
    """Set default model request."""

    provider: str
    model: str


@router.get("/health/ready", response_model=HealthResponse)
async def health_ready() -> HealthResponse:
    """Comprehensive health check for all services."""
    # Check databases
    db_health = {
        "postgres": await check_db_health(),
        "neo4j": await neo4j_client.check_health(),
        "qdrant": await qdrant_client.check_health(),
        "redis": await redis_client.check_health(),
    }

    # Check LLM providers
    llm_health = await llm_router.health_check()

    # Overall status
    all_healthy = all(db_health.values())
    status = "healthy" if all_healthy else "degraded"

    return HealthResponse(
        status=status,
        databases=db_health,
        llm_providers=llm_health,
    )


@router.get("/models", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    """List all available LLM and embedding models."""
    llm_models = await llm_router.list_all_models()
    embedding_models = await embedding_router.list_all_models()

    return ModelsResponse(
        llm_models=llm_models,
        embedding_models=embedding_models,
    )


@router.put("/models/default")
async def set_default_model(request: SetDefaultRequest) -> dict[str, str]:
    """Set default LLM or embedding provider."""
    try:
        # Try to set as LLM provider first
        llm_router.set_default_provider(request.provider)
        return {"message": f"Default LLM provider set to {request.provider}"}
    except ValueError:
        # Try embedding provider
        try:
            embedding_router.set_default_provider(request.provider)
            return {"message": f"Default embedding provider set to {request.provider}"}
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Provider '{request.provider}' not found")
