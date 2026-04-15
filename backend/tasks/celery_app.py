"""
Celery Configuration
"""
from celery import Celery
from celery.schedules import crontab
from backend.api.config import settings

celery_app = Celery(
    "structural_design",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['backend.tasks.design_task', 'backend.tasks.quota_tasks']
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Configure periodic tasks
celery_app.conf.beat_schedule = {
    'reset-daily-quota': {
        'task': 'backend.tasks.quota_tasks.reset_daily_quota_task',
        'schedule': crontab(hour=0, minute=3),  # Daily at 00:03 UTC
    },
    'reset-monthly-quota': {
        'task': 'backend.tasks.quota_tasks.reset_monthly_quota_task',
        'schedule': crontab(day_of_month=1, hour=0, minute=7),  # 1st of month at 00:07 UTC
    },
}
