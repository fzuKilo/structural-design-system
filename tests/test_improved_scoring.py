"""
Test script for improved scoring system
Tests MultiLevelScoringCurve and new BeamEvaluator
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Direct imports to avoid __init__.py issues
import importlib.util

def load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load modules directly
scoring_curve_path = os.path.join(project_root, 'structural_app/tool/evaluators/scoring_curve.py')
config_path = os.path.join(project_root, 'structural_app/tool/evaluators/evaluator_config.py')
evaluator_path = os.path.join(project_root, 'structural_app/tool/evaluators/beam_evaluator.py')
base_evaluator_path = os.path.join(project_root, 'structural_app/tool/evaluators/base_evaluator.py')

# Load scoring_curve first and register it
scoring_curve_module = load_module_from_path('scoring_curve', scoring_curve_path)
sys.modules['scoring_curve'] = scoring_curve_module

# Now load config which depends on scoring_curve
config_module = load_module_from_path('evaluator_config', config_path)
sys.modules['evaluator_config'] = config_module

# Load base_evaluator which depends on config
base_evaluator_module = load_module_from_path('base_evaluator', base_evaluator_path)
sys.modules['base_evaluator'] = base_evaluator_module

# Finally load beam_evaluator
evaluator_module = load_module_from_path('beam_evaluator', evaluator_path)

MultiLevelScoringCurve = scoring_curve_module.MultiLevelScoringCurve
get_scoring_curves = config_module.get_scoring_curves
get_weights = config_module.get_weights
BeamEvaluator = evaluator_module.BeamEvaluator


def test_scoring_curve():
    """Test multi-level scoring curve"""
    print("=" * 60)
    print("Testing MultiLevelScoringCurve")
    print("=" * 60)

    # Create a beam stress curve
    curve = MultiLevelScoringCurve(
        excellent_range=(0.65, 0.75),
        good_range=(0.60, 0.80),
        acceptable_range=(0.50, 0.90),
        peak_position=0.70
    )

    # Test various utilization values
    test_values = [0.3, 0.5, 0.6, 0.65, 0.70, 0.75, 0.80, 0.90, 0.95, 1.0, 1.1]

    print("\nUtilization | Score | Zone")
    print("-" * 40)
    for util in test_values:
        score = curve.calculate_score(util)
        zone = get_zone(util)
        print(f"{util:11.2f} | {score:5.1f} | {zone}")


def get_zone(util):
    """Helper to identify scoring zone"""
    if util > 1.0:
        return "Over-limit"
    elif 0.65 <= util <= 0.75:
        return "Excellent"
    elif 0.60 <= util <= 0.80:
        return "Good"
    elif 0.50 <= util <= 0.90:
        return "Acceptable"
    else:
        return "Poor"


def test_config():
    """Test configuration loading"""
    print("\n" + "=" * 60)
    print("Testing Configuration")
    print("=" * 60)

    # Test weights
    beam_weights = get_weights('beam')
    print("\nBeam weights:")
    for dim, weight in beam_weights.items():
        print(f"  {dim}: {weight:.0%}")

    # Test scoring curves
    beam_curves = get_scoring_curves('beam')
    print("\nBeam scoring curves loaded:")
    print(f"  - Stress curve: {beam_curves['stress']}")
    print(f"  - Deflection curve: {beam_curves['deflection']}")


def test_beam_evaluator():
    """Test new BeamEvaluator"""
    print("\n" + "=" * 60)
    print("Testing BeamEvaluator v2.0")
    print("=" * 60)

    evaluator = BeamEvaluator()

    # Mock design and results
    design = {
        'type': 'beam',
        'geometry': {
            'length': 6.0,
            'width': 0.3,
            'height': 0.6,
            'n_elements': 20
        },
        'material': {
            'E': 30e9,
            'fy': 235e6,
            'material_name': 'Q235'
        }
    }

    results = {
        'status': 'success',
        'results': {
            'max_displacement': 0.006,  # 6mm
            'max_stress_MPa': 100.0,    # 100 MPa
            'detailed_results': {
                'moments': [10, 20, 30, 40, 45, 40, 30, 20, 10]
            }
        },
        'code_check': {
            'compliant': True,
            'safety_factors': {
                'stress': 1.57,
                'deflection': 4.0
            }
        }
    }

    # Test economy evaluation
    print("\n1. Economy Evaluation:")
    economy = evaluator.evaluate_economy(design, results)
    print(f"   Score: {economy['score']}")
    print(f"   Comprehensive utilization: {economy['indicators']['comprehensive_utilization']:.4f}")
    print(f"   Material usage index: {economy['indicators']['material_usage_index']:.3f}")

    # Test efficiency evaluation
    print("\n2. Efficiency Evaluation:")
    efficiency = evaluator.evaluate_efficiency(design, results)
    print(f"   Score: {efficiency['score']}")
    print(f"   Average utilization: {efficiency['indicators']['average_utilization']:.4f}")

    # Test safety evaluation
    print("\n3. Safety Evaluation:")
    safety = evaluator.evaluate_safety(design, results)
    print(f"   Score: {safety['score']}")
    print(f"   Strength score: {safety['indicators']['strength_score']:.1f}")
    print(f"   Stiffness score: {safety['indicators']['stiffness_score']:.1f}")
    print(f"   Construction score: {safety['indicators']['construction_score']:.1f}")
    print(f"   Construction issues: {len(safety['indicators']['construction_issues'])}")

    # Test sustainability evaluation
    print("\n4. Sustainability Evaluation:")
    sustainability = evaluator.evaluate_sustainability(design, results)
    print(f"   Score: {sustainability['score']}")
    print(f"   Carbon emission: {sustainability['indicators']['carbon_emission_kg']:.1f} kg")

    # Test comprehensive evaluation
    print("\n5. Comprehensive Evaluation:")
    comprehensive = evaluator.evaluate_comprehensive(design, results)
    print(f"   Status: {comprehensive['status']}")
    print(f"   Comprehensive score: {comprehensive['comprehensive_score']}")
    print(f"   Grade: {comprehensive['grade']}")
    print(f"   Recommendations: {len(comprehensive['recommendations'])}")


if __name__ == '__main__':
    test_scoring_curve()
    test_config()
    test_beam_evaluator()
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
