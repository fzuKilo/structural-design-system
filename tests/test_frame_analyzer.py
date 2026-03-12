"""
Test frame analyzer
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from structural_app.tool.analyzers.frame_analyzer import FrameAnalyzer


def test_frame_analyzer_single_bay_single_story():
    """Test single-bay single-story frame"""
    design = {
        "type": "frame",
        "geometry": {
            "num_bays": 1,
            "num_stories": 1,
            "bay_widths": [6.0],
            "story_heights": [4.0],
            "columns": {"type": "rectangular", "width": 0.4, "depth": 0.4},
            "beams": {"type": "rectangular", "width": 0.3, "depth": 0.6},
            "n_elements_per_beam": 5,
            "n_elements_per_column": 4
        },
        "material": {
            "E": 30e9,
            "nu": 0.2,
            "fy": 235e6,
            "material_name": "C30"
        },
        "loads": {
            "beam_distributed": [
                {"story": 1, "bay": 0, "q": -10000, "direction": "y"}
            ],
            "lateral": [
                {"story": 1, "Fx": 5000}
            ]
        },
        "boundary": {
            "column_base": "fixed"
        }
    }

    analyzer = FrameAnalyzer()

    # Test validation
    is_valid, error_msg = analyzer.validate_design(design)
    assert is_valid, f"Validation failed: {error_msg}"

    # Test model building
    success = analyzer.build_model(design)
    assert success, "Model building failed"

    # Test analysis
    results = analyzer.analyze()
    assert results.analysis_status == "success", f"Analysis failed: {results.error_message}"
    assert results.max_displacement > 0
    assert results.max_moment > 0

    print(f"\n✅ Single-bay single-story frame test passed!")
    print(f"   Max displacement: {results.max_displacement*1000:.2f} mm")
    print(f"   Max moment: {results.max_moment/1000:.2f} kN·m")
    print(f"   Max stress: {results.max_stress/1e6:.2f} MPa")


def test_frame_analyzer_multi_bay_multi_story():
    """Test multi-bay multi-story frame"""
    design = {
        "type": "frame",
        "geometry": {
            "num_bays": 2,
            "num_stories": 3,
            "bay_widths": [6.0, 6.0],
            "story_heights": [4.0, 3.5, 3.5],
            "columns": {"type": "rectangular", "width": 0.4, "depth": 0.4},
            "beams": {"type": "rectangular", "width": 0.3, "depth": 0.6},
            "n_elements_per_beam": 5,
            "n_elements_per_column": 4
        },
        "material": {
            "E": 30e9,
            "nu": 0.2,
            "fy": 235e6,
            "material_name": "C30"
        },
        "loads": {
            "beam_distributed": [
                {"story": 1, "bay": 0, "q": -10000, "direction": "y"},
                {"story": 1, "bay": 1, "q": -10000, "direction": "y"},
                {"story": 2, "bay": 0, "q": -8000, "direction": "y"},
                {"story": 2, "bay": 1, "q": -8000, "direction": "y"},
                {"story": 3, "bay": 0, "q": -6000, "direction": "y"},
                {"story": 3, "bay": 1, "q": -6000, "direction": "y"}
            ],
            "lateral": [
                {"story": 1, "Fx": 5000},
                {"story": 2, "Fx": 4000},
                {"story": 3, "Fx": 3000}
            ]
        },
        "boundary": {
            "column_base": "fixed"
        }
    }

    analyzer = FrameAnalyzer()

    # Test validation
    is_valid, error_msg = analyzer.validate_design(design)
    assert is_valid, f"Validation failed: {error_msg}"

    # Test model building
    success = analyzer.build_model(design)
    assert success, "Model building failed"

    # Test analysis
    results = analyzer.analyze()
    assert results.analysis_status == "success", f"Analysis failed: {results.error_message}"
    assert results.max_displacement > 0
    assert results.max_moment > 0
    assert len(results.nodes) == 12  # (2+1) * (3+1) = 12 nodes

    print(f"\n✅ Multi-bay multi-story frame test passed!")
    print(f"   Max displacement: {results.max_displacement*1000:.2f} mm")
    print(f"   Max moment: {results.max_moment/1000:.2f} kN·m")
    print(f"   Max stress: {results.max_stress/1e6:.2f} MPa")
    print(f"   Number of nodes: {len(results.nodes)}")


if __name__ == "__main__":
    test_frame_analyzer_single_bay_single_story()
    test_frame_analyzer_multi_bay_multi_story()
    print("\n🎉 All frame analyzer tests passed!")
