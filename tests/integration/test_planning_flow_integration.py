"""
Integration tests for PlanningFlow
"""

import pytest
import sys
import os
import tempfile
import json

# Add project path
_project_path = 'C:\\Users\\86177\\projects\\structural-design-system'
if _project_path not in sys.path:
    sys.path.insert(0, _project_path)


class TestPlanningFlowInitialization:
    """Test cases for PlanningFlow initialization"""

    def test_planning_flow_exists(self):
        """Test that PlanningFlow class can be imported"""
        from structural_app.planning_flow import PlanningFlow
        assert PlanningFlow is not None

    def test_create_planning_flow_function_exists(self):
        """Test that create_planning_flow function can be imported"""
        from structural_app.planning_flow import create_planning_flow
        assert create_planning_flow is not None

    def test_planning_flow_in_agent_module(self):
        """Test that PlanningFlow is exported from agent module"""
        from structural_app.agent import PlanningFlow
        assert PlanningFlow is not None

    def test_create_planning_flow_in_agent_module(self):
        """Test that create_planning_flow is exported from agent module"""
        from structural_app.agent import create_planning_flow
        assert create_planning_flow is not None

    def test_planning_flow_has_output_dir(self):
        """Test that PlanningFlow has output_dir attribute"""
        from structural_app.planning_flow import PlanningFlow
        flow = PlanningFlow()
        assert hasattr(flow, 'output_dir')

    def test_planning_flow_has_results(self):
        """Test that PlanningFlow has results dictionary"""
        from structural_app.planning_flow import PlanningFlow
        flow = PlanningFlow()
        assert hasattr(flow, 'results')
        assert isinstance(flow.results, dict)


class TestPlanningFlowResults:
    """Test cases for PlanningFlow results handling"""

    def test_results_contains_all_keys(self):
        """Test that results dict contains all expected keys"""
        from structural_app.planning_flow import PlanningFlow
        flow = PlanningFlow()
        expected_keys = [
            'design_proposal',
            'analysis_results',
            'drawing_results',
            'evaluation_report',
            'report_results',
        ]
        for key in expected_keys:
            assert key in flow.results

    def test_save_results_creates_file(self):
        """Test that save_results creates a file"""
        from structural_app.planning_flow import PlanningFlow

        with tempfile.TemporaryDirectory() as tmpdir:
            flow = PlanningFlow(output_dir=tmpdir)
            flow.results = {'test': 'data'}
            filepath = flow.save_results('test_results.json')

            assert os.path.exists(filepath)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert data == {'test': 'data'}


class TestPlanningFlowFactory:
    """Test cases for create_planning_flow factory function"""

    def test_create_planning_flow_returns_instance(self):
        """Test that create_planning_flow returns PlanningFlow instance"""
        from structural_app.planning_flow import create_planning_flow, PlanningFlow
        flow = create_planning_flow()
        assert isinstance(flow, PlanningFlow)

    def test_create_planning_flow_with_custom_output_dir(self):
        """Test creating PlanningFlow with custom output directory"""
        from structural_app.planning_flow import create_planning_flow

        with tempfile.TemporaryDirectory() as tmpdir:
            flow = create_planning_flow(output_dir=tmpdir)
            assert str(flow.output_dir) == tmpdir


class TestPlanningFlowMethods:
    """Test cases for PlanningFlow helper methods"""

    def test_planning_flow_builds_analysis_request(self):
        """Test that PlanningFlow can build analysis requests"""
        from structural_app.planning_flow import PlanningFlow
        import json

        flow = PlanningFlow()
        design_proposal = {
            'type': 'beam',
            'geometry': {'length': 12000},
        }

        request = flow._build_analysis_request(design_proposal)
        parsed = json.loads(request)

        assert parsed['type'] == 'beam'
        assert parsed['geometry']['length'] == 12000

    def test_planning_flow_builds_report_request(self):
        """Test that PlanningFlow can build report requests"""
        from structural_app.planning_flow import PlanningFlow
        import json

        flow = PlanningFlow()
        design_proposal = {'type': 'beam'}
        analysis_results = {'status': 'success'}
        evaluation_report = {'comprehensive_score': 85}
        drawing_results = {'status': 'success'}

        request = flow._build_report_request(
            design_proposal,
            analysis_results,
            evaluation_report,
            drawing_results
        )

        parsed = json.loads(request)
        assert parsed['design_proposal']['type'] == 'beam'
        assert parsed['analysis_results']['status'] == 'success'
        assert parsed['evaluation_report']['comprehensive_score'] == 85
        assert parsed['drawing_results']['status'] == 'success'

    def test_planning_flow_builds_empty_requests(self):
        """Test that PlanningFlow handles None inputs gracefully"""
        from structural_app.planning_flow import PlanningFlow
        import json

        flow = PlanningFlow()

        # Test with None inputs for analysis request
        request = flow._build_analysis_request(None)
        # When None is passed, returns error message
        assert "No design proposal" in request

        # Test with None inputs for report request
        request = flow._build_report_request(None, None, None, None)
        parsed = json.loads(request)
        assert parsed['design_proposal'] is None
        assert parsed['analysis_results'] is None
        assert parsed['evaluation_report'] is None
        assert parsed['drawing_results'] is None
