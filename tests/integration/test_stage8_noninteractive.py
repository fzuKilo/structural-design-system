"""
阶段8集成测试 - 非交互版本
用于自动化测试，不依赖用户输入
"""

import sys
import os
import asyncio
import json
import pytest

# Add OpenManus to path
_openmanus_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'OpenManus')
if os.path.exists(_openmanus_path) and _openmanus_path not in sys.path:
    sys.path.insert(0, _openmanus_path)

# Add project root to path
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _project_root not in sys.path:
    sys.path.append(_project_root)

from structural_app.agent.structural_design_agent import StructuralDesignAgent
from structural_app.agent.fe_analysis_agent import FEAnalysisAgent
from structural_app.agent.cad_drawing_agent import CADDrawingAgent


@pytest.mark.asyncio
async def test_design_agent():
    """测试 StructuralDesignAgent 能否正确返回 JSON"""
    print("\n" + "="*80)
    print("测试 StructuralDesignAgent")
    print("="*80)

    user_request = "设计一个6米跨度的简支梁，承受10kN/m的均布荷载，使用C30混凝土"

    design_agent = StructuralDesignAgent()

    print(f"\n用户需求: {user_request}")

    try:
        # 设置 max_iterations=1 来快速测试
        result = await design_agent.run(user_request)

        print("\n[Agent 原始响应]:")
        print(result[:500] + "..." if len(result) > 500 else result)

        # 提取设计方案
        design_proposal = design_agent.extract_design_proposal(result)

        if design_proposal is None:
            print("\n[FAIL] 无法从 Agent 响应中提取设计方案")
            return False

        print("\n[提取的设计方案]:")
        print(json.dumps(design_proposal, indent=2, ensure_ascii=False))

        # 验证设计方案
        is_valid, error = design_agent.validate_design_proposal(design_proposal)
        if not is_valid:
            print(f"\n[FAIL] 设计方案验证失败: {error}")
            return False

        print("\n[PASS] 设计方案验证通过")
        return True

    except Exception as e:
        print(f"\n[FAIL] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_fe_analysis_agent():
    """测试 FEAnalysisAgent 能否正确返回分析结果"""
    print("\n" + "="*80)
    print("测试 FEAnalysisAgent")
    print("="*80)

    # 预设设计方案
    design_proposal = {
        "type": "beam",
        "geometry": {
            "length": 6.0,
            "width": 0.3,
            "height": 0.5,
            "n_elements": 20
        },
        "material": {
            "E": 30e9,
            "nu": 0.2,
            "fy": 14.3e6,
            "material_name": "C30"
        },
        "loads": {
            "distributed": [
                {"q": -10000, "direction": "y"}
            ],
            "point": []
        },
        "constraints": {
            "support_type": "simply_supported"
        }
    }

    fe_agent = FEAnalysisAgent(enable_loop=False)

    try:
        fe_request = f"""请分析以下结构设计方案:

{json.dumps(design_proposal, indent=2, ensure_ascii=False)}
"""

        print(f"\nFE分析请求: {fe_request[:200]}...")

        result = await fe_agent.run(fe_request)

        print("\n[Agent 原始响应]:")
        print(result[:500] + "..." if len(result) > 500 else result)

        # 提取分析结果
        analysis_results = fe_agent.extract_analysis_results(result)

        if analysis_results is None:
            print("\n[FAIL] 无法从 Agent 响应中提取分析结果")
            return False

        print("\n[提取的分析结果]:")
        print(json.dumps(analysis_results, indent=2, ensure_ascii=False))

        # 验证分析结果
        if analysis_results.get('status') != 'success':
            print(f"\n[FAIL] FE分析失败: {analysis_results.get('error', 'Unknown error')}")
            return False

        print("\n[PASS] FE分析状态检查通过")
        return True

    except Exception as e:
        print(f"\n[FAIL] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_cad_drawing_agent():
    """测试 CADDrawingAgent 能否正确返回绘图结果"""
    print("\n" + "="*80)
    print("测试 CADDrawingAgent")
    print("="*80)

    # 预设设计方案
    design_proposal = {
        "type": "beam",
        "geometry": {
            "length": 6.0,
            "width": 0.3,
            "height": 0.5,
            "n_elements": 20
        },
        "material": {
            "E": 30e9,
            "nu": 0.2,
            "fy": 14.3e6,
            "material_name": "C30"
        },
        "loads": {
            "distributed": [
                {"q": -10000, "direction": "y"}
            ],
            "point": []
        },
        "constraints": {
            "support_type": "simply_supported"
        }
    }

    cad_agent = CADDrawingAgent()

    try:
        cad_request = f"""请为以下结构设计方案生成CAD图纸:

{json.dumps(design_proposal, indent=2, ensure_ascii=False)}
"""

        print(f"\nCAD绘图请求: {cad_request[:200]}...")

        result = await cad_agent.run(cad_request)

        print("\n[Agent 原始响应]:")
        print(result[:500] + "..." if len(result) > 500 else result)

        # 提取绘图结果
        drawing_results = cad_agent.extract_drawing_results(result)

        if drawing_results is None:
            print("\n[FAIL] 无法从 Agent 响应中提取绘图结果")
            return False

        print("\n[提取的绘图结果]:")
        print(json.dumps(drawing_results, indent=2, ensure_ascii=False))

        # 验证绘图结果
        if drawing_results.get('status') != 'success':
            print(f"\n[FAIL] CAD绘图失败: {drawing_results.get('error', 'Unknown error')}")
            return False

        print("\n[PASS] CAD绘图状态检查通过")
        return True

    except Exception as e:
        print(f"\n[FAIL] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run non-interactive tests"""
    print("\n" + "="*80)
    print("OpenManus 结构设计系统 - 阶段8集成测试（非交互版）")
    print("="*80)

    # Test 1: Design Agent
    test1_pass = await test_design_agent()

    # Test 2: FE Analysis Agent
    test2_pass = await test_fe_analysis_agent()

    # Test 3: CAD Drawing Agent
    test3_pass = await test_cad_drawing_agent()

    # Summary
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    print(f"StructuralDesignAgent: {'[PASS]' if test1_pass else '[FAIL]'}")
    print(f"FEAnalysisAgent: {'[PASS]' if test2_pass else '[FAIL]'}")
    print(f"CADDrawingAgent: {'[PASS]' if test3_pass else '[FAIL]'}")

    all_pass = test1_pass and test2_pass and test3_pass
    print("\n" + ("[SUCCESS] 所有测试通过！" if all_pass else "[FAIL] 部分测试失败"))
    print("="*80)

    return all_pass


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
