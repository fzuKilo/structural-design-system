"""
Database Models
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, BigInteger, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()


def _uuid_default():
    return str(uuid.uuid4())


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid_default)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    api_key_encrypted = Column(Text, nullable=True)
    quota_daily = Column(Integer, default=100)  # 增加到100次/天
    quota_monthly = Column(Integer, default=1000)  # 增加到1000次/月
    created_at = Column(DateTime, default=datetime.utcnow)

    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")


class Task(Base):
    """Task model"""
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=_uuid_default)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending", index=True)
    celery_task_id = Column(String(255), nullable=True)
    request_text = Column(Text, nullable=False)
    structure_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    result_json = Column(JSON, nullable=True)

    user = relationship("User", back_populates="tasks")
    files = relationship("TaskFile", back_populates="task", cascade="all, delete-orphan")


class TaskFile(Base):
    """Task file model"""
    __tablename__ = "task_files"

    id = Column(String(36), primary_key=True, default=_uuid_default)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="files")
