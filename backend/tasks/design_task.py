"""
Design Task - Celery task to run PlanningFlow
"""
import sys
import os
import re
import json

# OpenManus is installed as a package via pip, no manual path needed

import asyncio
from backend.tasks.celery_app import celery_app
from backend.database import get_db_context, Task
from backend.api.services import ws_manager
from backend.api.config import settings
from structural_app.planning_flow import PlanningFlow


def _to_relative_path(path: str) -> str:
    """将绝对路径转换为相对路径（去掉任意项目根前缀）。"""
    if not path:
        return ""
    path = path.replace("\\", "/")
    # 匹配 /app/、/root/xxx/、C:/Users/xxx/ 等各种绝对路径前缀，截取 output/ 之后的部分
    match = re.search(r'(output/.+)', path)
    if match:
        return match.group(1)
    # 如果路径不含 output/，但仍是绝对路径，直接返回文件名
    return os.path.basename(path)


@celery_app.task
def run_design_task(task_id: str, user_request: str, exp_mode: str = None):
    """
    Run design workflow in background

    Args:
        task_id: Task UUID
        user_request: User's design request text
        exp_mode: Experiment configuration (None/B4=full loop, B3/A1/A2/A3/A4 baselines/ablations)
    """
    print(f"[DEBUG] Starting task {task_id} (exp_mode={exp_mode}) with request: {user_request}")

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
        asyncio.run(_run_workflow(task_id, user_request, websocket_callback_sync, exp_mode))
        print(f"[DEBUG] Task {task_id} completed successfully")
    except Exception as e:
        print(f"[ERROR] Task {task_id} failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


async def _run_workflow(task_id: str, user_request: str, ws_callback_sync, exp_mode: str = None):
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

            # E4 cross-model override (paper §4.3): when EXP_LLM_* env vars are set on the
            # worker, run B4 with a different backing model instead of DeepSeek. Key comes
            # from EXP_LLM_API_KEY (falls back to the user's stored key). Affects both the
            # agents' LLM and PlanningFlow's own direct calls (flow.api_* below).
            _exp_model = os.environ.get("EXP_LLM_MODEL")
            if _exp_model:
                _llm_model = _exp_model
                _llm_base = os.environ.get("EXP_LLM_BASE_URL", "https://api.deepseek.com/v1")
                _llm_type = os.environ.get("EXP_LLM_API_TYPE", "openai")
                _llm_key = os.environ.get("EXP_LLM_API_KEY") or plain_api_key
            else:
                _llm_model, _llm_base, _llm_type, _llm_key = (
                    "deepseek-chat", "https://api.deepseek.com/v1", "openai", plain_api_key)

            user_llm_config = LLMSettings(
                model=_llm_model,
                base_url=_llm_base,
                api_key=_llm_key,
                api_type=_llm_type,
                api_version="",
                max_tokens=4000,
                temperature=0,
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
            # In experiment mode, skip the interactive model-confirmation step that
            # calls WebAskHuman (which the exp_client cannot reliably answer in time).
            analysis_agent = FEAnalysisAgent(
                tools=[web_ask_human], llm=user_llm,
                enable_visual_validation=(exp_mode is None),
            )
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
                exp_mode=exp_mode,
            )

            # Override PlanningFlow's api_key with user's key (it loads from config.toml by default)
            flow.api_key = _llm_key
            flow.api_base_url = _llm_base
            flow.api_model = _llm_model

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
                "ifc_path": _to_relative_path((result.get("ifc_results") or {}).get("path", "")),
                "interaction_history": interaction_history,
                "raw": result
            }

            # Promote objective metrics to top level for experiment analysis (paper §5.2/§5.3).
            # Sources: evaluation_report.dimensions.{economy,safety}.indicators + code_check.
            try:
                _eval = result.get("evaluation_report") or {}
                _dims = _eval.get("dimensions") or {}
                _econ_ind = (_dims.get("economy") or {}).get("indicators") or {}
                _safe_ind = (_dims.get("safety") or {}).get("indicators") or {}
                _cc = (result.get("analysis_results") or {}).get("code_check") or {}
                _sfs = _cc.get("safety_factors") or {}
                flattened_result["metrics"] = {
                    "exp_mode": result.get("exp_mode"),
                    "llm_model": _llm_model,
                    "compliant": _cc.get("compliant"),
                    "violations_count": len(_cc.get("violations") or []),
                    "comprehensive_score": _eval.get("comprehensive_score"),
                    "dimension_scores": {k: (v or {}).get("score") for k, v in _dims.items()},
                    "material_volume": _econ_ind.get("volume_m3"),
                    "min_safety_factor": _safe_ind.get("min_safety_factor")
                        if _safe_ind.get("min_safety_factor") is not None
                        else (min(_sfs.values()) if _sfs else None),
                    "safety_factors": _sfs,
                    "score_history": result.get("score_history"),
                }
            except Exception as _me:
                print(f"[WARN] Failed to promote metrics: {_me}")

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
            import traceback as _tb
            _full_tb = _tb.format_exc()
            print(f"[ERROR] workflow exception:\n{_full_tb}")
            task.status = "failed"
            task.error = str(e)
            db.commit()

            is_cancelled = "用户停止" in str(e)
            await ws_callback({
                "type": "cancelled" if is_cancelled else "error",
                "error_code": "USER_CANCELLED" if is_cancelled else "WORKFLOW_FAILED",
                "message": str(e) if is_cancelled else f"设计流程失败: {str(e)}"
            })
