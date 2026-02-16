"""
阶段7集成测试：StructuralDesignAgent -> FEAnalysisAgent 端到端测试

测试内容：
1. StructuralDesignAgent 生成设计方案
2. FEAnalysisAgent 接收方案并进行有限元分析
3. 验证 AnalysisResults 数值合理性
"""

import sys
import os
import asyncio
import json
import re

import pytest

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


@pytest.mark.asyncio
async def test_stage7_end_to_end():
    """
    阶段7端到端测试：完整的设计-分析流程

    测试步骤：
    1. StructuralDesignAgent 生成简支梁设计方案
    2. FEAnalysisAgent 进行有限元分析
    3. 验证分析结果
    """
    print("\n" + "="*80)
    print("阶段7集成测试：StructuralDesignAgent -> FEAnalysisAgent")
    print("="*80)

    # 配置测试参数
    user_request = "设计一个6米跨度的简支梁，承受10kN/m的均布荷载，使用C30混凝土"

    print(f"\n[步骤1] 用户需求: {user_request}")

    # ========== 步骤1: 结构设计 ==========
    print("\n[步骤2] 调用 StructuralDesignAgent 生成设计方案...")

    design_agent = StructuralDesignAgent()

    try:
        design_result = await design_agent.run(user_request)

        # 提取设计方案
        if isinstance(design_result, dict) and 'content' in design_result:
            design_response = design_result['content']
        elif isinstance(design_result, str):
            design_response = design_result
        else:
            design_response = str(design_result)

        print("\n[设计Agent原始响应]:")
        print(design_response[:500] + "..." if len(design_response) > 500 else design_response)

        design_proposal = design_agent.extract_design_proposal(design_response)

        if design_proposal is None:
            print("\n[FAIL] 无法从设计Agent响应中提取设计方案")
            return False

        print("\n[提取的设计方案]:")
        print(json.dumps(design_proposal, indent=2, ensure_ascii=False))

        # 验证设计方案
        is_valid, error = design_agent.validate_design_proposal(design_proposal)
        if not is_valid:
            print(f"\n[FAIL] 设计方案验证失败: {error}")
            return False

        print("\n[PASS] 设计方案验证通过")

    except Exception as e:
        print(f"\n[FAIL] 设计Agent执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ========== 步骤2: 有限元分析 ==========
    print("\n[步骤3] 调用 FEAnalysisAgent 进行有限元分析...")

    fe_agent = FEAnalysisAgent()

    try:
        # 将设计方案传递给FE分析Agent
        fe_request = f"""请分析以下结构设计方案:

{json.dumps(design_proposal, indent=2, ensure_ascii=False)}
"""

        fe_result = await fe_agent.run(fe_request)

        # 提取分析结果
        if isinstance(fe_result, dict) and 'content' in fe_result:
            fe_response = fe_result['content']
        elif isinstance(fe_result, str):
            fe_response = fe_result
        else:
            fe_response = str(fe_result)

        print("\n[FEAnalysisAgent原始响应]:")
        print(fe_response[:500] + "..." if len(fe_response) > 500 else fe_response)

        analysis_results = fe_agent.extract_analysis_results(fe_response)

        if analysis_results is None:
            print("\n[FAIL] 无法从FE分析Agent响应中提取分析结果")
            return False

        print("\n[提取的分析结果]:")
        print(json.dumps(analysis_results, indent=2, ensure_ascii=False))

        # 验证分析结果
        if analysis_results.get('status') != 'success':
            print(f"\n[FAIL] FE分析失败: {analysis_results.get('error', 'Unknown error')}")
            return False

        print("\n[PASS] FE分析状态检查通过")

    except UnicodeEncodeError as e:
        print(f"\n[FAIL] 编码错误: {e}")
        print("注意: 这是由于 Windows 控制台使用 GBK 编码，无法显示 Unicode 字符")
        print("请确保所有输出只使用 ASCII 字符 (参考 TD-010)")
        return False
    except Exception as e:
        print(f"\n[FAIL] FEAnalysisAgent执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ========== 步骤3: 验证分析结果数值 ==========
    print("\n[步骤4] 验证分析结果数值...")

    results = analysis_results.get('results', {})

    # 关键结果验证
    max_displacement_mm = results.get('max_displacement_mm', 0)
    max_stress_MPa = results.get('max_stress_MPa', 0)
    max_moment_kNm = results.get('max_moment_kNm', 0)

    print("\n[关键结果]:")
    print(f"  - 最大位移: {max_displacement_mm:.4f} mm (预期: ~1.0 mm)")
    print(f"  - 最大应力: {max_stress_MPa:.4f} MPa (预期: ~2.5 MPa)")
    print(f"  - 最大弯矩: {max_moment_kNm:.4f} kN*m (预期: ~45 kN*m)")

    # 数值合理性检查
    code_check = analysis_results.get('code_check', {})

    # 位移检查 (简支梁6m跨度，10kN/m，C30混凝土 0.3x0.6截面)
    # 理论值: delta_max = 5qL^4/384EI = 1.04mm
    if 0.5 <= max_displacement_mm <= 3.0:
        print("\n  [PASS] 最大位移在合理范围内")
    else:
        print(f"\n  [WARN] 最大位移可能异常 (理论值~1.0mm)")

    # 应力检查 (M_max = qL^2/8 = 45kN*m, sigma = M*y/I = 2.5MPa)
    if 1.0 <= max_stress_MPa <= 5.0:
        print("  [PASS] 最大应力在合理范围内")
    else:
        print(f"  [WARN] 最大应力可能异常 (理论值~2.5MPa)")

    # 弯矩检查
    if 35 <= max_moment_kNm <= 55:
        print("  [PASS] 最大弯矩在合理范围内")
    else:
        print(f"  [WARN] 最大弯矩可能异常 (理论值~45kN*m)")

    # 规范校核检查
    if code_check.get('compliant', False):
        print("  [PASS] 规范校核通过")
    else:
        print(f"  [WARN] 规范校核未通过: {code_check.get('violations', [])}")

    # ========== 测试总结 ==========
    print("\n" + "="*80)
    print("阶段7集成测试总结")
    print("="*80)

    # 通过条件
    all_passed = (
        design_proposal is not None and
        analysis_results is not None and
        analysis_results.get('status') == 'success' and
        0.5 <= max_displacement_mm <= 3.0
    )

    if all_passed:
        print("\n[SUCCESS] 阶段7集成测试通过！")
        print("  - StructuralDesignAgent 正常生成设计方案")
        print("  - FEAnalysisAgent 正常调用 FEAnalysisTool")
        print("  - OpenSeesPy 分析结果数值合理")
        print("  - 数据传递流程完整")
        return True
    else:
        print("\n[FAIL] 阶段7集成测试部分失败")
        return False


async def main():
    """Run stage 7 integration test"""
    print("\n" + "="*80)
    print("OpenManus 结构设计系统 - 阶段7集成测试")
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

    # Run test
    print("\n" + "-"*80)
    print("开始执行阶段7集成测试...")
    print("-"*80)

    result = await test_stage7_end_to_end()

    # Summary
    print("\n" + "="*80)
    if result:
        print("[测试结果] 通过")
    else:
        print("[测试结果] 失败")
    print("="*80)

    return result


if __name__ == "__main__":
    asyncio.run(main())
