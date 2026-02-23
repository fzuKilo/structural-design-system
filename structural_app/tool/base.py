"""
Base classes for tools in structural-app
Imports BaseTool and ToolResult from OpenManus (app.tool.base)
"""

try:
    from app.tool.base import BaseTool, ToolResult
except ImportError:
    # Fallback for different OpenManus installation paths
    from openmanus.app.tool.base import BaseTool, ToolResult

__all__ = ['BaseTool', 'ToolResult']
