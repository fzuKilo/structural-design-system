"""
Pytest configuration for structural-design-system tests
"""

import sys
import os

# Add OpenManus to path for imports
_openmanus_path = 'D:\\openmanus'

if os.path.exists(_openmanus_path):
    if _openmanus_path not in sys.path:
        sys.path.insert(0, _openmanus_path)

# Add structural_app to path for imports
_structural_app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _structural_app_path not in sys.path:
    sys.path.insert(0, _structural_app_path)

