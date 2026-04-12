"""
API Configuration
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    API_TITLE: str = "OpenManus Structural Design API"
    API_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours for development
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://localhost/structural_design"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # File Storage
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./output")

    class Config:
        env_file = ".env"
        extra = "ignore"  # 忽略未定义的环境变量


settings = Settings()
