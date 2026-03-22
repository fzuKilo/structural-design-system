"""
WebSocket Routes
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from uuid import UUID
from backend.api.services import ws_manager, decode_token

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/design/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: UUID, token: str = Query(...)):
    """WebSocket 连接端点"""
    # Verify token
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=1008)
        return

    task_id_str = str(task_id)
    await ws_manager.connect(task_id_str, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong or other messages if needed
    except WebSocketDisconnect:
        ws_manager.disconnect(task_id_str, websocket)
