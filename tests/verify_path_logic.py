"""
Direct test of cantilever beam drawer path configuration
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Direct import to avoid tool chain dependencies
import ezdxf
from datetime import datetime

# Simulate the base drawer initialization
class MockBaseDrawer:
    def __init__(self):
        self.structure_type = "cantilever_beam"
        _project_root = self._find_project_root()
        self.output_dir = _project_root / "output" / "drawings"
        print(f"Base drawer output_dir: {self.output_dir}")
        print(f"Output dir type: {type(self.output_dir)}")
        print(f"Output dir is absolute: {self.output_dir.is_absolute()}")

    def _find_project_root(self) -> Path:
        _current_file = Path(__file__).resolve()
        _project_root = _current_file.parent

        while _project_root.parent != _project_root:
            if (_project_root / "structural_app").exists():
                return _project_root
            if (_project_root / "config.toml").exists():
                return _project_root
            if (_project_root / "README.md").exists() and (_project_root / "structural_app").exists():
                return _project_root
            _project_root = _project_root.parent

        return _current_file.parent.parent

# Test the path logic
print("="*60)
print("Testing CantileverBeamDrawer path configuration")
print("="*60)

drawer = MockBaseDrawer()

# Test file path generation (simulating what the fixed code does)
os.makedirs(drawer.output_dir, exist_ok=True)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f"{drawer.output_dir}/cantilever_beam_elevation_{timestamp}.dxf"

print(f"\nGenerated filename: {filename}")
print(f"Filename type: {type(filename)}")
print(f"Is absolute path: {os.path.isabs(str(filename))}")

# Create a simple DXF to verify it works
doc = ezdxf.new('R2010')
msp = doc.modelspace()
msp.add_line((0, 0), (100, 100))

try:
    doc.saveas(filename)
    print(f"\n✓ Successfully saved test file")
    print(f"  File exists: {os.path.exists(filename)}")
    print(f"  File size: {os.path.getsize(filename)} bytes")
    print(f"  Full path: {os.path.abspath(filename)}")
except Exception as e:
    print(f"\n✗ Failed to save: {e}")

print("\n" + "="*60)
print("Verification complete!")
print("="*60)
