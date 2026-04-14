"""
WebAskHuman - Web-aware replacement for OpenManus AskHuman tool.

Instead of blocking on input(), this tool:
1. Broadcasts an ask_human message via WebSocket to the frontend
2. Polls Redis for the answer (written by POST /api/design/{task_id}/respond)
3. Returns the answer when received, or raises TimeoutError
"""
import asyncio
from app.tool import BaseTool
from app.tool.ask_human import AskHuman


class WebAskHuman(AskHuman):
    """AskHuman tool that communicates via WebSocket + Redis instead of stdin."""

    name: str = "ask_human"
    description: str = "Use this tool to ask human for help. Supports both structured parameters and legacy text format."
    parameters: dict = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question text to ask the user.",
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of choices for the user to select from. If provided, the frontend will display radio buttons instead of free text input.",
            },
            "context": {
                "type": "object",
                "description": "Optional context information (e.g., warnings, scores, image paths) to display alongside the question.",
            },
            "inquire": {
                "type": "string",
                "description": "Legacy parameter: full text containing question and options. Use 'question' + 'options' instead for better reliability.",
            }
        },
        "required": [],
    }

    # Injected at runtime by PlanningFlow
    task_id: str = ""
    websocket_callback: object = None  # async callable
    redis_url: str = "redis://localhost:6379/0"
    timeout: int = 300  # seconds to wait for user response

    class Config:
        arbitrary_types_allowed = True

    async def execute(self, question: str = None, options: list = None, context: dict = None, inquire: str = None) -> str:
        """
        Broadcast question via WebSocket, then poll Redis for the answer.

        Supports two modes:
        1. Structured parameters (recommended): question, options, context
        2. Legacy text format: inquire (will be parsed)

        Args:
            question: The question text to display
            options: List of option strings for radio button selection
            context: Additional context (warnings, scores, image_path, etc.)
            inquire: Legacy parameter - full text containing question and options

        Returns:
            User's answer as a string
        """
        print(f"[WebAskHuman] execute() called with question={question is not None}, options={options}, context={context is not None}, inquire={inquire is not None}")
        print(f"[WebAskHuman] task_id={self.task_id}, has_callback={self.websocket_callback is not None}")

        # Mode 1: Structured parameters (preferred)
        if question is not None:
            clean_question = question
            final_options = options if options else []
            final_context = context if context else {}

            # Extract image path from context if present
            image_path = final_context.get('image_path', '')

        # Mode 2: Legacy text parsing (fallback for backward compatibility)
        elif inquire is not None:
            # Extract image path from inquire text if present
            image_path = self._extract_image_path(inquire)

            # Parse structured context from inquire text
            final_context = self._parse_context(inquire)

            # Parse options from inquire text (this also extracts the question)
            parsed_question, final_options = self._parse_inquire(inquire)

            # Clean up the question text for display
            clean_question = self._clean_question_text(parsed_question)

            # Add image path to context if found
            if image_path:
                final_context['image_path'] = image_path
        else:
            raise ValueError("Either 'question' or 'inquire' parameter must be provided")

        # Broadcast ask_human event to frontend
        if self.websocket_callback and self.task_id:
            print(f"[WebAskHuman] Broadcasting ask_human message via WebSocket")
            message = {
                "type": "ask_human",
                "question": clean_question,
                "options": final_options,
                "default": final_options[0] if final_options else ""
            }

            # Add image path if present in context
            if final_context.get('image_path'):
                message["image_path"] = final_context['image_path']
                print(f"[WebAskHuman] Including image: {final_context['image_path']}")

            # Add context (excluding image_path as it's already added separately)
            context_without_image = {k: v for k, v in final_context.items() if k != 'image_path'}
            if context_without_image:
                message["context"] = context_without_image
                print(f"[WebAskHuman] Including context: {list(context_without_image.keys())}")

            await self.websocket_callback(message)
        else:
            print(f"[WebAskHuman] WARNING: Cannot broadcast - missing task_id or callback")

        # If no task_id/redis configured, fall back to empty
        if not self.task_id:
            return ""

        # Poll Redis for answer
        answer = await self._wait_for_answer()
        print(f"[WebAskHuman] Received answer: {answer}")
        return answer

    def _extract_image_path(self, inquire: str) -> str:
        """Extract image path from inquire text."""
        import re
        # Look for new format: "IMAGE_PATH:path"
        match = re.search(r'IMAGE_PATH:\s*([^\n]+)', inquire)
        if match:
            path = match.group(1).strip()
            # Convert Windows path to forward slashes
            path = path.replace('\\', '/')
            return path
        # Fallback: old format "模型示意图已保存至：path" or "已保存至：path"
        match = re.search(r'(?:模型示意图)?已保存至[：:]\s*([^\n]+)', inquire)
        if match:
            path = match.group(1).strip()
            path = path.replace('\\', '/')
            return path
        return ""

    def _clean_question_text(self, inquire: str) -> str:
        """Clean up question text for user-friendly display."""
        import re
        text = inquire

        # Remove IMAGE_PATH: line
        text = re.sub(r'IMAGE_PATH:[^\n]*\n?', '', text)

        # Remove old format image path lines
        text = re.sub(r'(?:模型示意图)?已保存至[：:][^\n]*\n?', '', text)

        # Remove markdown bold syntax **text**
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)

        # Remove technical prompts like "请输入 (y/n):"
        text = re.sub(r'请输入\s*\([^)]+\)[：:]\s*$', '', text)

        # Remove option lines like "y - xxx" or "n - xxx"
        text = re.sub(r'\n\s*[yn]\s*-\s*[^\n]+', '', text)

        # Remove numbered option lines like "1 - continue : xxx", "2 - optimize : xxx"
        # But keep question numbering like "1. 材料类型：xxx"
        # Pattern: digit + dash + word (option key) + optional colon + description
        text = re.sub(r'\n\s*\d+\s*[-–—]\s*\w+\s*[:：][^\n]*', '', text)

        # Remove separator lines (=== or ---)
        text = re.sub(r'\n\s*[=\-]{3,}\s*\n', '\n', text)

        # Remove comparison tables (lines with multiple columns separated by spaces/tabs)
        lines = text.split('\n')
        filtered_lines = []
        for line in lines:
            # Skip lines that look like table headers or data rows
            if re.search(r'(原方案|方案\d|截面|材料|应力|位移|经济性|结构效率|安全性|可持续性|综合得分|等级|推荐方案)', line):
                continue
            filtered_lines.append(line)
        text = '\n'.join(filtered_lines)

        # Clean up extra whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        return text

    def _parse_context(self, inquire: str) -> dict:
        """Parse structured context from inquire text."""
        import re
        context = {}

        # Extract warnings (严重/不合格 patterns)
        warnings = []
        warning_patterns = [
            r'\[严重\]\s*([^\n]+)',
            r'\[不合格\]\s*([^\n]+)',
            r'⚠️\s*([^\n]+)',
        ]
        for pattern in warning_patterns:
            matches = re.findall(pattern, inquire)
            warnings.extend(matches)

        if warnings:
            context['warnings'] = warnings

        # Extract score and grade
        score_match = re.search(r'综合得分[：:]\s*([\d.]+)', inquire)
        if score_match:
            context['score'] = float(score_match.group(1))

        grade_match = re.search(r'等级[：:]\s*([A-F][+]?)', inquire)
        if grade_match:
            context['grade'] = grade_match.group(1)

        # Extract comparison table for multi-proposal scenario
        if '原方案' in inquire or '方案1' in inquire:
            proposals = self._parse_proposal_table(inquire)
            if proposals:
                context['proposals'] = proposals

        # Extract recommendation
        recommend_match = re.search(r'[★⭐]\s*推荐方案[：:]\s*([^\n]+)', inquire)
        if recommend_match:
            context['recommendation'] = recommend_match.group(1).strip()

        return context

    def _parse_proposal_table(self, inquire: str) -> list:
        """Parse proposal comparison table from inquire text."""
        import re
        proposals = []

        # Find all proposal columns (原方案, 方案1, 方案2, 方案3)
        proposal_names = re.findall(r'(原方案|方案\d[★⭐]?)', inquire)
        if not proposal_names:
            return proposals

        # Extract key metrics for each proposal
        lines = inquire.split('\n')

        # Initialize proposal data structures
        for name in proposal_names:
            proposals.append({
                'name': name.replace('★', '').replace('⭐', '').strip(),
                'recommended': '★' in name or '⭐' in name,
                'metrics': {}
            })

        # Parse metrics from table rows
        metric_patterns = {
            'section': r'截面\s*\(m\)',
            'material': r'材料',
            'stress': r'应力\s*\(MPa\)',
            'displacement': r'位移\s*\(mm\)',
            'economy': r'经济性',
            'efficiency': r'结构效率',
            'safety': r'安全性',
            'sustainability': r'可持续性',
            'total_score': r'综合得分',
            'grade': r'等级',
        }

        for line in lines:
            for metric_key, pattern in metric_patterns.items():
                if re.search(pattern, line):
                    # Extract values for each proposal
                    # Remove the metric name part
                    values_part = re.sub(pattern, '', line).strip()
                    # Split by whitespace (multiple spaces/tabs)
                    values = re.split(r'\s{2,}', values_part)

                    # Assign values to proposals
                    for i, value in enumerate(values):
                        if i < len(proposals) and value.strip():
                            proposals[i]['metrics'][metric_key] = value.strip()

        return proposals if proposals else []

    def _parse_inquire(self, inquire: str) -> tuple[str, list[str]]:
        """Extract question text and options list from inquire string.

        Only recognizes explicit option formats like:
        - "1 - continue : description"
        - "2 - optimize : description"

        Does NOT recognize plain numbered lists like:
        - "1. 跨度（长度）是多少米？"
        - "2. 承受什么荷载？"
        """
        import re
        lines = inquire.strip().splitlines()
        question_lines = []
        options = []

        for line in lines:
            stripped = line.strip()
            # Only match explicit option format: "数字 - 关键词" or "数字 - 关键词 : 描述"
            # Examples: "1 - continue", "2 - optimize : 尝试自动优化", "1- Q235钢材（描述）"
            # Match: digit(s) + optional spaces + dash + optional spaces + any content
            option_match = re.match(r'^(\d+)\s*[-–—]\s*(.+)$', stripped)
            if option_match:
                # Extract the full option text
                options.append(stripped)
            else:
                # Not an option, keep as question text
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
