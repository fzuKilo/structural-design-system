import asyncio
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.schema import Function, ToolCall
from app.agent.toolcall import ToolCallAgent
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.tool_collection import ToolCollection

async def main():
    agent = ToolCallAgent()
    # Ensure tool is available
    agent.available_tools = ToolCollection(StrReplaceEditor())

    # Use encode_args to simulate safer upstream encoding
    from app.utils.arg_serialization import encode_args

    raw_args = encode_args({
        "command": "create",
        "path": "D:/openmanus/workspace/construction_management.html",
        "file_text": "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>建筑工地管理系统</title>\n    <style>\n        * {\n            margin: 0;\n            padding: 0;\n            box-sizing: border-box;\n            font-family: 'Segoe UI', 'Microsoft YaHei';\n        }\n    </style>"
    })

    fn = Function(name='str_replace_editor', arguments=raw_args)
    tc = ToolCall(id='test', function=fn)

    result = await agent.execute_tool(tc)
    print('Result from execute_tool:')
    print(result)

if __name__ == '__main__':
    asyncio.run(main())
