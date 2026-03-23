"""
WebAskHuman - Web-aware replacement for OpenManus AskHuman tool.

Instead of blocking on input(), this tool:
1. Broadcasts an ask_human message via WebSocket to the frontend
2. Polls Redis for the answer (written by POST /api/design/{task_id}/respond)
3. Returns the answer when received, or raises TimeoutError
"""
import asyncio
from app.tool import BaseTool


class WebAskHuman(BaseTool):
    """AskHuman tool that communicates via WebSocket + Redis instead of stdin."""

    name: str = "ask_human"
    description: str = "Use this tool to ask human for help."
    parameters: dict = {
        "type": "object",
        "properties": {
            "inquire": {
                "type": "string",
                "description": "The question you want to ask human.",
            }
        },
        "required": ["inquire"],
    }

    # Injected at runtime by PlanningFlow
    task_id: str = ""
    websocket_callback: object = None  # async callable
    redis_url: str = "redis://localhost:6379/0"
    timeout: int = 300  # seconds to wait for user response

    class Config:
        arbitrary_types_allowed = True

    async def execute(self, inquire: str) -> str:
        """
        Broadcast question via WebSocket, then poll Redis for the answer.
        Falls back to empty string on timeout.
        """
        # Parse question and options from inquire string
        question, options = self._parse_inquire(inquire)

        # Broadcast ask_human event to frontend
        if self.websocket_callback and self.task_id:
            await self.websocket_callback({
                "type": "ask_human",
                "question": question,
                "options": options,
                "default": options[0] if options else ""
            })

        # If no task_id/redis configured, fall back to empty
        if not self.task_id:
            return ""

        # Poll Redis for answer
        answer = await self._wait_for_answer()
        return answer

    def _parse_inquire(self, inquire: str) -> tuple[str, list[str]]:
        """Extract question text and options list from inquire string."""
        lines = inquire.strip().splitlines()
        question_lines = []
        options = []

        for line in lines:
            stripped = line.strip()
            # Detect option lines like "1. xxx", "- xxx", "* xxx"
            if stripped and (
                (stripped[0].isdigit() and len(stripped) > 2 and stripped[1] in '.)')
                or stripped.startswith(('- ', '* ', '• '))
            ):
                opt = stripped.lstrip('0123456789.-*)• ').strip()
                if opt:
                    options.append(opt)
            else:
                question_lines.append(line)

        question = '\n'.join(question_lines).strip() or inquire.strip()
        return question, options

    async def _wait_for_answer(self) -> str:
        """Poll Redis every second until answer appears or timeout."""
        try:
            import redis.asyncio as aioredis
        except ImportError:
            import aioredis  # type: ignore

        redis_key = f"ask_human:{self.task_id}"
        client = aioredis.from_url(self.redis_url, decode_responses=True)

        try:
            elapsed = 0
            while elapsed < self.timeout:
                answer = await client.get(redis_key)
                if answer is not None:
                    await client.delete(redis_key)
                    return answer
                await asyncio.sleep(1)
                elapsed += 1
        finally:
            await client.aclose()

        return ""  # timeout — return empty, agent will handle gracefully
