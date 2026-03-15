"""
Test script to verify truss axial force extraction and evaluator improvements
"""

import sys
sys.path.insert(0, 'D:/structural-design-system')

from structural_app.tool.analyzers.truss_analyzer import TrussAnalyzer
from structural_app.tool.evaluators.truss_evaluator import TrussEvaluator


def test_truss_axial_forces():
    """Test that axial forces are correctly extracted and passed to evaluator"""

    # Create a simple truss design
    design = {
        'geometry': {
            'span': 10.0,
            'height': 2.0,
            'n_panels': 5,
            'truss_type': 'pratt'
        },
        'material': {
            'E': 200e9,  # Steel: 200 GPa
            'A': 0.01,   # 100 cm² = 0.01 m²
            'fy': 235e6  # Q235 steel
        },
        'loads': {
            'nodal': [
                {'node': 1, 'Fx': 0, 'Fy': -50000},  # 50 kN downward at node 1
                {'node': 2, 'Fx': 0, 'Fy': -50000},
                {'node': 3, 'Fx': 0, 'Fy': -50000},
                {'node': 4, 'Fx': 0, 'Fy': -50000},
                {'node': 5, 'Fx': 0, 'Fy': -50000},
            ]
        },
        'constraints': {
            'support_type': 'simply_supported'
        }
    }

    # Build and analyze
    analyzer = TrussAnalyzer()
    is_valid, error = analyzer.validate_design(design)
    print(f"Design validation: {is_valid}")
    if not is_valid:
        print(f"Validation error: {error}")
        return

    success = analyzer.build_model(design)
    print(f"Model built: {success}")
    if not success:
        return

    results = analyzer.analyze()
    print(f"Analysis status: {results.analysis_status}")

    # Check if axial forces are in extra field
    if hasattr(results, 'extra') and results.extra:
        axial_forces = results.extra.get('axial_forces', [])
        member_lengths = results.extra.get('member_lengths', [])

        print(f"\n=== Axial Forces Extraction ===")
        print(f"Number of members: {len(axial_forces)}")
        print(f"Axial forces (first 10): {[round(f, 2) for f in axial_forces[:10]]}")

        # Count tension and compression members
        tension_count = sum(1 for f in axial_forces if f > 0)
        compression_count = sum(1 for f in axial_forces if f < 0)

        print(f"Tension members: {tension_count}")
        print(f"Compression members: {compression_count}")
        print(f"Member lengths (first 5): {[round(l, 2) for l in member_lengths[:5]]}")

        # Test evaluator
        print(f"\n=== Evaluator Test ===")
        evaluator = TrussEvaluator()

        # Prepare results dict for evaluator
        results_dict = {
            'results': {
                'detailed_results': {
                    'max_displacement': results.max_displacement,
                    'max_stress': results.max_stress,
                    'extra': results.extra
                }
            },
            'code_check': analyzer.check_code(results)
        }

        # Test sustainability evaluation (承载能力计算)
        sustainability = evaluator.evaluate_sustainability(design, results_dict)
        print(f"Sustainability score: {sustainability['score']}")
        print(f"N_u (bearing capacity): {sustainability['indicators']['N_u_kN']} kN")
        print(f"Carbon intensity: {sustainability['indicators']['carbon_intensity']} kg CO2/kN")

        # Test construction check (长细比检查)
        construction = evaluator._check_structure_specific_construction(design, results_dict)
        print(f"\n=== Construction Issues ===")
        if construction:
            for issue in construction:
                print(f"- [{issue['severity']}] {issue['message']}")
        else:
            print("No construction issues found")

        print("\n✅ Test completed successfully!")

    else:
        print("❌ ERROR: Axial forces not found in results.extra")


if __name__ == '__main__':
    test_truss_axial_forces()
