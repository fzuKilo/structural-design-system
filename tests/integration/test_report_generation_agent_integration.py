"""
Integration tests for ReportGenerationAgent
Tests the agent with actual LLM calls and end-to-end evaluation
"""

import pytest
import sys
import os
import json

# Add openmanus to path
_openmanus_path = 'D:\\openmanus'
if os.path.exists(_openmanus_path) and _openmanus_path not in sys.path:
    sys.path.insert(0, _openmanus_path)


class TestReportGenerationAgentIntegration:
    """Integration tests for ReportGenerationAgent"""

    @pytest.fixture
    def report_generation_agent(self):
        """Create a ReportGenerationAgent instance"""
        from structural_app.agent.report_generation_agent import ReportGenerationAgent
        return ReportGenerationAgent()

    @pytest.fixture
    def sample_design_proposal(self):
        """Sample design proposal for testing"""
        return {
            "type": "beam",
            "units": "m",
            "geometry": {
                "length": 6.0,
                "width": 0.3,
                "height": 0.5,
                "n_elements": 20
            },
            "material": {
                "E": 30e9,
                "nu": 0.2,
                "fy": 235e6,
                "material_name": "C30"
            },
            "loads": {
                "distributed": [{"q": -10000, "direction": "y"}],
                "point": []
            },
            "constraints": {
                "support_type": "simply_supported"
            }
        }

    @pytest.fixture
    def sample_analysis_results(self):
        """Sample analysis results for testing"""
        return {
            "status": "success",
            "results": {
                "max_displacement": 0.00104,
                "max_displacement_mm": 1.04,
                "max_stress": 2.49e6,
                "max_stress_MPa": 2.49,
                "max_moment": 44.78,
                "max_moment_kNm": 44.78,
                "max_shear": 30000.0,
                "max_shear_kN": 30.0,
                "detailed_results": {
                    "geometry": {"length": 6.0, "width": 0.3, "height": 0.5},
                    "material": {"E": 30e9, "nu": 0.2},
                    "moments": [0, 10, 20, 30, 40, 44.78, 40, 30, 20, 10, 0],
                    "shears": [15, 20, 25, 30, 30, 30, 30, 25, 20, 15, 0]
                }
            },
            "code_check": {
                "compliant": True,
                "violations": [],
                "safety_factors": {
                    "stress": 63.05,
                    "deflection": 5.77
                }
            }
        }

    @pytest.fixture
    def sample_evaluation_report(self):
        """Sample evaluation report for testing"""
        return {
            "status": "success",
            "comprehensive_score": 85.5,
            "grade": "B+",
            "dimensions": {
                "economy": {"score": 80.0, "indicators": {"material_usage_index": 0.85}},
                "structural_efficiency": {"score": 85.0, "indicators": {"average_utilization": 0.72}},
                "safety": {"score": 90.0, "indicators": {"min_safety_factor": 5.77}},
                "sustainability": {"score": 75.0, "indicators": {"carbon_emission_kg": 450.0}}
            },
            "recommendations": []
        }

    @pytest.fixture
    def sample_drawing_results(self):
        """Sample drawing results for testing"""
        return {
            "status": "success",
            "files": {
                "plan_view": "output/drawings/beam_plan_20260228_143022.dxf",
                "elevation_view": "output/drawings/beam_elevation_20260228_143022.dxf",
                "details": "output/drawings/beam_details_20260228_143022.dxf"
            },
            "metadata": {
                "drawing_standard": "GB/T 50001-2017",
                "scale": "1:50",
                "units": "mm"
            }
        }

    def test_agent_exists_and_is_registered(self, report_generation_agent):
        """Test that the agent can be created and is properly configured"""
        assert report_generation_agent is not None
        assert report_generation_agent.name == "ReportGenerationAgent"

        # Check available tools
        tool_names = [t.name for t in report_generation_agent.available_tools.tool_map.values()]
        assert "report" in tool_names
        assert "visualization" in tool_names
        assert "ask_human" in tool_names

    def test_report_tool_available(self, report_generation_agent):
        """Test that the report tool is properly configured"""
        report_tool = report_generation_agent.available_tools.tool_map.get('report')
        assert report_tool is not None
        assert report_tool.name == 'report'
        assert 'report' in report_tool.description.lower()

    def test_visualization_tool_available(self, report_generation_agent):
        """Test that the visualization tool is properly configured"""
        viz_tool = report_generation_agent.available_tools.tool_map.get('visualization')
        assert viz_tool is not None
        assert viz_tool.name == 'visualization'
        assert 'visual' in viz_tool.description.lower()

    def test_system_prompt_structure(self, report_generation_agent):
        """Test that the system prompt has the correct structure"""
        prompt = report_generation_agent.system_prompt

        # Check for required sections
        assert "report" in prompt.lower()
        assert "visualization" in prompt.lower()
        assert "design" in prompt.lower()
        assert "report_file" in prompt
        assert "visualizations" in prompt

    def test_extract_report_results_from_context(self, report_generation_agent):
        """Test extracting report results from context"""
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
  "report_file": "output/reports/beam_design_report.md",
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

        report = report_generation_agent.extract_report_results(response)
        assert report is not None
        assert report['status'] == 'success'
        assert 'report_file' in report
        assert 'summary' in report
        assert report['summary']['comprehensive_score'] == 85.5
        assert report['summary']['design_grade'] == 'A'

    def test_extract_comprehensive_score_for_decision(self, report_generation_agent):
        """Test extracting comprehensive score for smart decision making"""
        response = """Step 1: Observed output of cmd `report` executed:
{
  "status": "success",
  "report_file": "output/reports/beam_design_report.md",
  "summary": {
    "structure_type": "beam",
    "design_grade": "B+",
    "comprehensive_score": 78.5,
    "code_compliant": true
  }
}"""

        score = report_generation_agent.extract_comprehensive_score(response)
        assert score is not None
        assert score == 78.5

    @pytest.mark.asyncio
    async def test_report_tool_direct_call(self, report_generation_agent, sample_design_proposal, sample_analysis_results, sample_evaluation_report):
        """Test calling the report tool directly"""
        # Get the report tool from the agent
        report_tool = report_generation_agent.available_tools.tool_map.get('report')

        # Convert data to JSON string
        report_data = json.dumps({
            'design_proposal': sample_design_proposal,
            'analysis_results': sample_analysis_results,
            'evaluation_report': sample_evaluation_report
        }, ensure_ascii=False)

        # Execute the tool
        result = await report_tool.execute(report_data=report_data)

        assert result is not None
        assert hasattr(result, 'output')

        # Parse the result
        result_data = json.loads(result.output)
        assert result_data['status'] == 'success'
        assert 'report_file' in result_data

        print(f"Report file: {result_data['report_file']}")

    @pytest.mark.asyncio
    async def test_visualization_tool_direct_call(self, report_generation_agent, sample_design_proposal, sample_analysis_results):
        """Test calling the visualization tool directly"""
        # Get the visualization tool from the agent
        viz_tool = report_generation_agent.available_tools.tool_map.get('visualization')

        # Execute the tool with design_proposal and analysis_results as separate parameters
        # This matches the expected signature in VisualizationTool.execute()
        result = await viz_tool.execute(
            design_proposal=sample_design_proposal,
            analysis_results=sample_analysis_results
        )

        assert result is not None
        assert hasattr(result, 'output')

        # Parse the result
        result_data = json.loads(result.output)

        # Debug output
        print(f"\n[DEBUG] Raw result: {result_data}")

        assert result_data['status'] == 'success', f"Expected success, got {result_data.get('error', 'unknown error')}"
        assert 'visualizations' in result_data
        assert 'static' in result_data['visualizations']
        assert 'interactive' in result_data['visualizations']

        print(f"Static visualizations: {result_data['visualizations']['static']}")
        print(f"Interactive visualizations: {result_data['visualizations']['interactive']}")


# Run the async tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
