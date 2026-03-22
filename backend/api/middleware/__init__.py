"""
Middleware Package
"""
from backend.api.middleware.auth import get_current_user

__all__ = ["get_current_user"]
