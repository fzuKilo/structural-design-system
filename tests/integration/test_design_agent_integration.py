"""
Integration tests for StructuralDesignAgent
Tests actual LLM integration (requires valid API key in config.toml)
"""

import sys
import os
import asyncio
import json

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


@pytest.mark.asyncio
async def test_simple_beam_design():
    """
    Test 1: Simple beam design with complete parameters
    Expected: Agent generates valid DesignProposal without asking questions
    """
    print("\n" + "="*80)
    print("Test 1: Simple Beam Design (Complete Parameters)")
    print("="*80)

    # Create agent
    agent = StructuralDesignAgent()

    # Test input
    request = "设计一个6米跨度的简支梁，承受10kN/m的均布荷载，使用C30混凝土"

    print(f"\n输入: {request}")
    print("\n调用LLM生成设计方案...")

    try:
        # Run agent
        result = await agent.run(request)

        print("\n原始输出:")
        print(result)

        # Extract design proposal
        if isinstance(result, dict) and 'content' in result:
            response_text = result['content']
        elif isinstance(result, str):
            response_text = result
        else:
            response_text = str(result)

        design_proposal = agent.extract_design_proposal(response_text)

        if design_proposal:
            print("\n提取的设计方案:")
            print(json.dumps(design_proposal, indent=2, ensure_ascii=False))

            # Validate
            is_valid, error = agent.validate_design_proposal(design_proposal)

            if is_valid:
                print("\n[PASS] 验证通过：设计方案包含所有必需字段")

                # Check key values
                print("\n关键参数检查:")
                print(f"  - 结构类型: {design_proposal.get('type')}")
                print(f"  - 跨度: {design_proposal.get('geometry', {}).get('length')} m")
                print(f"  - 截面宽度: {design_proposal.get('geometry', {}).get('width')} m")
                print(f"  - 截面高度: {design_proposal.get('geometry', {}).get('height')} m")
                print(f"  - 材料: {design_proposal.get('material', {}).get('material_name')}")
                print(f"  - 弹性模量: {design_proposal.get('material', {}).get('E')} Pa")
                print(f"  - 荷载: {design_proposal.get('loads', {}).get('distributed', [{}])[0].get('q')} N/m")
                print(f"  - 支座类型: {design_proposal.get('constraints', {}).get('support_type')}")

                # Check reasonableness
                geometry = design_proposal.get('geometry', {})
                length = geometry.get('length', 0)
                height = geometry.get('height', 0)

                if length > 0 and height > 0:
                    span_depth_ratio = length / height
                    print(f"\n  - 跨高比: {span_depth_ratio:.1f} (合理范围: 10-15)")

                    if 8 <= span_depth_ratio <= 20:
                        print("    [OK] 跨高比合理")
                    else:
                        print("    [WARN] 跨高比可能不合理")

                return True
            else:
                print(f"\n[FAIL] 验证失败: {error}")
                return False
        else:
            print("\n[FAIL] 无法从响应中提取设计方案")
            return False

    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_incomplete_parameters():
    """
    Test 2: Beam design with missing parameters
    Expected: Agent should ask for missing information (if AskHuman is properly configured)
    """
    print("\n" + "="*80)
    print("Test 2: Incomplete Parameters (Should Ask Questions)")
    print("="*80)

    agent = StructuralDesignAgent()

    # Use a simple request that will trigger AskHuman
    request = "设计一个简支梁"

    print(f"\n输入: {request}")
    print("\n注意: 如果缺少必要参数，Agent 会通过 AskHuman 询问你。")
    print("请在终端根据 Agent 的提示输入缺失的信息。\n")

    try:
        result = await agent.run(request)

        print("\n原始输出:")
        print(result)

        # Extract design proposal
        if isinstance(result, dict) and 'content' in result:
            response_text = result['content']
        elif isinstance(result, str):
            response_text = result
        else:
            response_text = str(result)

        design_proposal = agent.extract_design_proposal(response_text)

        if design_proposal:
            print("\n提取的设计方案:")
            print(json.dumps(design_proposal, indent=2, ensure_ascii=False))

            is_valid, error = agent.validate_design_proposal(design_proposal)

            if is_valid:
                print("\n[PASS] 验证通过")
                return True
            else:
                print(f"\n[FAIL] 验证失败: {error}")
                return False
        else:
            print("\n[FAIL] 无法提取设计方案")
            return False

    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all integration tests"""
    print("\n" + "="*80)
    print("StructuralDesignAgent 集成测试")
    print("="*80)
    print("\n前置条件:")
    print("  1. config.toml 已配置有效的 DeepSeek API key")
    print("  2. OpenManus 已正确安装")
    print("  3. 网络连接正常")

    # Check config file
    config_path = os.path.join(_project_root, 'config.toml')
    if not os.path.exists(config_path):
        print(f"\n[ERROR] 配置文件不存在: {config_path}")
        print("请先创建 config.toml 并配置 API key")
        return

    # Read config to check API key
    with open(config_path, 'r', encoding='utf-8') as f:
        config_content = f.read()
        if 'YOUR_DEEPSEEK_API_KEY_HERE' in config_content:
            print(f"\n[ERROR] 请先在 config.toml 中填入实际的 API key")
            print(f"配置文件位置: {config_path}")
            return

    print("\n[OK] 配置文件检查通过")

    # Ask user for test mode
    print("\n" + "-"*80)
    print("测试模式选择:")
    print("  1. 自定义需求测试 (输入你的结构设计需求)")
    print("  2. 使用预设测试 (完整参数测试)")
    print("  3. 使用预设测试 (缺失参数测试)")
    print("-"*80)

    test_mode = input("\n请选择测试模式 (1/2/3): ").strip()

    # Run tests based on mode
    results = []

    if test_mode == "1":
        # Custom user request
        print("\n" + "="*80)
        print("自定义需求测试")
        print("="*80)
        user_request = input("\n请输入你的结构设计需求:\n> ")

        agent = StructuralDesignAgent()
        print("\n调用LLM生成设计方案...")

        try:
            result = await agent.run(user_request)
            print("\n原始输出:")
            print(result)

            # Extract and validate
            if isinstance(result, dict) and 'content' in result:
                response_text = result['content']
            elif isinstance(result, str):
                response_text = result
            else:
                response_text = str(result)

            design_proposal = agent.extract_design_proposal(response_text)

            if design_proposal:
                print("\n提取的设计方案:")
                print(json.dumps(design_proposal, indent=2, ensure_ascii=False))

                is_valid, error = agent.validate_design_proposal(design_proposal)
                print(f"\n验证结果: {'[PASS] 通过' if is_valid else '[FAIL] ' + error}")

                results.append(("Custom Request Test", is_valid))
            else:
                print("\n[FAIL] 无法提取设计方案")
                results.append(("Custom Request Test", False))
        except Exception as e:
            print(f"\n[FAIL] 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append(("Custom Request Test", False))

    elif test_mode == "2":
        # Test 1: Complete parameters
        result1 = await test_simple_beam_design()
        results.append(("Test 1: Complete Parameters", result1))

    elif test_mode == "3":
        # Test 2: Incomplete parameters
        result2 = await test_incomplete_parameters()
        results.append(("Test 2: Incomplete Parameters", result2))

    else:
        print(f"\n[ERROR] 无效的选项: {test_mode}")
        return

    # Summary
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    for test_name, result in results:
        if result is True:
            status = "[PASS]"
        elif result is False:
            status = "[FAIL]"
        else:
            status = "[SKIP]"
        print(f"{test_name}: {status}")

    # Overall result
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)

    print(f"\n总计: {passed} 通过, {failed} 失败, {skipped} 跳过")

    if failed == 0 and passed > 0:
        print("\n[SUCCESS] 集成测试通过！StructuralDesignAgent 可以正常工作。")
    elif failed > 0:
        print("\n[FAILED] 集成测试失败，请检查错误信息。")
    else:
        print("\n[WARN] 没有测试被执行。")


if __name__ == "__main__":
    asyncio.run(main())
