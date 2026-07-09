"""Celery application configuration and initialization.

Configures the Celery task queue with Redis broker and result backend.
Provides task routing, serialization, and error handling settings.

Usage:
    from app.celery_app import celery_app

    @celery_app.task(bind=True, max_retries=3)
    def my_task(self, data: dict) -> dict:
        ...
"""

from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure

from app.config import settings

# ── Celery Application ─────────────────────────────────────────
celery_app = Celery(
    "rag_kb_system",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend,
)

# ── Configuration ──────────────────────────────────────────────
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="Asia/Shanghai",
    enable_utc=True,

    # Task execution
    task_track_started=True,
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Results
    result_expires=3600,  # 1 hour
    result_persistent=True,

    # Retry policy
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Worker
    worker_max_tasks_per_child=100,
    worker_max_memory_per_child=512000,  # 512MB

    # Queues
    task_routes={
        "app.tasks.document.*": {"queue": "documents"},
        "app.tasks.embedding.*": {"queue": "embeddings"},
        "app.tasks.retrieval.*": {"queue": "embeddings"},
    },

    # Queue defaults
    task_default_queue="default",
)

# ── Auto-discover tasks ────────────────────────────────────────
celery_app.autodiscover_tasks(["app.tasks"])


# ── Signal Handlers ────────────────────────────────────────────
@task_prerun.connect
def task_prerun_handler(sender: object, task_id: str, **kwargs: object) -> None:
    """Log task start.

    Args:
        sender: Task class.
        task_id: Unique task identifier.
        **kwargs: Additional signal arguments.
    """
    import logging
    logger = logging.getLogger("celery")
    logger.info("Task started: %s [%s]", sender, task_id)


@task_postrun.connect
def task_postrun_handler(
    sender: object, task_id: str, retval: object, **kwargs: object
) -> None:
    """Log task completion.

    Args:
        sender: Task class.
        task_id: Unique task identifier.
        retval: Task return value.
        **kwargs: Additional signal arguments.
    """
    import logging
    logger = logging.getLogger("celery")
    logger.info("Task completed: %s [%s]", sender, task_id)


@task_failure.connect
def task_failure_handler(
    sender: object, task_id: str, exception: Exception, **kwargs: object
) -> None:
    """Log task failure.

    Args:
        sender: Task class.
        task_id: Unique task identifier.
        exception: The exception that caused the failure.
        **kwargs: Additional signal arguments.
    """
    import logging
    logger = logging.getLogger("celery")
    logger.error(
        "Task failed: %s [%s] - %s: %s",
        sender, task_id, type(exception).__name__, exception,
    )
