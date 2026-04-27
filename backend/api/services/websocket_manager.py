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
        try:
            import redis.asyncio as aioredis
        except ImportError:
            import aioredis

        channel = f"task:{task_id}"
        # Use the same redis_url from initialization
        redis_url = self.redis_client.connection_pool.connection_kwargs.get('host', 'localhost')
        redis_port = self.redis_client.connection_pool.connection_kwargs.get('port', 6379)
        redis_db = self.redis_client.connection_pool.connection_kwargs.get('db', 0)
        full_url = f"redis://{redis_url}:{redis_port}/{redis_db}"

        client = aioredis.from_url(full_url, decode_responses=True)
        pubsub = client.pubsub()

        try:
            await pubsub.subscribe(channel)
            print(f"[WebSocket] Subscribed to Redis channel: {channel}")

            while task_id in self.active_connections:
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message:
                        print(f"[WebSocket] Received Redis message: type={message.get('type')}, data={message.get('data', '')[:100] if message.get('data') else 'None'}")
                    if message and message['type'] == 'message':
                        data = json.loads(message['data'])
                        print(f"[WebSocket] Parsed data: {data}")
                        if task_id not in self.active_connections:
                            break
                        print(f"[WebSocket] Broadcasting to {len(self.active_connections[task_id])} clients")
                        await self.broadcast(task_id, data)
                except Exception as e:
                    print(f"[WebSocket] Error: {e}")
                    import traceback
                    traceback.print_exc()
                    await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await client.close()


# Global WebSocket manager instance
from backend.api.config import settings
ws_manager = WebSocketManager(redis_url=settings.REDIS_URL)

