"""
Unit tests for FE Analysis Tool architecture
Tests analyzer factory, beam analyzer (without full OpenManus integration)
"""

import pytest
import numpy as np
from structural_app.tool.analyzers import AnalyzerFactory, BeamAnalyzer, StructureAnalyzer, AnalysisResults


class TestAnalyzerFactory:
    """Test cases for AnalyzerFactory"""

    def test_beam_analyzer_registered(self):
        """Test that beam analyzer is registered by default"""
        assert AnalyzerFactory.is_registered("beam")
        assert "beam" in AnalyzerFactory.get_available_types()

    def test_create_beam_analyzer(self):
        """Test creating a beam analyzer instance"""
        analyzer = AnalyzerFactory.create("beam")
        assert analyzer is not None
        assert isinstance(analyzer, BeamAnalyzer)
        assert isinstance(analyzer, StructureAnalyzer)

    def test_create_unknown_type_raises_error(self):
        """Test that creating unknown type raises ValueError"""
        with pytest.raises(ValueError, match="当前未支持的结构类型"):
            AnalyzerFactory.create("unknown_type")

    def test_get_available_types(self):
        """Test getting list of available types"""
        types = AnalyzerFactory.get_available_types()
        assert isinstance(types, list)
        assert "beam" in types


class TestBeamAnalyzer:
    """Test cases for BeamAnalyzer"""

    @pytest.fixture
    def simple_beam_design(self):
        """Fixture providing a simple beam design"""
        return {
            'geometry': {
                'length': 6.0,
                'width': 0.3,
                'height': 0.6,
                'n_elements': 20
            },
            'material': {
                'E': 30e9,
                'nu': 0.2,
                'fy': 235e6
            },
            'loads': {
                'distributed': [
                    {'q': -10000, 'direction': 'y'}
                ]
            },
            'constraints': {
                'support_type': 'simply_supported'
            }
        }

    def test_analyzer_initialization(self):
        """Test beam analyzer initialization"""
        analyzer = BeamAnalyzer()
        assert analyzer.structure_type == "beam"
        assert not analyzer.model_built

    def test_validate_valid_design(self, simple_beam_design):
        """Test validation of valid design"""
        analyzer = BeamAnalyzer()
        is_valid, error_msg = analyzer.validate_design(simple_beam_design)
        assert is_valid
        assert error_msg is None

    def test_validate_missing_geometry(self):
        """Test validation fails with missing geometry"""
        analyzer = BeamAnalyzer()
        design = {
            'material': {'E': 30e9, 'nu': 0.2},
            'loads': {'distributed': [{'q': -10000}]},
            'constraints': {'support_type': 'simply_supported'}
        }
        is_valid, error_msg = analyzer.validate_design(design)
        assert not is_valid
        assert "geometry" in error_msg.lower()

    def test_validate_invalid_support_type(self, simple_beam_design):
        """Test validation fails with invalid support type"""
        analyzer = BeamAnalyzer()
        simple_beam_design['constraints']['support_type'] = 'invalid_type'
        is_valid, error_msg = analyzer.validate_design(simple_beam_design)
        assert not is_valid
        assert "support_type" in error_msg.lower()

    def test_validate_negative_geometry(self, simple_beam_design):
        """Test validation fails with negative geometry values"""
        analyzer = BeamAnalyzer()
        simple_beam_design['geometry']['length'] = -5.0
        is_valid, error_msg = analyzer.validate_design(simple_beam_design)
        assert not is_valid
        assert "positive" in error_msg.lower()

    def test_build_model_success(self, simple_beam_design):
        """Test successful model building"""
        analyzer = BeamAnalyzer()
        success = analyzer.build_model(simple_beam_design)
        assert success
        assert analyzer.model_built

    def test_analyze_without_model_fails(self):
        """Test that analysis fails without building model first"""
        analyzer = BeamAnalyzer()
        results = analyzer.analyze()
        assert results.analysis_status == 'failed'
        assert 'not built' in results.error_message.lower()

    def test_full_analysis_workflow(self, simple_beam_design):
        """Test complete analysis workflow"""
        analyzer = BeamAnalyzer()
        result = analyzer.run_full_analysis(simple_beam_design)

        assert result['status'] == 'success'
        assert result['results'] is not None
        assert result['code_check'] is not None
        assert result['error'] is None

        # Check results structure
        results = result['results']
        assert isinstance(results, AnalysisResults)
        assert results.max_displacement > 0
        assert results.max_stress > 0
        assert results.max_moment > 0
        assert results.max_shear > 0
        assert len(results.displacements) == 21  # n_elements + 1
        assert len(results.moments) == 20  # n_elements

    def test_analysis_results_reasonable(self, simple_beam_design):
        """Test that analysis results are physically reasonable"""
        analyzer = BeamAnalyzer()
        result = analyzer.run_full_analysis(simple_beam_design)

        results = result['results']

        # Check displacement is reasonable (should be around 1mm for this case)
        assert 0.0005 < results.max_displacement < 0.005  # 0.5mm to 5mm

        # Check stress is reasonable (should be a few MPa)
        assert 1e6 < results.max_stress < 10e6  # 1 to 10 MPa

        # Check moment is reasonable (should be around 45 kN*m)
        assert 30000 < results.max_moment < 60000  # 30 to 60 kN*m

    def test_code_check_compliance(self, simple_beam_design):
        """Test code compliance checking"""
        analyzer = BeamAnalyzer()
        result = analyzer.run_full_analysis(simple_beam_design)

        code_check = result['code_check']
        assert 'compliant' in code_check
        assert 'violations' in code_check
        assert 'safety_factors' in code_check
        assert isinstance(code_check['violations'], list)
        assert isinstance(code_check['safety_factors'], dict)

    def test_cantilever_beam_support(self):
        """Test cantilever beam support type"""
        design = {
            'geometry': {'length': 3.0, 'width': 0.2, 'height': 0.4},
            'material': {'E': 30e9, 'nu': 0.2},
            'loads': {'distributed': [{'q': -5000}]},
            'constraints': {'support_type': 'cantilever'}
        }

        analyzer = BeamAnalyzer()
        result = analyzer.run_full_analysis(design)
        assert result['status'] == 'success'

    def test_point_load_support(self):
        """Test beam with point load"""
        design = {
            'geometry': {'length': 6.0, 'width': 0.3, 'height': 0.6},
            'material': {'E': 30e9, 'nu': 0.2},
            'loads': {
                'point': [
                    {'P': -50000, 'location': 3.0, 'direction': 'y'}
                ]
            },
            'constraints': {'support_type': 'simply_supported'}
        }

        analyzer = BeamAnalyzer()
        result = analyzer.run_full_analysis(design)
        assert result['status'] == 'success'
        assert result['results'].max_displacement > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
