"""
Design Task - Celery task to run PlanningFlow
"""
import sys
import os
import json

# OpenManus is installed as a package via pip, no manual path needed

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

        # Persist key state to DB immediately so page navigation doesn't lose data
        msg_type = message.get("type")
        try:
            with get_db_context() as db:
                t = db.query(Task).filter(Task.id == task_id).first()
                if not t:
                    return
                rj = dict(t.result_json) if t.result_json else {}

                # Persist interaction_history on every answer
                if msg_type == "interaction_history" and message.get("interaction_history"):
                    rj["interaction_history"] = message["interaction_history"]
                    t.result_json = rj
                    db.commit()

                # Persist completed stage data so rebuildStagesFromResult works on re-entry
                elif msg_type == "stage" and message.get("status") in ("completed", "skipped"):
                    stage = message.get("stage")
                    stages_snapshot = rj.get("stages_snapshot", {})
                    stages_snapshot[stage] = message.get("data", {})
                    rj["stages_snapshot"] = stages_snapshot
                    t.result_json = rj
                    db.commit()

        except Exception as e:
            print(f"[WARN] Failed to persist state: {e}")

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
    import redis

    # Create Redis client inside function scope
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    # Create async wrapper for sync callback
    async def ws_callback(message: dict):
        """Async wrapper that calls sync Redis publish"""
        ws_callback_sync(message)

    # Set OpenManus config path
    os.environ['OPENMANUS_CONFIG_DIR'] = '/app'

    with get_db_context() as db:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        # Check if already cancelled before starting
        if redis_client.exists(f"cancel:{task_id}") or task.status == "failed":
            print(f"[INFO] Task {task_id} was cancelled, skipping")
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

            # Decrypt API key
            from backend.api.services.encryption_service import decrypt_api_key
            plain_api_key = decrypt_api_key(user.api_key_encrypted)

            # Create LLM instance with user's API key (unique config_name bypasses singleton cache)
            from app.llm import LLM
            from app.config import LLMSettings
            config_key = f"user_{task_id}"
            user_llm_config = LLMSettings(
                model="deepseek-chat",
                base_url="https://api.deepseek.com/v1",
                api_key=plain_api_key,
                api_type="openai",
                api_version="",
                max_tokens=4000,
                temperature=0.7,
            )
            user_llm = LLM(config_name=config_key, llm_config={config_key: user_llm_config, "default": user_llm_config})

            # Create agents with user's LLM instance
            from structural_app.agent.structural_design_agent import StructuralDesignAgent
            from structural_app.agent.fe_analysis_agent import FEAnalysisAgent
            from structural_app.agent.cad_drawing_agent import CADDrawingAgent
            from structural_app.agent.evaluation_agent import EvaluationAgent
            from structural_app.agent.report_generation_agent import ReportGenerationAgent

            # Create WebAskHuman tool first
            from structural_app.tool.web_ask_human import WebAskHuman
            web_ask_human = WebAskHuman(
                task_id=task_id,
                websocket_callback=ws_callback,
                redis_url=settings.REDIS_URL,
            )

            design_agent = StructuralDesignAgent(tools=[web_ask_human], llm=user_llm)
            analysis_agent = FEAnalysisAgent(tools=[web_ask_human], llm=user_llm)
            drawing_agent = CADDrawingAgent(tools=[web_ask_human], llm=user_llm)
            evaluation_agent = EvaluationAgent(tools=[web_ask_human], llm=user_llm)
            report_agent = ReportGenerationAgent(tools=[web_ask_human], llm=user_llm)

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

            # Override PlanningFlow's api_key with user's key (it loads from config.toml by default)
            flow.api_key = plain_api_key
            flow.api_base_url = "https://api.deepseek.com/v1"
            flow.api_model = "deepseek-chat"

            # Run workflow with cancellation monitor
            async def cancel_monitor():
                """Poll Redis every 2s for cancellation signal"""
                while True:
                    await asyncio.sleep(2)
                    if redis_client.exists(f"cancel:{task_id}"):
                        raise asyncio.CancelledError("用户停止，工作流终止")

            workflow_task = asyncio.create_task(flow.run_full_design(user_request))
            monitor_task = asyncio.create_task(cancel_monitor())

            try:
                done, pending = await asyncio.wait(
                    [workflow_task, monitor_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                for t in pending:
                    t.cancel()

                if monitor_task in done:
                    raise Exception("用户停止，工作流终止")

                result = workflow_task.result()
            except asyncio.CancelledError:
                raise Exception("用户停止，工作流终止")

            # Extract actual visualization paths from output directory
            import glob
            output_dir = result.get("main_output_dir", "")
            vis_dir = os.path.join(output_dir, "visualizations")

            actual_visualizations = {"static": {}, "interactive": {}}
            if os.path.exists(vis_dir):
                # Static images
                for png in glob.glob(os.path.join(vis_dir, "*.png")):
                    basename = os.path.basename(png)
                    if "displacement_cloud" in basename or ("displacement" in basename and "cloud" in basename):
                        actual_visualizations["static"]["displacement_contour"] = png
                    elif "moment_cloud" in basename:
                        actual_visualizations["static"]["moment_contour"] = png
                    elif "stress_cloud" in basename:
                        actual_visualizations["static"]["stress_contour"] = png
                    elif "moment_diagram" in basename:
                        actual_visualizations["static"]["moment_diagram"] = png
                    # Frame-specific filenames: frame_displacement_*.png, frame_moment_*.png, frame_story_drift_*.png
                    elif basename.startswith("frame_displacement"):
                        actual_visualizations["static"]["displacement_contour"] = png
                    elif basename.startswith("frame_moment"):
                        actual_visualizations["static"]["moment_contour"] = png
                    elif basename.startswith("frame_story_drift"):
                        actual_visualizations["static"]["story_drift"] = png
                    # Truss-specific: truss_topology_*.png
                    elif "topology" in basename:
                        actual_visualizations["static"]["topology"] = png

                # Interactive HTML
                for html in glob.glob(os.path.join(vis_dir, "*.html")):
                    basename = os.path.basename(html)
                    if "displacement" in basename:
                        actual_visualizations["interactive"]["displacement_html"] = html
                    elif "moment" in basename:
                        actual_visualizations["interactive"]["moment_html"] = html
                    elif "stress" in basename:
                        actual_visualizations["interactive"]["stress_html"] = html

            # 从 Redis list 读取 WebAskHuman 记录的交互历史，合并 planning_flow 记录的历史
            web_ask_history_raw = redis_client.lrange(f"interaction_history:{task_id}", 0, -1)
            web_ask_history = [json.loads(x) for x in web_ask_history_raw] if web_ask_history_raw else []
            redis_client.delete(f"interaction_history:{task_id}")
            redis_client.delete(f"current_stage:{task_id}")

            # 合并两个来源：planning_flow._ask_web_or_cli 记录的 + WebAskHuman 记录的
            planning_flow_history = result.get("interaction_history", [])
            interaction_history = planning_flow_history + web_ask_history

            # 调试日志
            print(f"[DEBUG] planning_flow_history count: {len(planning_flow_history)}")
            print(f"[DEBUG] web_ask_history count: {len(web_ask_history)}")
            print(f"[DEBUG] Total interaction_history count: {len(interaction_history)}")
            if interaction_history:
                print(f"[DEBUG] Stages in history: {[item.get('stage') for item in interaction_history]}")

            # Pick first static PNG as preview_image
            static_viz = actual_visualizations.get("static", {})
            preview_image = ""
            for v in static_viz.values():
                if isinstance(v, str) and v.endswith(".png"):
                    preview_image = v.replace("\\", "/")
                    break

            # Flatten result structure for frontend compatibility
            flattened_result = {
                "report_file": (result.get("report_results") or {}).get("report_file", "").replace("\\", "/") if (result.get("report_results") or {}).get("report_file") else "",
                "files": {k: v.replace("\\", "/") if isinstance(v, str) else v for k, v in (result.get("drawing_results") or {}).get("files", {}).items()},
                "drawing_previews": {k: v.replace("\\", "/") for k, v in (result.get("drawing_results") or {}).get("metadata", {}).items() if isinstance(v, str) and v.endswith(".png")},
                "visualizations": {
                    "static": {k: v.replace("\\", "/") if isinstance(v, str) else v for k, v in actual_visualizations.get("static", {}).items()},
                    "interactive": {k: v.replace("\\", "/") if isinstance(v, str) else v for k, v in actual_visualizations.get("interactive", {}).items()}
                },
                "preview_image": preview_image,
                "evaluation": result.get("evaluation_report"),
                "bim_url": (result.get("bim_results") or {}).get("url") or (result.get("bim_results") or {}).get("embed_url"),
                "ifc_path": (result.get("ifc_results") or {}).get("path", "").replace("\\", "/").replace("C:/Users/86177/projects/structural-design-system/", "") if (result.get("ifc_results") or {}).get("path") else "",
                "interaction_history": interaction_history,
                "raw": result
            }

            # Update task with results
            task.status = "success"
            task.result_json = flattened_result
            db.commit()

            # Broadcast completion
            await ws_callback({
                "type": "result",
                "status": "success",
                "data": result
            })

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            db.commit()

            is_cancelled = "用户停止" in str(e)
            await ws_callback({
                "type": "cancelled" if is_cancelled else "error",
                "error_code": "USER_CANCELLED" if is_cancelled else "WORKFLOW_FAILED",
                "message": str(e) if is_cancelled else f"设计流程失败: {str(e)}"
            })
