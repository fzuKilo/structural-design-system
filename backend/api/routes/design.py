"""
Design Task Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from backend.database import get_db, User, Task
from backend.api.models import (
    DesignCreateRequest, TaskResponse, TaskDetailResponse, MessageResponse
)
from backend.api.middleware import get_current_user
from backend.tasks.design_task import run_design_task

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
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务状态"""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.delete("/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: UUID,
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
