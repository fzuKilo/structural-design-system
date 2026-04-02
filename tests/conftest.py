"""
Pytest configuration for structural-design-system tests
"""

import sys
import os

# Add project root to path so structural_app can be imported
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Try to add OpenManus to path if available (dev environment only, not required for CI)
_openmanus_candidates = [
    os.environ.get("OPENMANUS_PATH", ""),          # CI/dev 可通过环境变量覆盖
    os.path.join(_project_root, "..", "OpenManus"),
    "D:\\openmanus",
    "D:\\OpenManus",
]
for _path in _openmanus_candidates:
    if _path and os.path.exists(_path) and _path not in sys.path:
        sys.path.insert(0, _path)
        break
