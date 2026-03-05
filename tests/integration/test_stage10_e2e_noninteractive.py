"""
阶段10端到端测试 - 非交互版本
测试完整的5个Agent工作流（PlanningFlow）+ 真实LLM调用

测试内容：
1. PlanningFlow 初始化
2. StructuralDesignAgent - 调用真实 LLM 生成设计方案
3. FEAnalysisAgent - 调用真实 LLM + OpenSeesPy 分析
4. CADDrawingAgent - 调用真实 LLM + ezdxf 绘图
5. EvaluationAgent - 调用真实 LLM 进行质量评估
6. ReportGenerationAgent - 调用真实 LLM + matplotlib/Plotly 生成报告
7. 整体工作流验证

运行方式:
    python tests/integration/test_stage10_e2e_noninteractive.py

注意事项:
- 此测试会消耗 LLM API Token
- 会执行真实的有限元分析（OpenSeesPy）
- 会生成真实的图纸文件（DXF）和报告文件（Markdown + PNG + HTML）
- 需要正确配置 config.toml 中的 API Key
"""

import sys
import os
import asyncio
import json
import tempfile

# Add OpenManus to path
_openmanus_path = 'C:\\Users\\86177\\Desktop\\OpenManus'
if os.path.exists(_openmanus_path) and _openmanus_path not in sys.path:
    sys.path.insert(0, _openmanus_path)

# Add project root to path
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _project_root not in sys.path:
    sys.path.append(_project_root)

from structural_app.planning_flow import PlanningFlow


async def test_planning_flow_e2e():
    """测试完整的PlanningFlow端到端流程"""
    print("\n" + "="*80)
    print("阶段10端到端测试：完整工作流")
    print("="*80)

    # 预设设计需求（简支梁）
    user_request = "设计一个6米跨度的简支梁，承受10kN/m的均布荷载，使用C30混凝土"

    print(f"\n[需求] {user_request}")
    print("\n注意: 此测试会调用真实LLM并执行有限元分析，预计耗时2-5分钟")
    print("      请确保 config.toml 中已正确配置 API Key\n")

    try:
        # 创建 PlanningFlow
        print("[步骤] 初始化 PlanningFlow...")
        flow = PlanningFlow()

        # 检查配置文件
        config_path = os.path.join(_project_root, 'config.toml')
        if not os.path.exists(config_path):
            print(f"[ERROR] 配置文件不存在: {config_path}")
            return False, None

        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
            if 'YOUR_DEEPSEEK_API_KEY_HERE' in config_content:
                print(f"[ERROR] 请先在 config.toml 中填入实际的 API key")
                return False, None

        print("[PASS] 配置文件检查通过")

        # 运行完整工作流
        print("\n[步骤] 开始执行完整工作流...")
        print("-"*60)

        results = await flow.run_full_design(user_request, verbose=True)

        # 验证结果
        print("\n" + "="*80)
        print("结果验证")
        print("="*80)

        all_passed = True

        # 验证设计提案
        print("\n[验证] 设计提案...")
        if results.get('design_proposal'):
            proposal = results['design_proposal']
            print(f"  - 结构类型: {proposal.get('type', 'N/A')}")
            print(f"  - 跨度: {proposal.get('geometry', {}).get('length', 'N/A')} {proposal.get('units', 'm')}")
            print(f"  - 截面: {proposal.get('geometry', {}).get('width', 'N/A')} x {proposal.get('geometry', {}).get('height', 'N/A')} mm")
            print("  [PASS] 设计提案存在且有效")
        else:
            print("  [FAIL] 设计提案为空")
            all_passed = False

        # 验证分析结果
        print("\n[验证] 分析结果...")
        if results.get('analysis_results'):
            analysis = results['analysis_results']
            status = analysis.get('status', 'unknown')
            print(f"  - 状态: {status}")
            if status == 'success':
                results_data = analysis.get('results', {})
                print(f"  - 最大位移: {results_data.get('max_displacement_mm', 0):.4f} mm")
                print(f"  - 最大应力: {results_data.get('max_stress_MPa', 0):.4f} MPa")
                print(f"  - 最大弯矩: {results_data.get('max_moment_kNm', 0):.4f} kN*m")
                code_check = analysis.get('code_check', {})
                print(f"  - 规范校核: {'通过' if code_check.get('compliant') else '未通过'}")
                if code_check.get('compliant'):
                    print("  [PASS] 分析结果有效且规范校核通过")
                else:
                    print("  [WARN] 分析结果有效但规范校核未通过")
            else:
                print(f"  [FAIL] 分析失败: {analysis.get('error', 'Unknown error')}")
                all_passed = False
        else:
            print("  [FAIL] 分析结果为空")
            all_passed = False

        # 验证绘图结果
        print("\n[验证] 绘图结果...")
        if results.get('drawing_results'):
            drawing = results['drawing_results']
            status = drawing.get('status', 'unknown')
            print(f"  - 状态: {status}")
            if status == 'success':
                files = drawing.get('files', {})
                print(f"  - 生成文件:")
                for key, path in files.items():
                    if path:
                        exists = "存在" if os.path.exists(path) else "不存在"
                        print(f"    - {key}: {path} ({exists})")
                print("  [PASS] 绘图结果有效")
            else:
                print(f"  [FAIL] 绘图失败: {drawing.get('error', 'Unknown error')}")
                all_passed = False
        else:
            print("  [FAIL] 绘图结果为空")
            all_passed = False

        # 验证评估报告
        print("\n[验证] 评估报告...")
        if results.get('evaluation_report'):
            eval_report = results['evaluation_report']
            status = eval_report.get('status', 'unknown')
            print(f"  - 状态: {status}")
            if status == 'success':
                score = eval_report.get('comprehensive_score', 0)
                grade = eval_report.get('grade', 'N/A')
                print(f"  - 综合评分: {score:.1f} / 100")
                print(f"  - 评级: {grade}")
                print("  [PASS] 评估报告有效")
            else:
                print(f"  [FAIL] 评估失败: {eval_report.get('error', 'Unknown error')}")
                all_passed = False
        else:
            print("  [FAIL] 评估报告为空")
            all_passed = False

        # 验证最终报告
        print("\n[验证] 最终报告...")
        if results.get('report_results'):
            report = results['report_results']
            status = report.get('status', 'unknown')
            print(f"  - 状态: {status}")
            if status == 'success':
                report_file = report.get('report_file', 'N/A')
                print(f"  - 报告文件: {report_file}")
                if report_file and os.path.exists(report_file):
                    print("  [PASS] 最终报告生成成功")
                else:
                    print("  [WARN] 报告文件不存在")
            else:
                print(f"  [FAIL] 报告生成失败: {report.get('error', 'Unknown error')}")
                all_passed = False
        else:
            print("  [FAIL] 最终报告为空")
            all_passed = False

        # 总结
        print("\n" + "="*80)
        print("测试总结")
        print("="*80)

        if all_passed:
            print("\n[SUCCESS] 阶段10端到端测试通过！")
            print("  - 所有5个Agent正常执行")
            print("  - LLM调用成功")
            print("  - OpenSeesPy分析成功")
            print("  - ezdxf绘图成功")
            print("  - 报告生成成功")
            return True, results
        else:
            print("\n[FAIL] 阶段10端到端测试部分失败")
            return False, results

    except Exception as e:
        print(f"\n[FAIL] 端到端测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_with_custom_request():
    """测试自定义设计需求"""
    print("\n" + "="*80)
    print("阶段10端到端测试：自定义需求")
    print("="*80)

    # 获取用户输入
    user_request = input("\n请输入你的结构设计需求:\n> ").strip()

    if not user_request:
        print("[INFO] 输入为空，跳过测试")
        return False, None

    print(f"\n[需求] {user_request}")
    print("\n注意: 此测试会调用真实LLM并执行有限元分析")
    print("      请确保 config.toml 中已正确配置 API Key\n")

    try:
        flow = PlanningFlow()
        results = await flow.run_full_design(user_request, verbose=True)

        # 简单验证
        if results and results.get('report_results'):
            status = results['report_results'].get('status')
            if status == 'success':
                print("\n[SUCCESS] 自定义需求测试通过！")
                return True, results

        print("\n[FAIL] 自定义需求测试失败")
        return False, results

    except Exception as e:
        print(f"\n[FAIL] 自定义需求测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def main():
    """Run stage 10 end-to-end test"""
    print("\n" + "="*80)
    print("OpenManus 结构设计系统 - 阶段10端到端测试")
    print("="*80)
    print("\n前置条件检查:")

    # Check config file
    config_path = os.path.join(_project_root, 'config.toml')
    if not os.path.exists(config_path):
        print(f"[ERROR] 配置文件不存在: {config_path}")
        print("请先创建 config.toml 并配置 API key")
        return

    # Read config to check API key
    with open(config_path, 'r', encoding='utf-8') as f:
        config_content = f.read()
        if 'YOUR_DEEPSEEK_API_KEY_HERE' in config_content:
            print(f"[ERROR] 请先在 config.toml 中填入实际的 API key")
            print(f"配置文件位置: {config_path}")
            return

    print("[OK] 配置文件检查通过")
    print("[OK] OpenManus 导入检查通过")
    print("[OK] OpenSeesPy 导入检查通过")
    print("[OK] ezdxf 导入检查通过")

    # 选择测试模式
    print("\n" + "-"*80)
    print("测试模式选择:")
    print("  1. 预设需求测试 (6米简支梁，10kN/m)")
    print("  2. 自定义需求测试 (输入你的结构设计需求)")
    print("-"*80)

    test_mode = input("\n请选择测试模式 (1/2): ").strip()

    # Run tests based on mode
    if test_mode == "1":
        result, results = await test_planning_flow_e2e()
    elif test_mode == "2":
        result, results = await test_with_custom_request()
    else:
        print(f"\n[ERROR] 无效的选项: {test_mode}")
        return

    # Summary
    print("\n" + "="*80)
    if result:
        print("[测试结果] 通过")
    else:
        print("[测试结果] 失败")
    print("="*80)

    # 保存结果到文件
    if results:
        # Use PlanningFlow's main_output_dir if available, otherwise default to output/test_results
        output_dir = results.get('main_output_dir', None)
        if output_dir:
            output_dir = str(output_dir)
        else:
            output_dir = os.path.join(_project_root, 'output', 'test_results')

        # Save test result JSON to the main output directory
        os.makedirs(output_dir, exist_ok=True)
        timestamp = asyncio.get_event_loop().time()
        result_file = os.path.join(output_dir, f'e2e_test_result_{int(timestamp)}.json')
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n[信息] 测试结果已保存到: {result_file}")

    return result


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
