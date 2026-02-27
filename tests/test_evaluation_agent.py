"""
Unit tests for EvaluationAgent
"""

import pytest
import sys
import os

# Add openmanus to path
_openmanus_path = 'D:\\openmanus'
if os.path.exists(_openmanus_path) and _openmanus_path not in sys.path:
    sys.path.insert(0, _openmanus_path)


class TestEvaluationAgentInitialization:
    """Test cases for EvaluationAgent initialization"""

    def test_agent_exists(self):
        """Test that EvaluationAgent class can be imported"""
        from structural_app.agent.evaluation_agent import EvaluationAgent
        assert EvaluationAgent is not None

    def test_agent_inherits_toolcall_agent(self):
        """Test that EvaluationAgent inherits from ToolCallAgent"""
        from structural_app.agent.evaluation_agent import EvaluationAgent
        from app.agent.toolcall import ToolCallAgent
        assert issubclass(EvaluationAgent, ToolCallAgent)

    def test_agent_has_correct_name(self):
        """Test that EvaluationAgent has the correct default name"""
        from structural_app.agent.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()
        assert agent.name == "EvaluationAgent"

    def test_agent_has_correct_description(self):
        """Test that EvaluationAgent has the correct description"""
        from structural_app.agent.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()
        assert "evaluation" in agent.description.lower()

    def test_agent_has_evaluation_tool(self):
        """Test that EvaluationAgent includes EvaluationTool"""
        from structural_app.agent.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()

        # Check that evaluation is in available tools
        tool_names = [t.name for t in agent.available_tools.tool_map.values()]
        assert "evaluation" in tool_names

    def test_agent_has_ask_human_tool(self):
        """Test that EvaluationAgent includes AskHuman tool"""
        from structural_app.agent.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()

        # Check that ask_human is in available tools
        tool_names = [t.name for t in agent.available_tools.tool_map.values()]
        assert "ask_human" in tool_names


class TestEvaluationAgentSystemPrompt:
    """Test cases for EvaluationAgent system prompt"""

    def test_system_prompt_contains_evaluation_keywords(self):
        """Test that system prompt contains evaluation related keywords"""
        from structural_app.agent.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()

        prompt = agent.system_prompt
        assert "evaluation" in prompt.lower()
        assert "comprehensive score" in prompt.lower()
        assert "design" in prompt.lower()

    def test_system_prompt_mentions_evaluation_tool(self):
        """Test that system prompt mentions the evaluation tool"""
        from structural_app.agent.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()

        prompt = agent.system_prompt
        assert "evaluation" in prompt

    def test_system_prompt_contains_evaluation_dimensions(self):
        """Test that system prompt mentions the 4 evaluation dimensions"""
        from structural_app.agent.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()

        prompt = agent.system_prompt
        assert "economy" in prompt.lower()
        assert "safety" in prompt.lower()
        assert "sustainability" in prompt.lower()


class TestEvaluationAgentExtractEvaluationReport:
    """Test cases for extract_evaluation_report method"""

    def test_extract_from_evaluation_tool_output(self):
        """Test extracting evaluation report from evaluation tool output"""
        from structural_app.agent.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()

        response = """Step 1: Observed output of cmd `create_chat_completion` executed:
{
  "type": "evaluation",
  "arguments": "{\"evaluation_data\": \"...\"}"
}
Step 2: Observed output of cmd `evaluation` executed:
{
  "status": "success",
  "comprehensive_score": 85.5,
  "grade": "B+",
  "dimensions": {
    "economy": {"score": 80.0},
    "structural_efficiency": {"score": 85.0},
    "safety": {"score": 90.0},
    "sustainability": {"score": 75.0}
  },
  "recommendations": []
}
Step 3: Observed output of cmd `terminate` executed:"""

        report = agent.extract_evaluation_report(response)
        assert report is not None
        assert report['status'] == 'success'
        assert report['comprehensive_score'] == 85.5
        assert report['grade'] == 'B+'

    def test_extract_from_json_code_block(self):
        """Test extracting evaluation report from JSON code block"""
        from structural_app.agent.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()

        response = """Here is the evaluation result:

```json
{
  "status": "success",
  "comprehensive_score": 92.0,
  "grade": "A",
  "dimensions": {
    "economy": {"score": 88.0},
    "structural_efficiency": {"score": 95.0},
    "safety": {"score": 93.0},
    "sustainability": {"score": 82.0}
  },
  "recommendations": []
}
```

Let me know if you need any further information."""

        report = agent.extract_evaluation_report(response)
        assert report is not None
        assert report['status'] == 'success'
        assert report['comprehensive_score'] == 92.0
        assert report['grade'] == 'A'

    def test_extract_fallback_to_status_field(self):
        """Test extracting evaluation report using status field fallback"""
        from structural_app.agent.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()

        response = """Some text before
{"status": "success", "comprehensive_score": 78.5, "grade": "C+"}
Some text after"""

        report = agent.extract_evaluation_report(response)
        assert report is not None
        assert report['status'] == 'success'
        assert report['comprehensive_score'] == 78.5

    def test_extract_returns_none_for_invalid_response(self):
        """Test that extraction returns None for invalid response"""
        from structural_app.agent.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()

        response = "This is not a valid response with JSON"

        report = agent.extract_evaluation_report(response)
        assert report is None


class TestEvaluationAgentIntegration:
    """Integration tests for EvaluationAgent"""

    def test_agent_can_be_created_with_custom_tools(self):
        """Test that agent can be created with custom tools"""
        from structural_app.agent.evaluation_agent import EvaluationAgent
        from structural_app.tool.evaluation_tool import EvaluationTool

        custom_tool = EvaluationTool()
        agent = EvaluationAgent(tools=[custom_tool])

        assert agent.name == "EvaluationAgent"
        # Check that our custom tool is in the available tools
        tool_names = [t.name for t in agent.available_tools.tool_map.values()]
        assert "evaluation" in tool_names
