"""
Direct test of FrameAnalyzer without full environment
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Direct import to avoid full tool initialization
from structural_app.tool.analyzers.frame_analyzer import FrameAnalyzer


def test_frame_analyzer_methods():
    """Test that FrameAnalyzer has all required abstract methods implemented"""

    print("Testing FrameAnalyzer abstract method implementation...")
    print()

    # Check if class can be instantiated
    try:
        analyzer = FrameAnalyzer()
        print("✓ FrameAnalyzer instantiated successfully (no abstract method errors)")
    except TypeError as e:
        if "abstract" in str(e).lower():
            print(f"✗ FAILED: {e}")
            return False
        else:
            raise

    # Check required methods
    required_methods = [
        '_get_structure_type',
        'build_model',
        'analyze',
        'check_code'  # This is the one we just added
    ]

    print("\nChecking required abstract methods:")
    all_present = True
    for method_name in required_methods:
        if hasattr(analyzer, method_name):
            method = getattr(analyzer, method_name)
            if callable(method):
                print(f"  ✓ {method_name} - present and callable")
            else:
                print(f"  ✗ {method_name} - present but not callable")
                all_present = False
        else:
            print(f"  ✗ {method_name} - NOT FOUND")
            all_present = False

    print()
    if all_present:
        print("✅ SUCCESS: All required methods are implemented!")
        return True
    else:
        print("❌ FAILED: Some required methods are missing")
        return False


if __name__ == "__main__":
    success = test_frame_analyzer_methods()
    sys.exit(0 if success else 1)
