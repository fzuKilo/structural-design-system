"""
Design Task Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import redis
from backend.database import get_db, User, Task
from backend.api.models import (
    DesignCreateRequest, AskHumanResponse, TaskResponse, TaskDetailResponse, MessageResponse
)
from backend.api.middleware import get_current_user
from backend.tasks.design_task import run_design_task
from backend.api.config import settings

_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

router = APIRouter(prefix="/design", tags=["设计任务"])


@router.post("/create", response_model=TaskResponse)
async def create_design(
    request: DesignCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建设计任务"""
    task = Task(
        user_id=current_user.id,
        request_text=request.request_text,
        status="pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Queue Celery task
    run_design_task.delay(str(task.id), request.request_text)

    return task


@router.get("/list", response_model=List[TaskResponse])
async def list_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """列出用户的任务"""
    tasks = db.query(Task).filter(Task.user_id == current_user.id).order_by(Task.created_at.desc()).all()
    return tasks


@router.get("/{task_id}/status", response_model=TaskDetailResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务状态"""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.post("/{task_id}/respond", response_model=MessageResponse)
async def respond_ask_human(
    task_id: str,
    body: AskHumanResponse,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """响应 AskHuman 问题，将答案写入 Redis 供 Celery 任务读取"""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status != "running":
        raise HTTPException(status_code=400, detail="任务当前不在等待输入状态")

    redis_key = f"ask_human:{task_id}"
    _redis.set(redis_key, body.answer, ex=300)
    return MessageResponse(message="已提交回答")


@router.delete("/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除任务"""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    db.delete(task)
    db.commit()
    return MessageResponse(message="任务已删除")
