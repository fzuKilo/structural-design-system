"""
Unit tests for FEAnalysisAgent
"""

import pytest
import sys
import os

# OpenManus path is handled by conftest.py


class TestFEAnalysisAgentInitialization:
    """Test cases for FEAnalysisAgent initialization"""

    def test_agent_exists(self):
        """Test that FEAnalysisAgent class can be imported"""
        from structural_app.agent.fe_analysis_agent import FEAnalysisAgent
        assert FEAnalysisAgent is not None

    def test_agent_inherits_toolcall_agent(self):
        """Test that FEAnalysisAgent inherits from ToolCallAgent"""
        from structural_app.agent.fe_analysis_agent import FEAnalysisAgent
        from app.agent.toolcall import ToolCallAgent
        assert issubclass(FEAnalysisAgent, ToolCallAgent)

    def test_agent_has_correct_name(self):
        """Test that FEAnalysisAgent has the correct default name"""
        from structural_app.agent.fe_analysis_agent import FEAnalysisAgent
        agent = FEAnalysisAgent()
        assert agent.name == "FEAnalysisAgent"

    def test_agent_has_correct_description(self):
        """Test that FEAnalysisAgent has the correct description"""
        from structural_app.agent.fe_analysis_agent import FEAnalysisAgent
        agent = FEAnalysisAgent()
        assert "finite element analysis" in agent.description.lower()

    def test_agent_has_fe_analysis_tool(self):
        """Test that FEAnalysisAgent includes FEAnalysisTool"""
        from structural_app.agent.fe_analysis_agent import FEAnalysisAgent
        agent = FEAnalysisAgent()

        # Check that fe_analysis is in available tools
        tool_names = [t.name for t in agent.available_tools.tool_map.values()]
        assert "fe_analysis" in tool_names

    def test_agent_has_ask_human_tool(self):
        """Test that FEAnalysisAgent includes AskHuman tool"""
        from structural_app.agent.fe_analysis_agent import FEAnalysisAgent
        agent = FEAnalysisAgent()

        # Check that ask_human is in available tools
        tool_names = [t.name for t in agent.available_tools.tool_map.values()]
        assert "ask_human" in tool_names


class TestFEAnalysisAgentSystemPrompt:
    """Test cases for FEAnalysisAgent system prompt"""

    def test_system_prompt_contains_fe_analysis_keywords(self):
        """Test that system prompt contains FE analysis related keywords"""
        from structural_app.agent.fe_analysis_agent import FEAnalysisAgent
        agent = FEAnalysisAgent()

        prompt = agent.system_prompt
        assert "finite element" in prompt.lower()
        assert "analysis" in prompt.lower()
        assert "displacement" in prompt.lower()
        assert "stress" in prompt.lower()

    def test_system_prompt_mentions_fe_analysis_tool(self):
        """Test that system prompt mentions the fe_analysis tool"""
        from structural_app.agent.fe_analysis_agent import FEAnalysisAgent
        agent = FEAnalysisAgent()

        prompt = agent.system_prompt
        assert "fe_analysis" in prompt
