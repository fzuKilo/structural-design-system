"""
Quota management middleware
Checks user quota before allowing task creation
"""
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from backend.database import get_db, User
from backend.api.middleware.auth import get_current_user


async def check_quota(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user has available quota

    Raises:
        HTTPException: If quota is exhausted

    Returns:
        User: Current user if quota is available
    """
    # Refresh user to get latest quota values
    db.refresh(current_user)

    if current_user.quota_daily <= 0:
        raise HTTPException(
            status_code=403,
            detail="今日配额已用尽，请明天再试或联系管理员增加配额"
        )

    if current_user.quota_monthly <= 0:
        raise HTTPException(
            status_code=403,
            detail="本月配额已用尽，请下月再试或联系管理员增加配额"
        )

    return current_user


def deduct_quota(user: User, db: Session, task_id: str = None):
    """
    Deduct quota after task completion

    Args:
        user: User object
        db: Database session
        task_id: Optional task ID for tracking
    """
    from backend.database.models import QuotaUsageHistory

    # Deduct quota
    user.quota_daily = max(0, user.quota_daily - 1)
    user.quota_monthly = max(0, user.quota_monthly - 1)

    # Record usage history
    daily_history = QuotaUsageHistory(
        user_id=user.id,
        task_id=task_id,
        quota_type="daily",
        amount=1
    )
    monthly_history = QuotaUsageHistory(
        user_id=user.id,
        task_id=task_id,
        quota_type="monthly",
        amount=1
    )

    db.add(daily_history)
    db.add(monthly_history)
    db.commit()


def reset_daily_quota(db: Session):
    """
    Reset daily quota for all users
    Called by Celery Beat daily at midnight
    """
    from backend.database.models import User

    users = db.query(User).all()
    for user in users:
        user.quota_daily = 100  # Default daily quota

    db.commit()
    print(f"Reset daily quota for {len(users)} users")


def reset_monthly_quota(db: Session):
    """
    Reset monthly quota for all users
    Called by Celery Beat on 1st of each month
    """
    from backend.database.models import User

    users = db.query(User).all()
    for user in users:
        user.quota_monthly = 1000  # Default monthly quota

    db.commit()
    print(f"Reset monthly quota for {len(users)} users")
