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
from backend.api.middleware import get_current_user, check_quota, deduct_quota
from backend.tasks.design_task import run_design_task
from backend.api.config import settings

_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

router = APIRouter(prefix="/design", tags=["设计任务"])


@router.post("/create", response_model=TaskResponse)
async def create_design(
    request: DesignCreateRequest,
    current_user: User = Depends(check_quota),
    db: Session = Depends(get_db)
):
    """创建设计任务"""
    # 提前检查 API Key，避免任务创建后才报错
    if not current_user.api_key_encrypted:
        raise HTTPException(
            status_code=400,
            detail="请先在个人中心 → API Key 标签页配置您的 API Key"
        )
    task = Task(
        user_id=current_user.id,
        request_text=request.request_text,
        status="pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Deduct quota immediately after task creation
    deduct_quota(current_user, db, task.id)

    # Queue Celery task and save celery_task_id
    celery_result = run_design_task.delay(str(task.id), request.request_text)
    task.celery_task_id = celery_result.id
    db.commit()

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

    return TaskDetailResponse(
        id=task.id,
        status=task.status,
        request_text=task.request_text,
        structure_type=task.structure_type,
        created_at=task.created_at,
        completed_at=task.completed_at,
        result_json=task.result_json,
        files=task.files
    )


@router.get("/{task_id}/pending-ask")
async def get_pending_ask(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查询当前挂起的 ask_human 请求（用于页面重新进入时恢复交互状态）"""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status != "running":
        return {"pending": False, "ask_human": None}

    pending = _redis.get(f"ask_human_pending:{task_id}")
    if pending:
        import json
        return {"pending": True, "ask_human": json.loads(pending)}
    return {"pending": False, "ask_human": None}


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


@router.post("/{task_id}/cancel", response_model=MessageResponse)
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消运行中的任务"""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail="任务不在可取消状态")

    # Revoke Celery task
    if task.celery_task_id:
        from backend.tasks.celery_app import celery_app
        celery_app.control.revoke(task.celery_task_id, terminate=True, signal="SIGTERM")

    # Mark cancelled in DB with error message
    task.status = "failed"
    task.error = "用户停止，工作流终止"
    db.commit()

    # Clean up Redis keys
    _redis.delete(f"ask_human:{task_id}")
    _redis.set(f"cancel:{task_id}", "1", ex=600)

    return MessageResponse(message="任务已取消")


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
