"""
Unit tests for AskHuman tool
Tests the tool's schema and execution with mocked input
"""

import sys
import os

# Add OpenManus to path
_openmanus_path = 'D:\\openmanus'
if os.path.exists(_openmanus_path) and _openmanus_path not in sys.path:
    sys.path.insert(0, _openmanus_path)

import pytest
from unittest.mock import patch, MagicMock
from app.tool.ask_human import AskHuman


class TestAskHumanInitialization:
    """Test cases for AskHuman tool initialization"""

    def test_ask_human_exists(self):
        """Test that AskHuman class can be imported"""
        assert AskHuman is not None

    def test_ask_human_has_correct_name(self):
        """Test that AskHuman has the correct name"""
        tool = AskHuman()
        assert tool.name == "ask_human"

    def test_ask_human_has_correct_description(self):
        """Test that AskHuman has the correct description"""
        tool = AskHuman()
        assert tool.description == "Use this tool to ask human for help."

    def test_ask_human_has_correct_parameters(self):
        """Test that AskHuman has the correct parameter schema"""
        tool = AskHuman()
        params = tool.parameters

        assert "type" in params
        assert params["type"] == "object"

        assert "properties" in params
        assert "inquire" in params["properties"]

        assert params["properties"]["inquire"]["type"] == "string"
        assert "description" in params["properties"]["inquire"]

        assert "required" in params
        assert "inquire" in params["required"]


class TestAskHumanExecute:
    """Test cases for AskHuman.execute() method"""

    @pytest.mark.asyncio
    async def test_execute_calls_input_with_query(self):
        """Test that execute() calls input() with the inquiry message"""
        tool = AskHuman()

        # Mock the input function
        with patch('app.tool.ask_human.input') as mock_input:
            mock_input.return_value = "Test response"

            result = await tool.execute(inquire="What is the span?")

            # Verify input was called with the correct message
            mock_input.assert_called_once_with("Bot: What is the span?\n\nYou: ")

            # Verify the result is stripped
            assert result == "Test response"

    @pytest.mark.asyncio
    async def test_execute_strips_whitespace(self):
        """Test that execute() strips leading/trailing whitespace from input"""
        tool = AskHuman()

        with patch('app.tool.ask_human.input') as mock_input:
            mock_input.return_value = "  response with spaces  "

            result = await tool.execute(inquire="Test question")

            assert result == "response with spaces"

    @pytest.mark.asyncio
    async def test_execute_handles_empty_input(self):
        """Test that execute() handles empty input"""
        tool = AskHuman()

        with patch('app.tool.ask_human.input') as mock_input:
            mock_input.return_value = ""

            result = await tool.execute(inquire="Test question")

            assert result == ""

    @pytest.mark.asyncio
    async def test_execute_returns_stripped_newlines(self):
        """Test that execute() strips newlines from input"""
        tool = AskHuman()

        with patch('app.tool.ask_human.input') as mock_input:
            mock_input.return_value = "\n\nresponse\n"

            result = await tool.execute(inquire="Test question")

            assert result == "response"


class TestAskHumanIntegration:
    """Integration tests for AskHuman in StructuralDesignAgent"""

    def test_agent_has_ask_human_tool(self):
        """Test that StructuralDesignAgent automatically includes AskHuman tool"""
        # Add project root to path
        _project_root = os.path.dirname(os.path.dirname(__file__))
        if _project_root not in sys.path:
            sys.path.append(_project_root)

        from structural_app.agent.structural_design_agent import StructuralDesignAgent

        agent = StructuralDesignAgent()

        # Verify AskHuman is in the tools list
        has_ask_human = any(isinstance(tool, AskHuman) for tool in agent.tools)
        assert has_ask_human, "StructuralDesignAgent should include AskHuman tool"
