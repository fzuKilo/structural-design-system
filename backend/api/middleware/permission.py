"""Permission middleware"""
from functools import wraps
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from backend.database.models import Permission, RolePermission, Role, UserRole
from backend.api.middleware.auth import get_current_user
from backend.database.session import get_db


def require_permission(permission: str):
    """Check if user has specific permission"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user=None, db: Session = None, **kwargs):
            if not current_user:
                raise HTTPException(status_code=401, detail="未认证")

            has_perm = db.query(Permission).join(
                RolePermission
            ).join(Role).join(UserRole).filter(
                UserRole.user_id == current_user.id,
                Permission.name == permission
            ).first()

            if not has_perm:
                raise HTTPException(status_code=403, detail="权限不足")

            return await func(*args, current_user=current_user, db=db, **kwargs)
        return wrapper
    return decorator


def require_role(role_name: str):
    """Check if user has specific role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user=None, **kwargs):
            if not current_user:
                raise HTTPException(status_code=401, detail="未认证")

            user_roles = [role.name for role in current_user.roles]
            if role_name not in user_roles:
                raise HTTPException(status_code=403, detail=f"需要角色: {role_name}")

            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
