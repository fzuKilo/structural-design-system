"""
Test frame structure complete workflow
Tests all 5 components: Analyzer, Drawer, Visualizer, Evaluator, Reporter
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from structural_app.tool.analyzers.analyzer_factory import AnalyzerFactory
from structural_app.tool.drawers.drawer_factory import DrawerFactory
from structural_app.tool.visualizations.visualizer_factory import VisualizerFactory
from structural_app.tool.evaluators.evaluator_factory import EvaluatorFactory
from structural_app.tool.reports.reporter_factory import ReporterFactory


def test_frame_complete_workflow():
    """Test complete workflow for frame structure"""

    # Design parameters for a 2-bay 3-story frame
    design = {
        "type": "frame",
        "geometry": {
            "num_bays": 2,
            "num_stories": 3,
            "bay_widths": [6.0, 6.0],  # meters
            "story_heights": [4.0, 3.5, 3.5],  # meters
            "columns": {
                "type": "rectangular",
                "width": 0.4,  # meters
                "depth": 0.4   # meters
            },
            "beams": {
                "type": "rectangular",
                "width": 0.3,  # meters
                "depth": 0.6   # meters
            }
        },
        "material": {
            "E": 200e9,  # Pa (200 GPa for steel)
            "nu": 0.3,
            "fy": 235e6,  # Pa (Q235 steel)
            "material_name": "Q235"
        },
        "loads": {
            "beam_distributed": [
                {"story": 1, "bay": 0, "q": -10.0, "direction": "y"},  # kN/m
                {"story": 1, "bay": 1, "q": -10.0, "direction": "y"},
                {"story": 2, "bay": 0, "q": -8.0, "direction": "y"},
                {"story": 2, "bay": 1, "q": -8.0, "direction": "y"},
                {"story": 3, "bay": 0, "q": -8.0, "direction": "y"},
                {"story": 3, "bay": 1, "q": -8.0, "direction": "y"}
            ],
            "lateral": [
                {"story": 1, "F": 20.0},  # kN (wind/seismic)
                {"story": 2, "F": 15.0},
                {"story": 3, "F": 10.0}
            ]
        },
        "boundary": {
            "column_base": "fixed"
        },
        "units": "m"
    }

    print("=" * 80)
    print("框架结构完整流程测试")
    print("=" * 80)
    print()

    # Step 1: Analysis
    print("Step 1: 有限元分析 (FrameAnalyzer)")
    print("-" * 80)
    try:
        analyzer = AnalyzerFactory.create("frame")
        results = analyzer.analyze(design)

        if results.get('status') == 'success':
            print("✓ 分析成功")
            analysis_results = results.get('results', {})
            print(f"  - 最大位移: {analysis_results.get('max_displacement_mm', 0):.3f} mm")
            print(f"  - 最大应力: {analysis_results.get('max_stress_MPa', 0):.2f} MPa")
            print(f"  - 最大层间位移角: {analysis_results.get('max_drift_ratio', 0):.6f}")
        else:
            print(f"✗ 分析失败: {results.get('message', 'Unknown error')}")
            return
    except Exception as e:
        print(f"✗ 分析异常: {e}")
        return

    print()

    # Step 2: Drawing
    print("Step 2: CAD绘图 (FrameDrawer)")
    print("-" * 80)
    try:
        drawer = DrawerFactory.create("frame")

        # Draw elevation
        elevation_file = drawer.draw_elevation(design)
        if elevation_file:
            print(f"✓ 立面图生成成功: {elevation_file}")
        else:
            print("✗ 立面图生成失败")

        # Draw detail
        detail_file = drawer.draw_detail(design)
        if detail_file:
            print(f"✓ 详图生成成功: {detail_file}")
        else:
            print("✗ 详图生成失败")

    except Exception as e:
        print(f"✗ 绘图异常: {e}")

    print()

    # Step 3: Visualization
    print("Step 3: 可视化 (FrameVisualizer)")
    print("-" * 80)
    try:
        visualizer = VisualizerFactory.create("frame")

        # Generate static visualizations
        vis_files = visualizer.generate_static_visualizations(design, results)
        if vis_files:
            print(f"✓ 生成了 {len(vis_files)} 个可视化文件:")
            for vis_type, file_path in vis_files.items():
                print(f"  - {vis_type}: {file_path}")
        else:
            print("✗ 可视化生成失败")

    except Exception as e:
        print(f"✗ 可视化异常: {e}")

    print()

    # Step 4: Evaluation
    print("Step 4: 设计评估 (FrameEvaluator)")
    print("-" * 80)
    try:
        evaluator = EvaluatorFactory.create("frame")
        evaluation = evaluator.evaluate_comprehensive(design, results)

        if evaluation.get('status') == 'success':
            print("✓ 评估成功")
            print(f"  - 综合评分: {evaluation.get('comprehensive_score', 0):.1f} / 100")
            print(f"  - 评估等级: {evaluation.get('grade', 'N/A')}")

            dimensions = evaluation.get('dimensions', {})
            print(f"  - 经济性: {dimensions.get('economy', {}).get('score', 0):.1f}")
            print(f"  - 结构效率: {dimensions.get('structural_efficiency', {}).get('score', 0):.1f}")
            print(f"  - 安全性: {dimensions.get('safety', {}).get('score', 0):.1f}")
            print(f"  - 可持续性: {dimensions.get('sustainability', {}).get('score', 0):.1f}")
        else:
            print(f"✗ 评估失败: {evaluation.get('message', 'Unknown error')}")
            evaluation = None

    except Exception as e:
        print(f"✗ 评估异常: {e}")
        evaluation = None

    print()

    # Step 5: Report
    print("Step 5: 报告生成 (FrameReporter)")
    print("-" * 80)
    try:
        reporter = ReporterFactory.create("frame")

        # Collect drawing files
        drawings = {
            'files': {
                'elevation': elevation_file if 'elevation_file' in locals() else None,
                'detail': detail_file if 'detail_file' in locals() else None
            }
        }

        report_file = reporter.generate_report(design, results, evaluation, drawings)
        if report_file:
            print(f"✓ 报告生成成功: {report_file}")
        else:
            print("✗ 报告生成失败")

    except Exception as e:
        print(f"✗ 报告生成异常: {e}")

    print()
    print("=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_frame_complete_workflow()
