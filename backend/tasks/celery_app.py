"""
Celery Configuration
"""
from celery import Celery
from backend.api.config import settings

celery_app = Celery(
    "structural_design",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['backend.tasks.design_task']
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
