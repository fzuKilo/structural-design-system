import asyncio
import base64
import os
import sys

import pytest

# Ensure repository root is on sys.path so `app` package can be imported during tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agent.toolcall import ToolCallAgent
from app.tool.base import BaseTool
from app.tool.tool_collection import ToolCollection
from app.schema import ToolCall, Function


class DummyPythonExecute(BaseTool):
    name: str = "python_execute"
    description: str = "Dummy python execute tool"

    async def execute(self, **kwargs):
        # Echo back received kwargs for test verification
        return self.success_response({"received": kwargs})


def make_agent_with_dummy():
    # Construct without validation to avoid heavy LLM initialization
    agent = ToolCallAgent.construct()
    agent.available_tools = ToolCollection(DummyPythonExecute())
    agent.special_tool_names = ["terminate"]
    agent.memory = agent.memory or None
    return agent


def test_base64_arguments_parsing():
    agent = make_agent_with_dummy()
    code = "print(\"hello\")\nprint(2+2)\n"
    b64 = base64.b64encode(code.encode()).decode()
    inner = {"code_b64": b64, "path": "workspace/run.py"}
    args = pytest.json.dumps(inner) if hasattr(pytest, 'json') else __import__('json').dumps(inner)
    func = Function(name="python_execute", arguments=args)
    call = ToolCall(id="1", function=func)

    out = asyncio.run(agent.execute_tool(call))
    assert "Observed output of cmd `python_execute` executed" in out
    assert 'hello' in out


def test_unescaped_triple_quote_parsing():
    agent = make_agent_with_dummy()
    # Simulate an LLM output that embeds a triple-quoted Python string inside the arguments
    raw = '{"code": """print(\"triple\")\nprint(123)""", "path": "workspace/a.py"}'
    func = Function(name="python_execute", arguments=raw)
    call = ToolCall(id="2", function=func)

    out = asyncio.run(agent.execute_tool(call))
    assert "Observed output of cmd `python_execute` executed" in out
    assert "triple" in out or "123" in out or "received" in out


def test_escaped_newline_parsing():
    agent = make_agent_with_dummy()
    inner = {"code": "print(\"ok\")\\nprint(1)", "path": "workspace/b.py"}
    args = __import__('json').dumps(inner)
    func = Function(name="python_execute", arguments=args)
    call = ToolCall(id="3", function=func)

    out = asyncio.run(agent.execute_tool(call))
    assert "Observed output of cmd `python_execute` executed" in out

