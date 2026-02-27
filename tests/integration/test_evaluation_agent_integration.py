"""
Integration tests for EvaluationAgent
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

# Add structural_app to path
_structural_app_path = r'D:\structural-design-system\structural_app'
if _structural_app_path not in sys.path:
    sys.path.insert(0, _structural_app_path)


class TestEvaluationAgentIntegration:
    """Integration tests for EvaluationAgent"""

    @pytest.fixture
    def evaluation_agent(self):
        """Create an EvaluationAgent instance"""
        from structural_app.agent.evaluation_agent import EvaluationAgent
        return EvaluationAgent()

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
    def sample_evaluation_data(self, sample_design_proposal, sample_analysis_results):
        """Sample evaluation data combining design and results"""
        return {
            "design_proposal": sample_design_proposal,
            "analysis_results": sample_analysis_results
        }

    def test_agent_exists_and_is_registered(self, evaluation_agent):
        """Test that the agent can be created and is properly configured"""
        assert evaluation_agent is not None
        assert evaluation_agent.name == "EvaluationAgent"

        # Check available tools
        tool_names = [t.name for t in evaluation_agent.available_tools.tool_map.values()]
        assert "evaluation" in tool_names
        assert "ask_human" in tool_names

    def test_evaluation_tool_available(self, evaluation_agent):
        """Test that the evaluation tool is properly configured"""
        evaluation_tool = evaluation_agent.available_tools.tool_map.get('evaluation')
        assert evaluation_tool is not None
        # Check that the tool has the expected name and description
        assert evaluation_tool.name == 'evaluation'
        assert 'evaluation' in evaluation_tool.description.lower()

    def test_system_prompt_structure(self, evaluation_agent):
        """Test that the system prompt has the correct structure"""
        prompt = evaluation_agent.system_prompt

        # Check for required sections
        assert "evaluation" in prompt.lower()
        assert "comprehensive score" in prompt.lower()
        assert "grade" in prompt.lower()
        assert "economy" in prompt.lower()
        assert "safety" in prompt.lower()
        assert "sustainability" in prompt.lower()

    def test_extract_evaluation_report_from_context(self, evaluation_agent, sample_evaluation_data):
        """Test extracting evaluation data from context"""
        # Test the extraction with a proper OpenManus execution log format
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

        report = evaluation_agent.extract_evaluation_report(response)
        assert report is not None
        assert report['status'] == 'success'
        assert 'comprehensive_score' in report
        assert report['comprehensive_score'] == 85.5
        assert report['grade'] == 'B+'

    @pytest.mark.asyncio
    async def test_evaluation_tool_direct_call(self, evaluation_agent, sample_evaluation_data):
        """Test calling the evaluation tool directly"""
        # Get the evaluation tool from the agent
        evaluation_tool = evaluation_agent.available_tools.tool_map.get('evaluation')

        # Convert evaluation data to JSON string
        evaluation_data_str = json.dumps({
            'design_proposal': sample_evaluation_data['design_proposal'],
            'analysis_results': sample_evaluation_data['analysis_results']
        }, ensure_ascii=False)

        # Execute the tool
        result = await evaluation_tool.execute(evaluation_data=evaluation_data_str)

        assert result is not None
        assert hasattr(result, 'output')

        # Parse the result
        result_data = json.loads(result.output)
        assert result_data['status'] == 'success'
        assert 'comprehensive_score' in result_data
        assert 'grade' in result_data
        assert 'dimensions' in result_data

        # Verify all 4 dimensions are present
        dimensions = result_data['dimensions']
        assert 'economy' in dimensions
        assert 'structural_efficiency' in dimensions
        assert 'safety' in dimensions
        assert 'sustainability' in dimensions


# asyncio.run() helper for async tests
def run_async(test_func, *args, **kwargs):
    """Helper function to run async tests"""
    import asyncio
    return asyncio.run(test_func(*args, **kwargs))


@pytest.mark.asyncio
async def test_evaluation_agent_with_sample_data():
    """End-to-end test with sample beam data"""
    from structural_app.agent.evaluation_agent import EvaluationAgent
    from structural_app.tool.evaluation_tool import EvaluationTool
    import json

    # Create agent
    agent = EvaluationAgent()

    # Sample data
    design_proposal = {
        "type": "beam",
        "geometry": {"length": 6.0, "width": 0.3, "height": 0.5, "n_elements": 20},
        "material": {"E": 30e9, "nu": 0.2, "fy": 235e6},
        "loads": {"distributed": [{"q": -10000, "direction": "y"}]},
        "constraints": {"support_type": "simply_supported"}
    }

    analysis_results = {
        "status": "success",
        "results": {
            "max_displacement": 0.001,
            "max_stress_MPa": 2.5,
            "max_moment_kNm": 45,
            "max_shear_kN": 30
        },
        "code_check": {
            "compliant": True,
            "safety_factors": {"stress": 60, "deflection": 6}
        }
    }

    # Test the evaluation tool directly
    tool = EvaluationTool()
    evaluation_data = json.dumps({
        "design_proposal": design_proposal,
        "analysis_results": analysis_results
    }, ensure_ascii=False)

    result = await tool.execute(evaluation_data=evaluation_data)

    assert result is not None
    result_data = json.loads(result.output)

    # Verify evaluation results
    assert result_data['status'] == 'success'
    assert 0 <= result_data['comprehensive_score'] <= 100
    assert result_data['grade'] in ['A+', 'A', 'B+', 'B', 'C+', 'C', 'D']

    print(f"Comprehensive Score: {result_data['comprehensive_score']}")
    print(f"Grade: {result_data['grade']}")
    print(f"Recommendations: {result_data.get('recommendations', [])}")


# Run the async test
if __name__ == "__main__":
    # Run pytest
    pytest.main([__file__, "-v"])
