"""
Minimal test for continuous beam - bypasses tool package __init__.py
"""

import sys
import os

# Direct module imports to bypass __init__.py
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import directly from module files
import importlib.util

def load_module_from_file(module_name, file_path):
    """Load a module directly from file path"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Load modules directly
analyzer_path = os.path.join(project_root, 'structural_app', 'tool', 'analyzers', 'continuous_beam_analyzer.py')
ContinuousBeamAnalyzer = load_module_from_file('continuous_beam_analyzer', analyzer_path).ContinuousBeamAnalyzer

evaluator_path = os.path.join(project_root, 'structural_app', 'tool', 'evaluators', 'continuous_beam_evaluator.py')
ContinuousBeamEvaluator = load_module_from_file('continuous_beam_evaluator', evaluator_path).ContinuousBeamEvaluator

drawer_path = os.path.join(project_root, 'structural_app', 'tool', 'drawers', 'continuous_beam_drawer.py')
ContinuousBeamDrawer = load_module_from_file('continuous_beam_drawer', drawer_path).ContinuousBeamDrawer


def test_continuous_beam():
    """Test continuous beam with 2 spans"""
    print("=" * 80)
    print("连续梁结构最小化测试 (2跨)")
    print("=" * 80)

    design = {
        'structure_type': 'continuous_beam',
        'geometry': {
            'length': 12.0,
            'width': 0.3,
            'height': 0.6,
            'n_elements': 40,
            'n_spans': 2
        },
        'material': {
            'E': 30e9,
            'nu': 0.2,
            'fy': 235e6,
            'material_name': 'C30'
        },
        'loads': {
            'distributed': [
                {'q': -10000, 'direction': 'y'}
            ]
        },
        'units': 'm'
    }

    # Test Analyzer
    print("\n[测试 1] 有限元分析")
    print("-" * 80)
    try:
        analyzer = ContinuousBeamAnalyzer()
        print(f"✓ 创建分析器")

        analyzer.build_model(design)
        print(f"✓ 构建模型: {design['geometry']['n_spans']}跨")

        results = analyzer.analyze()
        if results['status'] == 'success':
            print(f"✓ 分析成功")
            print(f"  - 最大位移: {results['max_displacement']*1000:.2f} mm")
            print(f"  - 最大弯矩: {results['max_moment']/1000:.2f} kN·m")
            print(f"  - 最大应力: {results['max_stress_MPa']:.2f} MPa")
        else:
            print(f"✗ 分析失败")
            return False
    except Exception as e:
        print(f"✗ 分析器失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test Drawer
    print("\n[测试 2] CAD绘图")
    print("-" * 80)
    try:
        drawer = ContinuousBeamDrawer()
        print(f"✓ 创建绘图器")

        output_dir = os.path.join(project_root, 'output', 'continuous_beam_test')
        drawer.set_output_directory(output_dir)

        elevation_file = drawer.draw_elevation(design)
        if elevation_file:
            print(f"✓ 立面图: {os.path.basename(elevation_file)}")

        plan_file = drawer.draw_plan(design)
        if plan_file:
            print(f"✓ 平面图: {os.path.basename(plan_file)}")

        detail_file = drawer.draw_details(design)
        if detail_file:
            print(f"✓ 详图: {os.path.basename(detail_file)}")

        print(f"  输出目录: {output_dir}")
    except Exception as e:
        print(f"✗ 绘图器失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test Evaluator
    print("\n[测试 3] 设计评估")
    print("-" * 80)
    try:
        evaluator = ContinuousBeamEvaluator()
        print(f"✓ 创建评估器")

        evaluation = evaluator.evaluate(design, results)
        print(f"\n综合评分: {evaluation['overall_score']:.1f}/100")
        print(f"评级: {evaluation['grade']}")

        safety_data = evaluation['dimension_scores']['safety']
        if 'construction_issues' in safety_data:
            issues = safety_data['construction_issues']
            if issues:
                print(f"\n构造问题: {len(issues)}个")
                for issue in issues:
                    print(f"  - [{issue['severity']}] {issue['message']}")
            else:
                print(f"\n✓ 无构造问题")

    except Exception as e:
        print(f"✗ 评估器失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 80)
    print("✓ 连续梁测试通过!")
    print("=" * 80)
    return True


if __name__ == '__main__':
    try:
        success = test_continuous_beam()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
