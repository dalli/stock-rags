"""Celery application for background tasks."""

from celery import Celery
from celery.signals import worker_process_init

from app.config import get_settings

settings = get_settings()

# Create Celery application
app = Celery(
    "stockrags",
    broker=settings.celery_broker_url,
    backend=settings.redis_url,
)

# Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    # Worker configuration for API rate limiting
    worker_prefetch_multiplier=1,  # Prefetch only 1 task at a time
    worker_max_tasks_per_child=10,  # Recycle worker after 10 tasks
    # Task routing
    task_default_queue="default",
    task_routes={
        "app.workers.tasks.process_report": {"queue": "reports"},
    },
    # Queue configuration for rate limiting
    task_queue_max_priority=10,
)

# Auto-discover tasks
app.autodiscover_tasks(["app.workers.tasks"])


@worker_process_init.connect
def init_worker(**kwargs):
    """Initialize LLM providers when worker process starts"""
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

    # Register LLM providers - prioritize Gemini
    if settings.google_api_key:
        llm_router.register_provider("gemini", GeminiProvider())
        llm_router.set_default_provider("gemini")

    if settings.openai_api_key:
        llm_router.register_provider("openai", OpenAIProvider())

    if settings.anthropic_api_key:
        llm_router.register_provider("anthropic", AnthropicProvider())

    # Always register local providers
    llm_router.register_provider("ollama", OllamaProvider())
    llm_router.register_provider("lmstudio", LMStudioProvider())

    # Register embedding providers - prioritize Gemini
    if settings.google_api_key:
        embedding_router.register_provider("gemini", GeminiEmbeddingProvider())
        embedding_router.set_default_provider("gemini")

    embedding_router.register_provider("ollama", OllamaEmbeddingProvider())

    if settings.openai_api_key:
        embedding_router.register_provider("openai", OpenAIEmbeddingProvider())
