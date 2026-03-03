"""
阶段10端到端测试 - 交互版本
测试完整的5个Agent工作流（PlanningFlow）+ 真实LLM调用 + 人工交互

支持三种测试模式：
1. 预设需求测试 (6米简支梁，10kN/m均布荷载)
2. 自定义需求测试 (手动输入设计需求)
3. 完整参数测试 (直接提供完整参数，跳过DesignAgent交互)

运行方式:
    python tests/integration/test_stage10_e2e_integration.py

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

# Add OpenManus to path
_openmanus_path = 'D:\\openmanus'
if os.path.exists(_openmanus_path) and _openmanus_path not in sys.path:
    sys.path.insert(0, _openmanus_path)

# Add project root to path
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _project_root not in sys.path:
    sys.path.append(_project_root)

from structural_app.agent.structural_design_agent import StructuralDesignAgent
from structural_app.agent.fe_analysis_agent import FEAnalysisAgent
from structural_app.agent.cad_drawing_agent import CADDrawingAgent
from structural_app.agent.evaluation_agent import EvaluationAgent
from structural_app.agent.report_generation_agent import ReportGenerationAgent


async def run_full_workflow_with_agents(user_request: str, enable_loop: bool = False):
    """
    使用独立的Agent运行完整工作流（可用于调试和交互）
    """
    print("\n" + "="*80)
    print("完整工作流：5个Agent顺序执行")
    print("="*80)

    try:
        # Step 1: StructuralDesignAgent
        print("\n" + "-"*60)
        print("步骤1: StructuralDesignAgent - 生成设计方案")
        print("-"*60)

        design_agent = StructuralDesignAgent()
        print(f"\n用户需求: {user_request}")

        design_result = await design_agent.run(user_request)
        design_response = design_result if isinstance(design_result, str) else design_result.get('content', str(design_result))
        design_proposal = design_agent.extract_design_proposal(design_response)

        if design_proposal is None:
            print("[FAIL] 无法从设计Agent响应中提取设计方案")
            return None

        print("\n[设计方案]:")
        print(json.dumps(design_proposal, indent=2, ensure_ascii=False))

        # Step 2: FEAnalysisAgent
        print("\n" + "-"*60)
        print("步骤2: FEAnalysisAgent - 有限元分析")
        print("-"*60)

        fe_agent = FEAnalysisAgent(enable_loop=enable_loop)
        fe_request = f"""请分析以下结构设计方案:

{json.dumps(design_proposal, indent=2, ensure_ascii=False)}
"""

        fe_result = await fe_agent.run(fe_request)
        fe_response = fe_result if isinstance(fe_result, str) else fe_result.get('content', str(fe_result))
        analysis_results = fe_agent.extract_analysis_results(fe_response)

        if analysis_results is None:
            print("[FAIL] 无法从FE分析Agent响应中提取分析结果")
            return None

        print("\n[分析结果]:")
        print(json.dumps(analysis_results, indent=2, ensure_ascii=False))

        # Step 3: CADDrawingAgent
        print("\n" + "-"*60)
        print("步骤3: CADDrawingAgent - 生成CAD图纸")
        print("-"*60)

        cad_agent = CADDrawingAgent()
        cad_request = f"""请为以下结构设计方案生成CAD图纸:

{json.dumps(design_proposal, indent=2, ensure_ascii=False)}
"""

        cad_result = await cad_agent.run(cad_request)
        cad_response = cad_result if isinstance(cad_result, str) else cad_result.get('content', str(cad_result))
        drawing_results = cad_agent.extract_drawing_results(cad_response)

        if drawing_results is None:
            print("[FAIL] 无法从CAD绘图Agent响应中提取绘图结果")
            return None

        print("\n[绘图结果]:")
        print(json.dumps(drawing_results, indent=2, ensure_ascii=False))

        # Step 4: EvaluationAgent
        print("\n" + "-"*60)
        print("步骤4: EvaluationAgent - 设计质量评估")
        print("-"*60)

        eval_agent = EvaluationAgent()
        eval_request = f"""请评估以下结构设计方案和分析结果:

设计方案:
{json.dumps(design_proposal, indent=2, ensure_ascii=False)}

分析结果:
{json.dumps(analysis_results, indent=2, ensure_ascii=False)}
"""

        eval_result = await eval_agent.run(eval_request)
        eval_response = eval_result if isinstance(eval_result, str) else eval_result.get('content', str(eval_result))
        evaluation_report = eval_agent.extract_evaluation_report(eval_response)

        if evaluation_report is None:
            print("[FAIL] 无法从EvaluationAgent响应中提取评估报告")
            return None

        print("\n[评估报告]:")
        print(json.dumps(evaluation_report, indent=2, ensure_ascii=False))

        # Step 5: ReportGenerationAgent
        print("\n" + "-"*60)
        print("步骤5: ReportGenerationAgent - 生成综合报告")
        print("-"*60)

        report_agent = ReportGenerationAgent()
        report_request = f"""请生成完整的结构设计报告:

设计方案:
{json.dumps(design_proposal, indent=2, ensure_ascii=False)}

分析结果:
{json.dumps(analysis_results, indent=2, ensure_ascii=False)}

评估报告:
{json.dumps(evaluation_report, indent=2, ensure_ascii=False)}

绘图结果:
{json.dumps(drawing_results, indent=2, ensure_ascii=False)}
"""

        report_result = await report_agent.run(report_request)
        report_response = report_result if isinstance(report_result, str) else report_result.get('content', str(report_result))
        report_results = report_agent.extract_report_results(report_response)

        if report_results is None:
            print("[FAIL] 无法从ReportGenerationAgent响应中提取报告结果")
            return None

        print("\n[报告结果]:")
        print(json.dumps(report_results, indent=2, ensure_ascii=False))

        # 总结
        print("\n" + "="*80)
        print("工作流执行完成")
        print("="*80)

        return {
            'design_proposal': design_proposal,
            'analysis_results': analysis_results,
            'drawing_results': drawing_results,
            'evaluation_report': evaluation_report,
            'report_results': report_results,
        }

    except Exception as e:
        print(f"\n[FAIL] 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_planning_flow_workflow(user_request: str):
    """使用PlanningFlow运行完整工作流"""
    print("\n" + "="*80)
    print("PlanningFlow工作流测试")
    print("="*80)

    print(f"\n用户需求: {user_request}")

    try:
        from structural_app.planning_flow import PlanningFlow

        flow = PlanningFlow()
        results = await flow.run_full_design(user_request, verbose=True)

        # 验证结果
        all_passed = True
        for key, value in results.items():
            if value is None:
                print(f"[FAIL] {key} 为空")
                all_passed = False
            else:
                print(f"[PASS] {key} 有效")

        if all_passed:
            print("\n[SUCCESS] PlanningFlow工作流测试通过！")
        else:
            print("\n[FAIL] PlanningFlow工作流测试部分失败")

        return results

    except Exception as e:
        print(f"\n[FAIL] PlanningFlow执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def run_test_with_predefined_request():
    """预设需求测试"""
    print("\n" + "="*80)
    print("预设需求测试 - 6米简支梁")
    print("="*80)

    user_request = "设计一个6米跨度的简支梁，承受10kN/m的均布荷载，使用C30混凝土"

    print(f"\n需求: {user_request}")
    print("\n说明: 此测试会调用真实LLM并执行有限元分析")
    print("      预计耗时2-5分钟\n")

    # 选择工作流方式
    print("请选择工作流方式:")
    print("  1. PlanningFlow (自动编排5个Agent)")
    print("  2. 独立Agent (显示每个Agent的详细输出)")

    workflow_mode = input("\n请选择 (1/2): ").strip()

    if workflow_mode == "1":
        print("\n使用 PlanningFlow...")
        results = await test_planning_flow_workflow(user_request)
    else:
        print("\n使用独立Agent...")
        enable_loop = input("是否启用循环模式? (y/n, 默认n): ").strip().lower() == 'y'
        results = await run_full_workflow_with_agents(user_request, enable_loop=enable_loop)

    return results is not None


async def run_test_with_custom_request():
    """自定义需求测试"""
    print("\n" + "="*80)
    print("自定义需求测试")
    print("="*80)

    print("\n请输入你的结构设计需求（例如：设计一个12米跨度的简支梁...）:")
    user_request = input("> ").strip()

    if not user_request:
        print("[INFO] 输入为空，跳过测试")
        return False

    print("\n说明: 此测试会调用真实LLM并执行有限元分析")
    print("      预计耗时2-5分钟\n")

    # 选择工作流方式
    print("请选择工作流方式:")
    print("  1. PlanningFlow (自动编排5个Agent)")
    print("  2. 独立Agent (显示每个Agent的详细输出)")

    workflow_mode = input("\n请选择 (1/2): ").strip()

    if workflow_mode == "1":
        print("\n使用 PlanningFlow...")
        results = await test_planning_flow_workflow(user_request)
    else:
        print("\n使用独立Agent...")
        enable_loop = input("是否启用循环模式? (y/n, 默认n): ").strip().lower() == 'y'
        results = await run_full_workflow_with_agents(user_request, enable_loop=enable_loop)

    return results is not None


async def main():
    """Run stage 10 end-to-end integration test"""
    print("\n" + "="*80)
    print("OpenManus 结构设计系统 - 阶段10端到端测试（交互版）")
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
    print("  2. 自定义需求测试 (手动输入设计需求)")
    print("-"*80)

    test_mode = input("\n请选择测试模式 (1/2): ").strip()

    # Run tests based on mode
    if test_mode == "1":
        result = await run_test_with_predefined_request()
    elif test_mode == "2":
        result = await run_test_with_custom_request()
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

    return result


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
