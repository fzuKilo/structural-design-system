"""
Response Models
"""
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from uuid import UUID


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User response"""
    id: UUID
    username: str
    email: str
    quota_daily: int
    quota_monthly: int
    created_at: datetime

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    """Task response"""
    id: UUID
    status: str
    request_text: str
    structure_type: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class TaskDetailResponse(TaskResponse):
    """Task detail response with results"""
    result_json: Optional[Any] = None


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    status: str = "success"
