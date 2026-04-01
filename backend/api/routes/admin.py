"""Admin API routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from backend.database.session import get_db
from backend.database.models import User, Role, Permission, UserRole
from backend.api.middleware import get_current_user, require_permission

router = APIRouter(prefix="/admin", tags=["管理"])


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    roles: List[str]

    class Config:
        from_attributes = True


class RoleAssignRequest(BaseModel):
    role_id: str


@router.get("/users")
async def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user list (requires user:manage permission)"""
    has_perm = db.query(Permission).join(
        Role.permissions
    ).join(Role.users).filter(
        User.id == current_user.id,
        Permission.name == "user:manage"
    ).first()

    if not has_perm:
        raise HTTPException(status_code=403, detail="权限不足")

    users = db.query(User).all()
    return {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "roles": [r.name for r in u.roles]
            }
            for u in users
        ]
    }


@router.post("/users/{user_id}/roles")
async def assign_role(
    user_id: str,
    request: RoleAssignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign role to user"""
    has_perm = db.query(Permission).join(
        Role.permissions
    ).join(Role.users).filter(
        User.id == current_user.id,
        Permission.name == "user:manage"
    ).first()

    if not has_perm:
        raise HTTPException(status_code=403, detail="权限不足")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    role = db.query(Role).filter(Role.id == request.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    existing = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == request.role_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="角色已分配")

    user_role = UserRole(user_id=user_id, role_id=request.role_id)
    db.add(user_role)
    db.commit()

    return {"message": "角色分配成功"}


@router.get("/roles")
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get role list"""
    has_perm = db.query(Permission).join(
        Role.permissions
    ).join(Role.users).filter(
        User.id == current_user.id,
        Permission.name == "role:manage"
    ).first()

    if not has_perm:
        raise HTTPException(status_code=403, detail="权限不足")

    roles = db.query(Role).all()
    return {
        "roles": [
            {
                "id": r.id,
                "name": r.name,
                "display_name": r.display_name,
                "description": r.description
            }
            for r in roles
        ]
    }
