"""
WebSocket Manager with Redis Pub/Sub
"""
from typing import Dict, List
from fastapi import WebSocket
import json
import redis
import asyncio


class WebSocketManager:
    """Manage WebSocket connections with Redis Pub/Sub"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.pubsub = None

    async def connect(self, task_id: str, websocket: WebSocket):
        """Connect a WebSocket and start listening to Redis"""
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)

        # Start Redis listener for this task if not already started
        if len(self.active_connections[task_id]) == 1:
            asyncio.create_task(self._listen_redis(task_id))

    def disconnect(self, task_id: str, websocket: WebSocket):
        """Disconnect a WebSocket"""
        if task_id in self.active_connections:
            if websocket in self.active_connections[task_id]:
                self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

    async def broadcast(self, task_id: str, message: dict):
        """Broadcast message to all connections for a task"""
        if task_id in self.active_connections:
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

    def publish(self, task_id: str, message: dict):
        """Publish message to Redis (for Celery Worker)"""
        channel = f"task:{task_id}"
        self.redis_client.publish(channel, json.dumps(message))

    async def _listen_redis(self, task_id: str):
        """Listen to Redis pub/sub for a task (non-blocking)"""
        import asyncio

        channel = f"task:{task_id}"
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(channel)

        try:
            while task_id in self.active_connections:
                # Non-blocking check for messages
                message = pubsub.get_message(ignore_subscribe_messages=True)
                if message and message['type'] == 'message':
                    data = json.loads(message['data'])
                    await self.broadcast(task_id, data)

                # Small delay to avoid busy loop
                await asyncio.sleep(0.1)
        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()


# Global WebSocket manager instance
ws_manager = WebSocketManager()

