"""
Test script to verify frame element stress extraction and uniformity calculation
"""

import sys
sys.path.insert(0, 'D:/structural-design-system')

from structural_app.tool.analyzers.frame_analyzer import FrameAnalyzer
from structural_app.tool.evaluators.frame_evaluator import FrameEvaluator


def test_frame_element_stresses():
    """Test that element stresses are correctly extracted and used for uniformity calculation"""

    # Create a simple 2-bay 2-story frame design
    design = {
        'geometry': {
            'num_bays': 2,
            'num_stories': 2,
            'bay_widths': [4.0, 4.0],  # 2 bays, each 4m
            'story_heights': [3.5, 3.5],  # 2 stories, each 3.5m
            'beams': {
                'width': 0.3,
                'depth': 0.6
            },
            'columns': {
                'width': 0.4,
                'depth': 0.4
            }
        },
        'material': {
            'E': 30e9,  # Concrete: 30 GPa
            'fy': 20.1e6,  # C30 concrete compressive strength
            'material_name': 'C30'
        },
        'loads': {
            'beam_distributed': [
                {'story': 1, 'bay': 1, 'q': -15000},  # 15 kN/m
                {'story': 1, 'bay': 2, 'q': -15000},
                {'story': 2, 'bay': 1, 'q': -12000},  # 12 kN/m
                {'story': 2, 'bay': 2, 'q': -12000}
            ],
            'lateral': [
                {'story': 1, 'Fx': 20000},  # 20 kN lateral load
                {'story': 2, 'Fx': 15000}   # 15 kN lateral load
            ]
        },
        'constraints': {
            'support_type': 'fixed'
        }
    }

    # Build and analyze
    analyzer = FrameAnalyzer()
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

    # Check if element stresses are in extra field
    if hasattr(results, 'extra') and results.extra:
        element_stresses = results.extra.get('element_stresses', [])

        print(f"\n=== Element Stresses Extraction ===")
        print(f"Number of elements: {results.n_elements}")
        print(f"Number of element stresses: {len(element_stresses)}")

        if element_stresses:
            print(f"Element stresses (first 10): {[round(s/1e6, 2) for s in element_stresses[:10]]} MPa")
            print(f"Max element stress: {max(element_stresses)/1e6:.2f} MPa")
            print(f"Min element stress: {min(element_stresses)/1e6:.2f} MPa")
            print(f"Avg element stress: {sum(element_stresses)/len(element_stresses)/1e6:.2f} MPa")

            # Calculate stress utilization
            fy = design['material']['fy']
            allowable = fy / 1.5
            utilizations = [s / allowable for s in element_stresses]
            print(f"\nStress utilizations (first 10): {[round(u, 3) for u in utilizations[:10]]}")
            print(f"Max utilization: {max(utilizations):.3f}")
            print(f"Min utilization: {min(utilizations):.3f}")
            print(f"Avg utilization: {sum(utilizations)/len(utilizations):.3f}")

            # Calculate CV
            avg_util = sum(utilizations) / len(utilizations)
            variance = sum((u - avg_util) ** 2 for u in utilizations) / len(utilizations)
            std_dev = variance ** 0.5
            cv = std_dev / avg_util if avg_util > 0 else 0
            print(f"Coefficient of Variation (CV): {cv:.3f}")

            # Test evaluator
            print(f"\n=== Evaluator Test ===")
            evaluator = FrameEvaluator()

            # Prepare results dict for evaluator
            results_dict = {
                'results': {
                    'detailed_results': {
                        'max_displacement': results.max_displacement,
                        'max_stress': results.max_stress,
                        'max_moment': results.max_moment,
                        'moments': results.moments,
                        'material': design['material'],
                        'extra': results.extra
                    }
                },
                'code_check': analyzer.check_code(results)
            }

            # Test efficiency evaluation (uses uniformity calculation)
            efficiency = evaluator.evaluate_efficiency(design, results_dict)
            print(f"Efficiency score: {efficiency['score']}")
            print(f"Average utilization: {efficiency['indicators']['average_utilization']:.4f}")
            print(f"Utilization uniformity: {efficiency['indicators']['utilization_uniformity']:.4f}")

            # Compare with fallback method (using moments)
            print(f"\n=== Method Comparison ===")
            # Temporarily remove element_stresses to test fallback
            results_dict_fallback = {
                'results': {
                    'detailed_results': {
                        'max_displacement': results.max_displacement,
                        'max_stress': results.max_stress,
                        'max_moment': results.max_moment,
                        'moments': results.moments,
                        'material': design['material'],
                        'extra': {}  # Empty extra to trigger fallback
                    }
                },
                'code_check': analyzer.check_code(results)
            }
            efficiency_fallback = evaluator.evaluate_efficiency(design, results_dict_fallback)
            print(f"Fallback uniformity (using moments): {efficiency_fallback['indicators']['utilization_uniformity']:.4f}")
            print(f"New uniformity (using stresses): {efficiency['indicators']['utilization_uniformity']:.4f}")
            print(f"Difference: {(efficiency['indicators']['utilization_uniformity'] - efficiency_fallback['indicators']['utilization_uniformity']):.4f}")

            print("\nTest completed successfully!")

        else:
            print("ERROR: Element stresses not found in results.extra")

    else:
        print("ERROR: results.extra not available")


if __name__ == '__main__':
    test_frame_element_stresses()
