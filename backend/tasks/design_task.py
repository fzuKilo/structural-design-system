"""
Design Task - Celery task to run PlanningFlow
"""
import sys
import os
import json

# Add OpenManus to Python path
openmanus_path = r"C:\Users\86177\Desktop\OpenManus"
if openmanus_path not in sys.path:
    sys.path.insert(0, openmanus_path)

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
    print(f"[DEBUG] Starting task {task_id} with request: {user_request}")

    # Create Redis client for publishing messages
    import redis
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    # Create synchronous callback for WebSocket (publish to Redis)
    def websocket_callback_sync(message: dict):
        """Synchronous callback that publishes to Redis"""
        channel = f"task:{task_id}"
        redis_client.publish(channel, json.dumps(message))
        print(f"[DEBUG] Published message to Redis: {message}")

    # Run async workflow
    try:
        asyncio.run(_run_workflow(task_id, user_request, websocket_callback_sync))
        print(f"[DEBUG] Task {task_id} completed successfully")
    except Exception as e:
        print(f"[ERROR] Task {task_id} failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


async def _run_workflow(task_id: str, user_request: str, ws_callback_sync):
    """Run the actual workflow"""
    import os

    # Create async wrapper for sync callback
    async def ws_callback(message: dict):
        """Async wrapper that calls sync Redis publish"""
        ws_callback_sync(message)

    # Set OpenManus config path to avoid "No configuration file found" error
    os.environ['OPENMANUS_CONFIG_DIR'] = 'C:/Users/86177/projects/structural-design-system'

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

            # Get user's API key from database
            user = task.user
            if not user.api_key_encrypted:
                raise Exception("用户未配置 API Key，请在个人设置中添加")

            # Create agents with user's API config
            from structural_app.agent.structural_design_agent import StructuralDesignAgent
            from structural_app.agent.fe_analysis_agent import FEAnalysisAgent
            from structural_app.agent.cad_drawing_agent import CADDrawingAgent
            from structural_app.agent.evaluation_agent import EvaluationAgent
            from structural_app.agent.report_generation_agent import ReportGenerationAgent

            # API configuration from user settings
            api_config = {
                "api_key": user.api_key_encrypted,  # TODO: decrypt if encrypted
                "provider": "openai",
                "base_url": "https://api.deepseek.com/v1",
                "model": "deepseek-chat"
            }

            # Initialize agents with API config
            design_agent = StructuralDesignAgent(**api_config)
            analysis_agent = FEAnalysisAgent(**api_config)
            drawing_agent = CADDrawingAgent(**api_config)
            evaluation_agent = EvaluationAgent(**api_config)
            report_agent = ReportGenerationAgent(**api_config)

            # Initialize PlanningFlow with pre-configured agents
            flow = PlanningFlow(
                design_agent=design_agent,
                analysis_agent=analysis_agent,
                drawing_agent=drawing_agent,
                evaluation_agent=evaluation_agent,
                report_agent=report_agent,
                websocket_callback=ws_callback,
                task_id=task_id,
                redis_url=settings.REDIS_URL,
            )

            # Manually inject WebAskHuman since agents were created before PlanningFlow
            flow._inject_web_ask_human()

            # Run workflow
            result = await flow.run_full_design(user_request)

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
