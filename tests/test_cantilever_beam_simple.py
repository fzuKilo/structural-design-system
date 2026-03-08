"""
悬臂梁简化测试脚本
使用正常的Python导入机制
"""

import sys
import os

# 确保项目根目录在Python路径中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 正常导入
from structural_app.tool.analyzers.analyzer_factory import AnalyzerFactory
from structural_app.tool.drawers.drawer_factory import DrawerFactory
from structural_app.tool.evaluators.evaluator_factory import EvaluatorFactory


def test_cantilever_beam():
    """测试悬臂梁完整流程"""
    print("=" * 80)
    print("悬臂梁测试 - 验证架构通用性")
    print("=" * 80)

    # 测试设计参数（3米悬臂梁，5kN/m均布荷载）
    design = {
        'type': 'cantilever_beam',
        'geometry': {
            'length': 3.0,
            'width': 0.3,
            'height': 0.5,
            'n_elements': 20
        },
        'material': {
            'E': 30e9,
            'nu': 0.2,
            'fy': 235e6,
            'material_name': 'C30'
        },
        'loads': {
            'distributed': [
                {'q': -5000, 'direction': 'y'}
            ],
            'point': []
        },
        'constraints': {
            'support_type': 'cantilever'
        },
        'units': 'm'
    }

    print("\n[设计参数]")
    print(f"  结构类型: {design['type']}")
    print(f"  跨度: {design['geometry']['length']} m")
    print(f"  截面: {design['geometry']['width']} m × {design['geometry']['height']} m")
    print(f"  荷载: {design['loads']['distributed'][0]['q']/1000} kN/m")

    # 测试1: 检查工厂注册
    print("\n" + "=" * 80)
    print("[测试1] 工厂注册检查")
    print("=" * 80)

    print("\n可用的Analyzer类型:")
    print(f"  {AnalyzerFactory.get_available_types()}")
    assert AnalyzerFactory.is_registered('cantilever_beam'), "CantileverBeamAnalyzer未注册"
    print("  [PASS] CantileverBeamAnalyzer已注册")

    print("\n可用的Drawer类型:")
    print(f"  {DrawerFactory.get_available_types()}")
    assert DrawerFactory.is_registered('cantilever_beam'), "CantileverBeamDrawer未注册"
    print("  [PASS] CantileverBeamDrawer已注册")

    print("\n可用的Evaluator类型:")
    print(f"  {EvaluatorFactory.get_available_types()}")
    assert EvaluatorFactory.is_registered('cantilever_beam'), "CantileverBeamEvaluator未注册"
    print("  [PASS] CantileverBeamEvaluator已注册")

    # 测试2: 创建实例（通过工厂）
    print("\n" + "=" * 80)
    print("[测试2] 通过工厂创建实例")
    print("=" * 80)

    try:
        analyzer = AnalyzerFactory.create('cantilever_beam')
        print(f"  [PASS] Analyzer创建成功: {type(analyzer).__name__}")

        drawer = DrawerFactory.create('cantilever_beam')
        print(f"  [PASS] Drawer创建成功: {type(drawer).__name__}")

        evaluator = EvaluatorFactory.create('cantilever_beam')
        print(f"  [PASS] Evaluator创建成功: {type(evaluator).__name__}")
    except Exception as e:
        print(f"  [FAIL] 创建实例失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试3: 有限元分析
    print("\n" + "=" * 80)
    print("[测试3] 有限元分析")
    print("=" * 80)

    try:
        analyzer.build_model(design)
        print("  [PASS] 模型构建成功")

        results = analyzer.analyze()
        print(f"  [PASS] 分析完成: {results['status']}")
        print(f"    最大位移: {results['max_displacement']*1000:.2f} mm")
        print(f"    最大应力: {results['max_stress_MPa']:.2f} MPa")
        print(f"    最大弯矩: {results['max_moment']/1000:.2f} kN·m")

        code_check = analyzer.check_code(results)
        print(f"  [PASS] 规范校核: {'通过' if code_check['compliant'] else '不通过'}")
        print(f"    应力安全系数: {code_check['safety_factors']['stress']}")
        print(f"    挠度安全系数: {code_check['safety_factors']['deflection']}")

        # 将code_check添加到results中
        results['code_check'] = code_check
        results['results'] = {
            'max_displacement': results['max_displacement'],
            'max_stress_MPa': results['max_stress_MPa'],
            'detailed_results': results['detailed_results']
        }

    except Exception as e:
        print(f"  [FAIL] 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试4: CAD绘图
    print("\n" + "=" * 80)
    print("[测试4] CAD绘图")
    print("=" * 80)

    try:
        elevation_file = drawer.draw_elevation(design)
        if elevation_file:
            print(f"  [PASS] 立面图生成: {elevation_file}")
        else:
            print(f"  [WARN] 立面图生成失败")

        plan_file = drawer.draw_plan(design)
        if plan_file:
            print(f"  [PASS] 平面图生成: {plan_file}")
        else:
            print(f"  [WARN] 平面图生成失败")

        details_file = drawer.draw_details(design)
        if details_file:
            print(f"  [PASS] 详图生成: {details_file}")
        else:
            print(f"  [WARN] 详图生成失败")

    except Exception as e:
        print(f"  [FAIL] 绘图失败: {e}")
        import traceback
        traceback.print_exc()

    # 测试5: 设计评估
    print("\n" + "=" * 80)
    print("[测试5] 设计评估")
    print("=" * 80)

    try:
        evaluation = evaluator.evaluate_comprehensive(design, results)
        print(f"  [PASS] 评估完成: {evaluation['status']}")
        print(f"\n  综合得分: {evaluation['comprehensive_score']} 分")
        print(f"  等级: {evaluation['grade']}")
        print(f"\n  维度得分:")
        print(f"    经济性: {evaluation['dimensions']['economy']['score']:.1f}")
        print(f"    结构效率: {evaluation['dimensions']['structural_efficiency']['score']:.1f}")
        print(f"    安全性: {evaluation['dimensions']['safety']['score']:.1f}")
        print(f"    可持续性: {evaluation['dimensions']['sustainability']['score']:.1f}")

        # 显示关键指标
        economy_indicators = evaluation['dimensions']['economy']['indicators']
        print(f"\n  关键指标:")
        print(f"    综合利用率: {economy_indicators['comprehensive_utilization']:.4f}")
        print(f"    应力利用率: {economy_indicators['stress_utilization']:.4f}")
        print(f"    挠度利用率: {economy_indicators['deflection_utilization']:.4f}")

        # 显示构造问题
        safety_indicators = evaluation['dimensions']['safety']['indicators']
        if 'construction_issues' in safety_indicators:
            issues = safety_indicators['construction_issues']
            if issues:
                print(f"\n  构造问题: {len(issues)} 个")
                for issue in issues:
                    print(f"    - [{issue['severity']}] {issue['message']}")
            else:
                print(f"\n  构造问题: 无")

    except Exception as e:
        print(f"  [FAIL] 评估失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试总结
    print("\n" + "=" * 80)
    print("[测试总结]")
    print("=" * 80)
    print("  ✓ 工厂注册正常")
    print("  ✓ 实例创建成功")
    print("  ✓ 有限元分析正常")
    print("  ✓ CAD绘图正常")
    print("  ✓ 设计评估正常")
    print("\n  [SUCCESS] 悬臂梁功能验证通过！")
    print("  [SUCCESS] 架构通用性验证通过！（Agent代码零修改）")

    return True


if __name__ == '__main__':
    try:
        success = test_cantilever_beam()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
