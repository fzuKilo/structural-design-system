"""
Pytest configuration for structural-design-system tests
Sets up sys.path to allow importing from OpenManus
"""

import sys
import os

# Add OpenManus to path before any test imports
# This must be at position 0 to take precedence over local 'app' package
_openmanus_path = 'D:\\openmanus'  # Absolute path to avoid computation issues

if os.path.exists(_openmanus_path):
    # Remove if already in path to ensure it's at position 0
    if _openmanus_path in sys.path:
        sys.path.remove(_openmanus_path)
    sys.path.insert(0, _openmanus_path)
    print(f"[conftest] Added OpenManus to sys.path: {_openmanus_path}")
