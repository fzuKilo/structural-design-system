"""
Response Models
"""
from pydantic import BaseModel, field_serializer
from typing import Optional, Any, List
from datetime import datetime
from uuid import UUID


def _to_utc_iso(v: Optional[datetime]) -> Optional[str]:
    """将无时区 datetime（数据库存储的 UTC）序列化为带 Z 后缀的 ISO 字符串，供前端正确解析。"""
    if v is None:
        return None
    return v.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'


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
    roles: List[str] = []
    has_api_key: bool = False  # 是否已配置API Key（不暴露加密值）

    class Config:
        from_attributes = True

    @field_serializer('created_at')
    def serialize_created_at(self, v):
        return _to_utc_iso(v)


class TaskResponse(BaseModel):
    """Task response"""
    id: UUID
    status: str
    request_text: str
    structure_type: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    error: Optional[str] = None

    class Config:
        from_attributes = True

    @field_serializer('created_at', 'completed_at')
    def serialize_datetimes(self, v):
        return _to_utc_iso(v)


class TaskFileResponse(BaseModel):
    """Task file response"""
    id: UUID
    file_type: str
    file_path: str
    file_size: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('created_at')
    def serialize_created_at(self, v):
        return _to_utc_iso(v)


class TaskDetailResponse(TaskResponse):
    """Task detail response with results"""
    result_json: Optional[Any] = None
    files: List[TaskFileResponse] = []

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    status: str = "success"
