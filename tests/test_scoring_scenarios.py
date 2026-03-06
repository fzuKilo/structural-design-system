"""
新评分系统测试 - 多场景验证
测试新评分系统在不同设计场景下的表现
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Direct imports
import importlib.util

def load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load modules
scoring_curve_path = os.path.join(project_root, 'structural_app/tool/evaluators/scoring_curve.py')
config_path = os.path.join(project_root, 'structural_app/tool/evaluators/evaluator_config.py')
base_evaluator_path = os.path.join(project_root, 'structural_app/tool/evaluators/base_evaluator.py')
evaluator_path = os.path.join(project_root, 'structural_app/tool/evaluators/beam_evaluator.py')

scoring_curve_module = load_module_from_path('scoring_curve', scoring_curve_path)
sys.modules['scoring_curve'] = scoring_curve_module

config_module = load_module_from_path('evaluator_config', config_path)
sys.modules['evaluator_config'] = config_module

base_evaluator_module = load_module_from_path('base_evaluator', base_evaluator_path)
sys.modules['base_evaluator'] = base_evaluator_module

evaluator_module = load_module_from_path('beam_evaluator', evaluator_path)
BeamEvaluator = evaluator_module.BeamEvaluator


def create_test_case(name, description, design, results):
    """创建测试用例"""
    return {
        'name': name,
        'description': description,
        'design': design,
        'results': results
    }


def run_multi_scenario_test():
    """运行多场景测试"""
    print("=" * 80)
    print("新评分系统 v2.0 - 多场景验证测试")
    print("=" * 80)

    # 测试用例1: 优秀设计（利用率在最优区间）
    test_case_1 = create_test_case(
        name="场景1: 优秀设计",
        description="利用率在最优区间（0.65-0.75），应获得高分",
        design={
            'type': 'beam',
            'geometry': {
                'length': 6.0,
                'width': 0.3,
                'height': 0.55,
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
                'max_displacement': 0.018,  # 18mm, 利用率 ~0.75
                'max_stress_MPa': 110.0,    # 110 MPa, 利用率 ~0.70
                'detailed_results': {
                    'moments': [10, 20, 30, 40, 45, 40, 30, 20, 10]
                }
            },
            'code_check': {
                'compliant': True,
                'safety_factors': {
                    'stress': 1.43,
                    'deflection': 1.33
                }
            }
        }
    )

    # 测试用例2: 过度保守设计（利用率过低）
    test_case_2 = create_test_case(
        name="场景2: 过度保守设计",
        description="利用率过低（<0.5），经济性和效率得分应较低",
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
                'max_displacement': 0.002,  # 2mm, 利用率 ~0.08
                'max_stress_MPa': 40.0,     # 40 MPa, 利用率 ~0.26
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

    # 测试用例3: 临界设计（利用率接近1.0）
    test_case_3 = create_test_case(
        name="场景3: 临界设计",
        description="利用率接近极限（>0.9），安全性得分应较低",
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
                'max_displacement': 0.022,  # 22mm, 利用率 ~0.92
                'max_stress_MPa': 145.0,    # 145 MPa, 利用率 ~0.92
                'detailed_results': {
                    'moments': [10, 20, 30, 40, 45, 40, 30, 20, 10]
                }
            },
            'code_check': {
                'compliant': True,
                'safety_factors': {
                    'stress': 1.08,
                    'deflection': 1.09
                }
            }
        }
    )

    # 测试用例4: 构造不合理设计（高跨比过小）
    test_case_4 = create_test_case(
        name="场景4: 构造不合理设计",
        description="高跨比过小，应触发构造扣分",
        design={
            'type': 'beam',
            'geometry': {
                'length': 6.0,
                'width': 0.3,
                'height': 0.25,  # 高跨比 = 0.042 < 0.05
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
                'max_displacement': 0.015,
                'max_stress_MPa': 100.0,
                'detailed_results': {
                    'moments': [10, 20, 30, 40, 45, 40, 30, 20, 10]
                }
            },
            'code_check': {
                'compliant': True,
                'safety_factors': {
                    'stress': 1.57,
                    'deflection': 1.6
                }
            }
        }
    )

    test_cases = [test_case_1, test_case_2, test_case_3, test_case_4]

    # 运行测试
    evaluator = BeamEvaluator()

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"{test_case['name']}")
        print(f"{'=' * 80}")
        print(f"描述: {test_case['description']}")

        # 显示设计参数
        geometry = test_case['design']['geometry']
        print(f"\n[设计参数]")
        print(f"  跨度: {geometry['length']} m")
        print(f"  截面: {geometry['width']} m × {geometry['height']} m")
        print(f"  高跨比: {geometry['height']/geometry['length']:.3f}")

        # 显示分析结果
        results = test_case['results']['results']
        print(f"\n[分析结果]")
        print(f"  最大位移: {results['max_displacement']*1000:.1f} mm")
        print(f"  最大应力: {results['max_stress_MPa']:.1f} MPa")

        # 评估
        result = evaluator.evaluate_comprehensive(test_case['design'], test_case['results'])

        print(f"\n[评分结果]")
        print(f"  综合得分: {result['comprehensive_score']} 分")
        print(f"  等级: {result['grade']}")
        print(f"\n  维度得分:")
        print(f"    经济性: {result['dimensions']['economy']['score']:.1f}")
        print(f"    结构效率: {result['dimensions']['structural_efficiency']['score']:.1f}")
        print(f"    安全性: {result['dimensions']['safety']['score']:.1f}")
        print(f"    可持续性: {result['dimensions']['sustainability']['score']:.1f}")

        # 显示关键指标
        economy_indicators = result['dimensions']['economy']['indicators']
        safety_indicators = result['dimensions']['safety']['indicators']

        print(f"\n  关键指标:")
        print(f"    综合利用率: {economy_indicators['comprehensive_utilization']:.4f}")
        print(f"    应力利用率: {economy_indicators['stress_utilization']:.4f}")
        print(f"    挠度利用率: {economy_indicators['deflection_utilization']:.4f}")
        print(f"    材料用量指数: {economy_indicators['material_usage_index']:.3f}")

        # 显示构造问题
        if 'construction_issues' in safety_indicators:
            issues = safety_indicators['construction_issues']
            if issues:
                print(f"\n  构造问题: {len(issues)} 个")
                for issue in issues:
                    print(f"    - [{issue['severity']}] {issue['message']}")
                    print(f"      建议: {issue['recommendation']}")
            else:
                print(f"\n  构造问题: 无")

        # 显示改进建议
        if result.get('recommendations'):
            print(f"\n  改进建议:")
            for rec in result['recommendations']:
                print(f"    - {rec}")

    print(f"\n{'=' * 80}")
    print("多场景测试完成")
    print(f"{'=' * 80}")

    # 总结
    print(f"\n[测试总结]")
    print(f"  新评分系统 v2.0 的特点:")
    print(f"  1. 多级评分曲线: 在最优利用率区间（0.65-0.75）获得最高分")
    print(f"  2. 综合利用率: 同时考虑应力和挠度利用率")
    print(f"  3. 构造评分: 扣分制，检查几何合理性")
    print(f"  4. 权重调整: 安全性40%，更符合工程实践")
    print(f"  5. 评分更严格: 过度保守和临界设计都会被扣分")


if __name__ == '__main__':
    run_multi_scenario_test()
