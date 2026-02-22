"""
Unit tests for CADDrawingAgent
"""

import pytest
import sys
import os

# Add openmanus to path
_openmanus_path = 'D:\\openmanus'
if os.path.exists(_openmanus_path) and _openmanus_path not in sys.path:
    sys.path.insert(0, _openmanus_path)


class TestCADDrawingAgentInitialization:
    """Test cases for CADDrawingAgent initialization"""

    def test_agent_exists(self):
        """Test that CADDrawingAgent class can be imported"""
        from structural_app.agent.cad_drawing_agent import CADDrawingAgent
        assert CADDrawingAgent is not None

    def test_agent_inherits_toolcall_agent(self):
        """Test that CADDrawingAgent inherits from ToolCallAgent"""
        from structural_app.agent.cad_drawing_agent import CADDrawingAgent
        from app.agent.toolcall import ToolCallAgent
        assert issubclass(CADDrawingAgent, ToolCallAgent)

    def test_agent_has_correct_name(self):
        """Test that CADDrawingAgent has the correct default name"""
        from structural_app.agent.cad_drawing_agent import CADDrawingAgent
        agent = CADDrawingAgent()
        assert agent.name == "CADDrawingAgent"

    def test_agent_has_correct_description(self):
        """Test that CADDrawingAgent has the correct description"""
        from structural_app.agent.cad_drawing_agent import CADDrawingAgent
        agent = CADDrawingAgent()
        assert "cad drawing" in agent.description.lower()

    def test_agent_has_cad_drawing_tool(self):
        """Test that CADDrawingAgent includes CADDrawingTool"""
        from structural_app.agent.cad_drawing_agent import CADDrawingAgent
        agent = CADDrawingAgent()

        # Check that cad_drawing is in available tools
        tool_names = [t.name for t in agent.available_tools.tool_map.values()]
        assert "cad_drawing" in tool_names

    def test_agent_has_ask_human_tool(self):
        """Test that CADDrawingAgent includes AskHuman tool"""
        from structural_app.agent.cad_drawing_agent import CADDrawingAgent
        agent = CADDrawingAgent()

        # Check that ask_human is in available tools
        tool_names = [t.name for t in agent.available_tools.tool_map.values()]
        assert "ask_human" in tool_names


class TestCADDrawingAgentSystemPrompt:
    """Test cases for CADDrawingAgent system prompt"""

    def test_system_prompt_contains_cad_keywords(self):
        """Test that system prompt contains CAD related keywords"""
        from structural_app.agent.cad_drawing_agent import CADDrawingAgent
        agent = CADDrawingAgent()

        prompt = agent.system_prompt
        assert "cad" in prompt.lower()
        assert "drawing" in prompt.lower()
        # Note: prompt uses plan_view/elevation_view as JSON field names
        assert "plan_view" in prompt.lower()
        assert "elevation_view" in prompt.lower()

    def test_system_prompt_mentions_cad_drawing_tool(self):
        """Test that system prompt mentions the cad_drawing tool"""
        from structural_app.agent.cad_drawing_agent import CADDrawingAgent
        agent = CADDrawingAgent()

        prompt = agent.system_prompt
        assert "cad_drawing" in prompt


class TestCADDrawingAgentExtraction:
    """Test cases for CADDrawingAgent result extraction"""

    def test_extract_drawing_results_with_valid_json(self):
        """Test extracting valid DrawingResults from response"""
        from structural_app.agent.cad_drawing_agent import CADDrawingAgent
        agent = CADDrawingAgent()

        response = """Step 1: Observed output of cmd `cad_drawing` executed:
{
  "status": "success",
  "files": {
    "plan_view": "output/drawings/beam_plan_20260222_100000.dxf",
    "elevation_view": "output/drawings/beam_elevation_20260222_100000.dxf"
  },
  "metadata": {
    "structure_type": "beam",
    "drawing_standard": "GB/T 50001-2017"
  }
}
Step 2: ..."""

        results = agent.extract_drawing_results(response)
        assert results is not None
        assert results["status"] == "success"
        assert "plan_view" in results["files"]
        assert "elevation_view" in results["files"]

    def test_extract_drawing_results_with_code_block(self):
        """Test extracting from JSON code block"""
        from structural_app.agent.cad_drawing_agent import CADDrawingAgent
        agent = CADDrawingAgent()

        response = """```json
{
  "status": "success",
  "files": {
    "plan_view": "output/drawings/beam_plan.dxf"
  }
}
```"""

        results = agent.extract_drawing_results(response)
        assert results is not None
        assert results["status"] == "success"

    def test_extract_drawing_results_returns_none_on_error(self):
        """Test that extraction returns None on invalid JSON"""
        from structural_app.agent.cad_drawing_agent import CADDrawingAgent
        agent = CADDrawingAgent()

        response = "This is not a valid response with JSON"

        results = agent.extract_drawing_results(response)
        assert results is None
