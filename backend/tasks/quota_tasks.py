"""
Quota management periodic tasks
"""
from backend.tasks.celery_app import celery_app
from backend.database import SessionLocal
from backend.api.middleware.quota import reset_daily_quota, reset_monthly_quota


@celery_app.task(name='backend.tasks.quota_tasks.reset_daily_quota_task')
def reset_daily_quota_task():
    """
    Reset daily quota for all users
    Runs daily at 00:03 UTC
    """
    db = SessionLocal()
    try:
        reset_daily_quota(db)
        return {"status": "success", "message": "Daily quota reset completed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name='backend.tasks.quota_tasks.reset_monthly_quota_task')
def reset_monthly_quota_task():
    """
    Reset monthly quota for all users
    Runs on 1st of each month at 00:07 UTC
    """
    db = SessionLocal()
    try:
        reset_monthly_quota(db)
        return {"status": "success", "message": "Monthly quota reset completed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
