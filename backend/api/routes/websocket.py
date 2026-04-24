"""
WebSocket Routes
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from backend.api.services import ws_manager, decode_token
from backend.api.config import settings
from backend.database import get_db_context, Task

router = APIRouter(tags=["WebSocket"])


async def _replay_state(websocket: WebSocket, task_id: str):
    """连接建立后，重放任务当前状态（已完成的 stage + 挂起的 ask_human）"""
    import redis.asyncio as aioredis

    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        # 1. 从数据库重建已完成的 stage 快照
        try:
            with get_db_context() as db:
                task = db.query(Task).filter(Task.id == task_id).first()
                if task and task.status == 'running' and task.result_json:
                    rj = task.result_json or {}
                    raw = rj.get('raw') or {}
                    # Prefer stages_snapshot (written incrementally during execution)
                    # Fallback to raw (written only on completion)
                    snapshot = rj.get('stages_snapshot', {})
                    stage_data_map = {
                        'design_proposal': snapshot.get('design_proposal') or raw.get('design_proposal'),
                        'fe_analysis': snapshot.get('fe_analysis') or raw.get('analysis_results'),
                        'evaluation': snapshot.get('evaluation') or rj.get('evaluation') or raw.get('evaluation_report'),
                        'cad_drawing': snapshot.get('cad_drawing') or raw.get('drawing_results'),
                        'report_generation': snapshot.get('report_generation') or raw.get('report_results'),
                    }
                    for stage_name, data in stage_data_map.items():
                        if data:
                            await websocket.send_json({
                                'type': 'stage',
                                'stage': stage_name,
                                'status': 'completed',
                                'data': data,
                            })

                    # 恢复交互历史
                    history = rj.get('interaction_history')
                    if history:
                        await websocket.send_json({
                            'type': 'interaction_history',
                            'interaction_history': history,
                        })
        except Exception as e:
            print(f"[WebSocket] replay_state stage error: {e}")

        # 2. 推送挂起的 ask_human（独立 try，保证不受上面异常影响）
        try:
            pending = await client.get(f"ask_human_pending:{task_id}")
            if pending:
                msg = json.loads(pending)
                await websocket.send_json(msg)
        except Exception as e:
            print(f"[WebSocket] replay_state ask_human error: {e}")
    finally:
        await client.aclose()


@router.websocket("/ws/design/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str, token: str = Query(...)):
    """WebSocket 连接端点"""
    payload = decode_token(token)
    if not payload:
        await websocket.accept()
        await websocket.close(code=1008)
        return

    await ws_manager.connect(task_id, websocket)
    await _replay_state(websocket, task_id)

    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(task_id, websocket)
