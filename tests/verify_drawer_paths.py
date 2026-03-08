"""
Quick verification script to test cantilever beam drawer path fix
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from structural_app.tool.drawers.cantilever_beam_drawer import CantileverBeamDrawer

# Create drawer instance
drawer = CantileverBeamDrawer()

# Test design parameters
test_design = {
    'type': 'cantilever_beam',
    'geometry': {
        'length': 6.0,
        'width': 0.3,
        'height': 0.6
    },
    'material': {
        'material_name': 'C30 Concrete',
        'E': 30000,
        'density': 2500
    },
    'units': 'm',
    'constraints': {
        'support_type': 'cantilever'
    }
}

print("Testing CantileverBeamDrawer path configuration...")
print(f"Output directory: {drawer.output_dir}")
print(f"Output directory type: {type(drawer.output_dir)}")
print(f"Output directory exists: {os.path.exists(drawer.output_dir)}")

# Test drawing generation
print("\nGenerating elevation view...")
elevation_path = drawer.draw_elevation(test_design)
if elevation_path:
    print(f"✓ Elevation view saved to: {elevation_path}")
    print(f"  Path is absolute: {os.path.isabs(elevation_path)}")
    print(f"  File exists: {os.path.exists(elevation_path)}")
    print(f"  File size: {os.path.getsize(elevation_path)} bytes")
else:
    print("✗ Failed to generate elevation view")

print("\nGenerating plan view...")
plan_path = drawer.draw_plan(test_design)
if plan_path:
    print(f"✓ Plan view saved to: {plan_path}")
    print(f"  Path is absolute: {os.path.isabs(plan_path)}")
    print(f"  File exists: {os.path.exists(plan_path)}")
    print(f"  File size: {os.path.getsize(plan_path)} bytes")
else:
    print("✗ Failed to generate plan view")

print("\nGenerating details view...")
details_path = drawer.draw_details(test_design)
if details_path:
    print(f"✓ Details view saved to: {details_path}")
    print(f"  Path is absolute: {os.path.isabs(details_path)}")
    print(f"  File exists: {os.path.exists(details_path)}")
    print(f"  File size: {os.path.getsize(details_path)} bytes")
else:
    print("✗ Failed to generate details view")

print("\n" + "="*60)
print("Verification complete!")
