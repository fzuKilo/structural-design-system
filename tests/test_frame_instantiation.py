"""
Quick test to verify FrameAnalyzer can be instantiated and check_code method exists
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from structural_app.tool.analyzers.analyzer_factory import AnalyzerFactory


def test_frame_analyzer_instantiation():
    """Test that FrameAnalyzer can be instantiated without abstract method error"""

    print("Testing FrameAnalyzer instantiation...")

    try:
        # Try to create FrameAnalyzer instance
        analyzer = AnalyzerFactory.create("frame")
        print("✓ FrameAnalyzer instantiated successfully")

        # Check if check_code method exists
        if hasattr(analyzer, 'check_code'):
            print("✓ check_code method exists")
        else:
            print("✗ check_code method not found")
            return False

        # Check if it's callable
        if callable(getattr(analyzer, 'check_code')):
            print("✓ check_code method is callable")
        else:
            print("✗ check_code method is not callable")
            return False

        print("\n✅ All checks passed! FrameAnalyzer is properly implemented.")
        return True

    except TypeError as e:
        if "abstract" in str(e).lower():
            print(f"✗ Abstract method error: {e}")
            return False
        else:
            raise
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_frame_analyzer_instantiation()
    sys.exit(0 if success else 1)
