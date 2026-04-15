"""
Authentication Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from backend.database import get_db, User
from backend.api.models import (
    UserRegister, UserLogin, TokenResponse, UserResponse, UpdateProfile
)
from backend.api.services import (
    verify_password, get_password_hash, create_access_token, encrypt_api_key
)
from backend.api.middleware import get_current_user
from backend.api.config import settings

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """用户注册"""
    # Check if username exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # Check if email exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(User.username == user_data.username).first()

    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """获取用户信息"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        quota_daily=current_user.quota_daily,
        quota_monthly=current_user.quota_monthly,
        created_at=current_user.created_at,
        roles=[role.name for role in current_user.roles],
        has_api_key=bool(current_user.api_key_encrypted)
    )


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_data: UpdateProfile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    if profile_data.api_key:
        # 验证 Key 格式（DeepSeek/OpenAI Key 以 sk- 开头）
        if not profile_data.api_key.startswith("sk-"):
            raise HTTPException(
                status_code=400,
                detail="API Key 格式无效，应以 sk- 开头"
            )
        # Encrypt API key before storing
        try:
            current_user.api_key_encrypted = encrypt_api_key(profile_data.api_key)
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail=f"加密API Key失败: {str(e)}"
            )

    db.commit()
    db.refresh(current_user)
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        quota_daily=current_user.quota_daily,
        quota_monthly=current_user.quota_monthly,
        created_at=current_user.created_at,
        roles=[role.name for role in current_user.roles],
        has_api_key=bool(current_user.api_key_encrypted)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """刷新访问令牌"""
    access_token = create_access_token(
        data={"sub": current_user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
