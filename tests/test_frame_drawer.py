"""
Test frame drawer
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from structural_app.tool.drawers.frame_drawer import FrameDrawer


def test_frame_drawer_single_bay():
    """Test single-bay single-story frame drawing"""
    design = {
        "type": "frame",
        "geometry": {
            "num_bays": 1,
            "num_stories": 1,
            "bay_widths": [6.0],
            "story_heights": [4.0],
            "columns": {"type": "rectangular", "width": 0.4, "depth": 0.4},
            "beams": {"type": "rectangular", "width": 0.3, "depth": 0.6}
        },
        "units": "m"
    }

    drawer = FrameDrawer()

    # Test elevation drawing
    elevation_file = drawer.draw_elevation(design)
    assert elevation_file is not None, "Elevation drawing failed"
    assert Path(elevation_file).exists(), f"File not found: {elevation_file}"

    print(f"\n✅ Single-bay frame elevation drawing test passed!")
    print(f"   File: {elevation_file}")

    # Test detail drawing
    detail_file = drawer.draw_detail(design)
    assert detail_file is not None, "Detail drawing failed"
    assert Path(detail_file).exists(), f"File not found: {detail_file}"

    print(f"✅ Frame detail drawing test passed!")
    print(f"   File: {detail_file}")


def test_frame_drawer_multi_bay():
    """Test multi-bay multi-story frame drawing"""
    design = {
        "type": "frame",
        "geometry": {
            "num_bays": 2,
            "num_stories": 3,
            "bay_widths": [6.0, 6.0],
            "story_heights": [4.0, 3.5, 3.5],
            "columns": {"type": "rectangular", "width": 0.4, "depth": 0.4},
            "beams": {"type": "rectangular", "width": 0.3, "depth": 0.6}
        },
        "units": "m"
    }

    drawer = FrameDrawer()

    # Test elevation drawing
    elevation_file = drawer.draw_elevation(design)
    assert elevation_file is not None, "Elevation drawing failed"
    assert Path(elevation_file).exists(), f"File not found: {elevation_file}"

    print(f"\n✅ Multi-bay frame elevation drawing test passed!")
    print(f"   File: {elevation_file}")


if __name__ == "__main__":
    test_frame_drawer_single_bay()
    test_frame_drawer_multi_bay()
    print("\n🎉 All frame drawer tests passed!")
