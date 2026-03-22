"""
Request Models
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserRegister(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    """User login request"""
    username: str
    password: str


class DesignCreateRequest(BaseModel):
    """Design task creation request"""
    request_text: str = Field(..., min_length=10, max_length=5000)


class AskHumanResponse(BaseModel):
    """Response to AskHuman question"""
    answer: str


class UpdateProfile(BaseModel):
    """Update user profile"""
    api_key: Optional[str] = None
