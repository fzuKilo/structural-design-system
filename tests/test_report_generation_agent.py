"""
Unit tests for ReportGenerationAgent
"""

import pytest
import sys
import os

# Add openmanus to path
_openmanus_path = 'D:\\openmanus'
if os.path.exists(_openmanus_path) and _openmanus_path not in sys.path:
    sys.path.insert(0, _openmanus_path)


class TestReportGenerationAgentInitialization:
    """Test cases for ReportGenerationAgent initialization"""

    def test_agent_exists(self):
        """Test that ReportGenerationAgent class can be imported"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        assert ReportGenerationAgent is not None

    def test_agent_inherits_toolcall_agent(self):
        """Test that ReportGenerationAgent inherits from ToolCallAgent"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        from app.agent.toolcall import ToolCallAgent
        assert issubclass(ReportGenerationAgent, ToolCallAgent)

    def test_agent_has_correct_name(self):
        """Test that ReportGenerationAgent has the correct default name"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()
        assert agent.name == "ReportGenerationAgent"

    def test_agent_has_correct_description(self):
        """Test that ReportGenerationAgent has the correct description"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()
        assert "report" in agent.description.lower()
        assert "generation" in agent.description.lower()

    def test_agent_has_report_tool(self):
        """Test that ReportGenerationAgent includes ReportTool"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()

        # Check that report is in available tools
        tool_names = [t.name for t in agent.available_tools.tool_map.values()]
        assert "report" in tool_names

    def test_agent_has_visualization_tool(self):
        """Test that ReportGenerationAgent includes VisualizationTool"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()

        # Check that visualization is in available tools
        tool_names = [t.name for t in agent.available_tools.tool_map.values()]
        assert "visualization" in tool_names

    def test_agent_has_ask_human_tool(self):
        """Test that ReportGenerationAgent includes AskHuman tool"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()

        # Check that ask_human is in available tools
        tool_names = [t.name for t in agent.available_tools.tool_map.values()]
        assert "ask_human" in tool_names


class TestReportGenerationAgentSystemPrompt:
    """Test cases for ReportGenerationAgent system prompt"""

    def test_system_prompt_contains_report_keywords(self):
        """Test that system prompt contains report related keywords"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()

        prompt = agent.system_prompt
        assert "report" in prompt.lower()
        assert "visualization" in prompt.lower()
        assert "design" in prompt.lower()

    def test_system_prompt_mentions_report_tool(self):
        """Test that system prompt mentions the report tool"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()

        prompt = agent.system_prompt
        assert "report tool" in prompt.lower() or "report" in prompt

    def test_system_prompt_mentions_visualization_tool(self):
        """Test that system prompt mentions the visualization tool"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()

        prompt = agent.system_prompt
        assert "visualization" in prompt.lower()

    def test_system_prompt_contains_output_format(self):
        """Test that system prompt contains output format information"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()

        prompt = agent.system_prompt
        assert "report_file" in prompt
        assert "visualizations" in prompt
        assert "summary" in prompt


class TestReportGenerationAgentExtractReportResults:
    """Test cases for extract_report_results method"""

    def test_extract_from_report_tool_output(self):
        """Test extracting report results from report tool output"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()

        response = """Step 1: Observed output of cmd `visualization` executed:
{
  "status": "success",
  "visualizations": {
    "static": {"moment_diagram": "output/visualizations/beam_moment.png"},
    "interactive": {"moment_html": "output/visualizations/beam_moment.html"}
  }
}
Step 2: Observed output of cmd `report` executed:
{
  "status": "success",
  "report_file": "output/reports/beam_design_report_20260228_143022.md",
  "visualizations": {
    "static": {"moment_diagram": "output/visualizations/beam_moment.png"},
    "interactive": {"moment_html": "output/visualizations/beam_moment.html"}
  },
  "summary": {
    "structure_type": "beam",
    "design_grade": "A",
    "comprehensive_score": 85.5,
    "code_compliant": true
  }
}
Step 3: Observed output of cmd `terminate` executed:"""

        report = agent.extract_report_results(response)
        assert report is not None
        assert report['status'] == 'success'
        assert 'report_file' in report
        assert 'summary' in report

    def test_extract_from_json_code_block(self):
        """Test extracting report results from JSON code block"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()

        response = """Here is the report result:

```json
{
  "status": "success",
  "report_file": "output/reports/beam_design_report_20260228_150000.md",
  "visualizations": {
    "static": {"moment_diagram": "output/visualizations/beam_moment_20260228_150000.png"},
    "interactive": {"moment_html": "output/visualizations/beam_moment_20260228_150000.html"}
  },
  "summary": {
    "structure_type": "beam",
    "design_grade": "A",
    "comprehensive_score": 92.0,
    "code_compliant": true
  }
}
```

Let me know if you need any further information."""

        report = agent.extract_report_results(response)
        assert report is not None
        assert report['status'] == 'success'
        assert 'report_file' in report
        assert report['summary']['comprehensive_score'] == 92.0

    def test_extract_fallback_to_status_field(self):
        """Test extracting report results using status field fallback"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()

        response = """Some text before
{"status": "success", "report_file": "output/reports/test.md", "summary": {"comprehensive_score": 78.5, "structure_type": "beam", "design_grade": "B"}}
Some text after"""

        report = agent.extract_report_results(response)
        assert report is not None
        assert report['status'] == 'success'
        assert 'report_file' in report

    def test_extract_returns_none_for_invalid_response(self):
        """Test that extraction returns None for invalid response"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()

        response = "This is not a valid response with JSON"

        report = agent.extract_report_results(response)
        assert report is None


class TestReportGenerationAgentExtractComprehensiveScore:
    """Test cases for extract_comprehensive_score method"""

    def test_extract_comprehensive_score_from_summary(self):
        """Test extracting comprehensive score from report summary"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()

        response = """Step 1: Observed output of cmd `report` executed:
{
  "status": "success",
  "report_file": "output/reports/test.md",
  "summary": {
    "structure_type": "beam",
    "design_grade": "A",
    "comprehensive_score": 85.5,
    "code_compliant": true
  }
}"""

        score = agent.extract_comprehensive_score(response)
        assert score is not None
        assert score == 85.5

    def test_extract_returns_none_when_score_not_found(self):
        """Test that extraction returns None when score not found"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()

        response = """Step 1: Observed output of cmd `report` executed:
{
  "status": "success",
  "report_file": "output/reports/test.md",
  "summary": {
    "structure_type": "beam",
    "design_grade": "A"
  }
}"""

        score = agent.extract_comprehensive_score(response)
        assert score is None

    def test_extract_returns_none_for_invalid_response(self):
        """Test that extraction returns None for invalid response"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        agent = ReportGenerationAgent()

        response = "This is not a valid response"

        score = agent.extract_comprehensive_score(response)
        assert score is None


class TestReportGenerationAgentIntegration:
    """Integration tests for ReportGenerationAgent"""

    def test_agent_can_be_created_with_custom_tools(self):
        """Test that agent can be created with custom tools"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        from structural_app.tool.report_tool import ReportTool
        from structural_app.tool.visualization_tool import VisualizationTool

        custom_report_tool = ReportTool()
        custom_viz_tool = VisualizationTool()
        agent = ReportGenerationAgent(tools=[custom_report_tool, custom_viz_tool])

        assert agent.name == "ReportGenerationAgent"
        # Check that our custom tools are in the available tools
        tool_names = [t.name for t in agent.available_tools.tool_map.values()]
        assert "report" in tool_names
        assert "visualization" in tool_names
