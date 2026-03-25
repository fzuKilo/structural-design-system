"""
WebSocket Routes
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from backend.api.services import ws_manager, decode_token

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/design/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str, token: str = Query(...)):
    """WebSocket 连接端点"""
    payload = decode_token(token)
    if not payload:
        await websocket.accept()
        await websocket.close(code=1008)
        return

    await ws_manager.connect(task_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(task_id, websocket)
