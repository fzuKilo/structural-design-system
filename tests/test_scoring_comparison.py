"""
评分系统对比测试
对比新旧评分系统的评分结果，验证改进效果
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

# Load modules
scoring_curve_path = os.path.join(project_root, 'structural_app/tool/evaluators/scoring_curve.py')
config_path = os.path.join(project_root, 'structural_app/tool/evaluators/evaluator_config.py')
new_base_evaluator_path = os.path.join(project_root, 'structural_app/tool/evaluators/base_evaluator.py')
old_base_evaluator_path = os.path.join(project_root, 'structural_app/tool/evaluators/base_evaluator.py.backup')
new_evaluator_path = os.path.join(project_root, 'structural_app/tool/evaluators/beam_evaluator.py')
old_evaluator_path = os.path.join(project_root, 'structural_app/tool/evaluators/beam_evaluator.py.backup')

# Load dependencies for new system
scoring_curve_module = load_module_from_path('scoring_curve', scoring_curve_path)
sys.modules['scoring_curve'] = scoring_curve_module

config_module = load_module_from_path('evaluator_config', config_path)
sys.modules['evaluator_config'] = config_module

new_base_evaluator_module = load_module_from_path('base_evaluator_new', new_base_evaluator_path)
sys.modules['base_evaluator'] = new_base_evaluator_module

# Load new evaluator
new_evaluator_module = load_module_from_path('beam_evaluator_new', new_evaluator_path)
NewBeamEvaluator = new_evaluator_module.BeamEvaluator

# Load old base evaluator (without new dependencies)
old_base_evaluator_module = load_module_from_path('base_evaluator_old', old_base_evaluator_path)

# Temporarily replace base_evaluator in sys.modules for old evaluator
sys.modules['base_evaluator'] = old_base_evaluator_module

# Load old evaluator
old_evaluator_module = load_module_from_path('beam_evaluator_old', old_evaluator_path)
OldBeamEvaluator = old_evaluator_module.BeamEvaluator

# Restore new base_evaluator
sys.modules['base_evaluator'] = new_base_evaluator_module


def create_test_case(name, design, results):
    """创建测试用例"""
    return {
        'name': name,
        'design': design,
        'results': results
    }


def run_comparison():
    """运行对比测试"""
    print("=" * 80)
    print("评分系统对比测试")
    print("=" * 80)

    # 测试用例1: 标准简支梁（6m跨度，10kN/m荷载）
    test_case_1 = create_test_case(
        name="标准简支梁（6m跨度，10kN/m荷载）",
        design={
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
                'material_name': 'C30'
            }
        },
        results={
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
    )

    # 测试用例2: 过度设计（截面过大）
    test_case_2 = create_test_case(
        name="过度设计（截面过大）",
        design={
            'type': 'beam',
            'geometry': {
                'length': 6.0,
                'width': 0.5,
                'height': 0.8,
                'n_elements': 20
            },
            'material': {
                'E': 30e9,
                'fy': 235e6,
                'material_name': 'C30'
            }
        },
        results={
            'status': 'success',
            'results': {
                'max_displacement': 0.002,  # 2mm
                'max_stress_MPa': 40.0,     # 40 MPa
                'detailed_results': {
                    'moments': [10, 20, 30, 40, 45, 40, 30, 20, 10]
                }
            },
            'code_check': {
                'compliant': True,
                'safety_factors': {
                    'stress': 3.9,
                    'deflection': 12.0
                }
            }
        }
    )

    # 测试用例3: 临界设计（接近极限）
    test_case_3 = create_test_case(
        name="临界设计（接近极限）",
        design={
            'type': 'beam',
            'geometry': {
                'length': 6.0,
                'width': 0.25,
                'height': 0.45,
                'n_elements': 20
            },
            'material': {
                'E': 30e9,
                'fy': 235e6,
                'material_name': 'C30'
            }
        },
        results={
            'status': 'success',
            'results': {
                'max_displacement': 0.020,  # 20mm
                'max_stress_MPa': 145.0,    # 145 MPa
                'detailed_results': {
                    'moments': [10, 20, 30, 40, 45, 40, 30, 20, 10]
                }
            },
            'code_check': {
                'compliant': True,
                'safety_factors': {
                    'stress': 1.08,
                    'deflection': 1.2
                }
            }
        }
    )

    test_cases = [test_case_1, test_case_2, test_case_3]

    # 运行对比
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"测试用例 {i}: {test_case['name']}")
        print(f"{'=' * 80}")

        # 旧评分系统
        print("\n[旧评分系统]")
        old_evaluator = OldBeamEvaluator()
        old_result = old_evaluator.evaluate_comprehensive(test_case['design'], test_case['results'])

        print(f"  综合得分: {old_result['comprehensive_score']}")
        print(f"  等级: {old_result['grade']}")
        print(f"  经济性: {old_result['dimensions']['economy']['score']}")
        print(f"  结构效率: {old_result['dimensions']['structural_efficiency']['score']}")
        print(f"  安全性: {old_result['dimensions']['safety']['score']}")
        print(f"  可持续性: {old_result['dimensions']['sustainability']['score']}")

        # 新评分系统
        print("\n[新评分系统 v2.0]")
        new_evaluator = NewBeamEvaluator()
        new_result = new_evaluator.evaluate_comprehensive(test_case['design'], test_case['results'])

        print(f"  综合得分: {new_result['comprehensive_score']}")
        print(f"  等级: {new_result['grade']}")
        print(f"  经济性: {new_result['dimensions']['economy']['score']}")
        print(f"  结构效率: {new_result['dimensions']['structural_efficiency']['score']}")
        print(f"  安全性: {new_result['dimensions']['safety']['score']}")
        print(f"  可持续性: {new_result['dimensions']['sustainability']['score']}")

        # 对比分析
        print("\n[对比分析]")
        score_diff = new_result['comprehensive_score'] - old_result['comprehensive_score']
        print(f"  得分差异: {score_diff:+.1f} 分")

        if abs(score_diff) < 5:
            print(f"  评价: 评分基本一致")
        elif score_diff > 0:
            print(f"  评价: 新系统评分更高（更宽松）")
        else:
            print(f"  评价: 新系统评分更低（更严格）")

        # 显示新系统的构造检查
        if 'construction_issues' in new_result['dimensions']['safety']['indicators']:
            issues = new_result['dimensions']['safety']['indicators']['construction_issues']
            if issues:
                print(f"\n  构造问题: {len(issues)} 个")
                for issue in issues:
                    print(f"    - [{issue['severity']}] {issue['message']}")
            else:
                print(f"\n  构造问题: 无")

    print(f"\n{'=' * 80}")
    print("对比测试完成")
    print(f"{'=' * 80}")


if __name__ == '__main__':
    run_comparison()
