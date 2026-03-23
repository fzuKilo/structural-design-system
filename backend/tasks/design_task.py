"""
Design Task - Celery task to run PlanningFlow
"""
import asyncio
from backend.tasks.celery_app import celery_app
from backend.database import get_db_context, Task
from backend.api.services import ws_manager
from backend.api.config import settings
from structural_app.planning_flow import PlanningFlow


@celery_app.task
def run_design_task(task_id: str, user_request: str):
    """
    Run design workflow in background

    Args:
        task_id: Task UUID
        user_request: User's design request text
    """
    # Create async callback for WebSocket
    async def websocket_callback(message: dict):
        await ws_manager.broadcast(task_id, message)

    # Run async workflow
    asyncio.run(_run_workflow(task_id, user_request, websocket_callback))


async def _run_workflow(task_id: str, user_request: str, ws_callback):
    """Run the actual workflow"""
    with get_db_context() as db:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        try:
            # Update status to running
            task.status = "running"
            db.commit()

            # Broadcast started
            await ws_callback({
                "type": "stage",
                "stage": "design_proposal",
                "status": "started",
                "message": "开始生成设计方案"
            })

            # Initialize PlanningFlow with WebSocket callback and task_id for WebAskHuman
            flow = PlanningFlow(
                websocket_callback=ws_callback,
                task_id=task_id,
                redis_url=settings.REDIS_URL,
            )

            # Run workflow
            result = await flow.run(user_request)

            # Update task with results
            task.status = "success"
            task.result_json = result
            db.commit()

            # Broadcast completion
            await ws_callback({
                "type": "result",
                "status": "success",
                "data": result
            })

        except Exception as e:
            task.status = "failed"
            db.commit()

            # Broadcast error
            await ws_callback({
                "type": "error",
                "error_code": "WORKFLOW_FAILED",
                "message": f"设计流程失败: {str(e)}"
            })
