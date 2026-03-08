"""
Standalone test for continuous beam (no OpenManus dependencies)
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Direct imports to avoid OpenManus dependencies
from structural_app.tool.analyzers.continuous_beam_analyzer import ContinuousBeamAnalyzer
from structural_app.tool.drawers.continuous_beam_drawer import ContinuousBeamDrawer
from structural_app.tool.evaluators.continuous_beam_evaluator import ContinuousBeamEvaluator


def test_continuous_beam():
    """Test continuous beam with 2 spans"""
    print("=" * 80)
    print("连续梁结构测试 (2跨)")
    print("=" * 80)

    # Define continuous beam design
    design = {
        'structure_type': 'continuous_beam',
        'geometry': {
            'length': 12.0,      # Total length: 12m (2 spans of 6m each)
            'width': 0.3,        # 300mm
            'height': 0.6,       # 600mm
            'n_elements': 40,    # 40 elements total
            'n_spans': 2         # 2 spans
        },
        'material': {
            'E': 30e9,           # 30 GPa (C30 concrete)
            'nu': 0.2,
            'fy': 235e6,         # 235 MPa
            'material_name': 'C30'
        },
        'loads': {
            'distributed': [
                {'q': -10000, 'direction': 'y'}  # 10 kN/m downward
            ]
        },
        'units': 'm'
    }

    # Test 1: Analyzer
    print("\n[测试 1] 有限元分析")
    print("-" * 80)
    try:
        analyzer = ContinuousBeamAnalyzer()
        print(f"✓ 创建分析器: {analyzer.__class__.__name__}")

        analyzer.build_model(design)
        print(f"✓ 构建模型: {design['geometry']['n_spans']}跨, "
              f"{design['geometry']['n_elements']}个单元")

        results = analyzer.analyze()
        if results['status'] == 'success':
            print(f"✓ 分析成功")
            print(f"  - 最大位移: {results['max_displacement']*1000:.2f} mm")
            print(f"  - 最大弯矩: {results['max_moment']/1000:.2f} kN·m")
            print(f"  - 最大剪力: {results['max_shear']/1000:.2f} kN")
            print(f"  - 最大应力: {results['max_stress_MPa']:.2f} MPa")
        else:
            print(f"✗ 分析失败: {results.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"✗ 分析器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Drawer
    print("\n[测试 2] CAD绘图")
    print("-" * 80)
    try:
        drawer = ContinuousBeamDrawer()
        print(f"✓ 创建绘图器: {drawer.__class__.__name__}")

        output_dir = os.path.join(project_root, 'output', 'continuous_beam_test')
        drawer.set_output_directory(output_dir)

        elevation_file = drawer.draw_elevation(design)
        if elevation_file:
            print(f"✓ 立面图: {os.path.basename(elevation_file)}")
        else:
            print(f"✗ 立面图生成失败")

        plan_file = drawer.draw_plan(design)
        if plan_file:
            print(f"✓ 平面图: {os.path.basename(plan_file)}")
        else:
            print(f"✗ 平面图生成失败")

        detail_file = drawer.draw_details(design)
        if detail_file:
            print(f"✓ 详图: {os.path.basename(detail_file)}")
        else:
            print(f"✗ 详图生成失败")

        print(f"  输出目录: {output_dir}")
    except Exception as e:
        print(f"✗ 绘图器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Evaluator
    print("\n[测试 3] 设计评估")
    print("-" * 80)
    try:
        evaluator = ContinuousBeamEvaluator()
        print(f"✓ 创建评估器: {evaluator.__class__.__name__}")

        evaluation = evaluator.evaluate(design, results)

        print(f"\n综合评分: {evaluation['overall_score']:.1f}/100")
        print(f"评级: {evaluation['grade']}")
        print(f"\n维度评分:")
        for dim, data in evaluation['dimension_scores'].items():
            print(f"  - {dim}: {data['score']:.1f}/100 (权重: {data['weight']*100:.0f}%)")

        # Check construction issues
        safety_data = evaluation['dimension_scores']['safety']
        if 'construction_issues' in safety_data:
            issues = safety_data['construction_issues']
            if issues:
                print(f"\n构造问题: {len(issues)}个")
                for issue in issues:
                    print(f"  - [{issue['severity']}] {issue['message']}")
                    print(f"    建议: {issue['recommendation']}")
            else:
                print(f"\n✓ 无构造问题")

        print(f"\n是否合规: {'是' if evaluation['compliant'] else '否'}")

    except Exception as e:
        print(f"✗ 评估器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 80)
    print("✓ 所有测试通过!")
    print("=" * 80)
    return True


def test_continuous_beam_3_spans():
    """Test continuous beam with 3 spans"""
    print("\n\n" + "=" * 80)
    print("连续梁结构测试 (3跨)")
    print("=" * 80)

    design = {
        'structure_type': 'continuous_beam',
        'geometry': {
            'length': 18.0,      # Total length: 18m (3 spans of 6m each)
            'width': 0.35,       # 350mm
            'height': 0.7,       # 700mm
            'n_elements': 60,    # 60 elements total
            'n_spans': 3         # 3 spans
        },
        'material': {
            'E': 30e9,
            'nu': 0.2,
            'fy': 235e6,
            'material_name': 'C30'
        },
        'loads': {
            'distributed': [
                {'q': -12000, 'direction': 'y'}  # 12 kN/m downward
            ]
        },
        'units': 'm'
    }

    print("\n[快速测试] 3跨连续梁")
    print("-" * 80)
    try:
        # Analyzer
        analyzer = ContinuousBeamAnalyzer()
        analyzer.build_model(design)
        results = analyzer.analyze()

        if results['status'] == 'success':
            print(f"✓ 分析成功 (3跨)")
            print(f"  - 最大位移: {results['max_displacement']*1000:.2f} mm")
            print(f"  - 最大弯矩: {results['max_moment']/1000:.2f} kN·m")

            # Evaluator
            evaluator = ContinuousBeamEvaluator()
            evaluation = evaluator.evaluate(design, results)
            print(f"✓ 评估完成: {evaluation['overall_score']:.1f}/100 ({evaluation['grade']})")
        else:
            print(f"✗ 分析失败")
            return False

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✓ 3跨连续梁测试通过!")
    return True


if __name__ == '__main__':
    try:
        # Test 2-span continuous beam
        success1 = test_continuous_beam()

        # Test 3-span continuous beam
        success2 = test_continuous_beam_3_spans()

        if success1 and success2:
            print("\n" + "=" * 80)
            print("✓✓✓ 连续梁结构完整测试通过! ✓✓✓")
            print("=" * 80)
            sys.exit(0)
        else:
            print("\n✗ 部分测试失败")
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
