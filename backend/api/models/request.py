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
    request_text: str = Field(..., min_length=1, max_length=5000)
    # Experiment mode for the paper's baseline/ablation configurations.
    # None/"B4" = full closed loop (default web behavior, unchanged).
    # "B3"/"A1" = skip Node1 repair (continue to evaluation); "A2" = disable Node2;
    # "A3" = disable RAG clause retrieval; "A4" = drop g(s) optimization constraints.
    exp_mode: Optional[str] = None


class AskHumanResponse(BaseModel):
    """Response to AskHuman question"""
    answer: str


class UpdateProfile(BaseModel):
    """Update user profile"""
    api_key: Optional[str] = None
