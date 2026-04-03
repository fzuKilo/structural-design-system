"""
测试StructuralDesignAgent是否正确识别连续梁类型
"""

import sys
import os

# OpenManus path is handled by conftest.py

# Add project root to path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from structural_app.agent.structural_design_agent import StructuralDesignAgent
import asyncio
import json


async def test_continuous_beam_recognition():
    """测试连续梁类型识别"""
    print("=" * 80)
    print("测试StructuralDesignAgent - 连续梁类型识别")
    print("=" * 80)

    agent = StructuralDesignAgent()

    test_cases = [
        {
            "name": "两跨连续梁 (明确说明)",
            "request": "设计一个两跨连续梁，总跨度12m，均布荷载10kN/m，使用C30混凝土",
            "expected_type": "continuous_beam",
            "expected_n_spans": 2
        },
        {
            "name": "三跨连续梁 (每跨长度)",
            "request": "设计三跨连续梁，每跨6米，承受15kN/m均布荷载，C30混凝土",
            "expected_type": "continuous_beam",
            "expected_n_spans": 3
        },
        {
            "name": "简支梁 (对照组)",
            "request": "设计一个6米跨度的简支梁，承受10kN/m的均布荷载，使用C30混凝土",
            "expected_type": "beam",
            "expected_n_spans": None
        },
        {
            "name": "悬臂梁 (对照组)",
            "request": "设计一个3米悬臂梁，承受5kN/m均布荷载，C30混凝土",
            "expected_type": "cantilever_beam",
            "expected_n_spans": None
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[测试 {i}/{len(test_cases)}] {test_case['name']}")
        print(f"需求: {test_case['request']}")
        print(f"期望类型: {test_case['expected_type']}")

        try:
            # Run agent
            response = await agent.run(test_case['request'])

            # Extract design proposal
            design = agent.extract_design_proposal(response)

            if design:
                actual_type = design.get('type')
                actual_n_spans = design.get('geometry', {}).get('n_spans')

                print(f"实际类型: {actual_type}")
                if actual_n_spans:
                    print(f"实际跨数: {actual_n_spans}")

                # Check if correct
                type_correct = actual_type == test_case['expected_type']
                n_spans_correct = (
                    actual_n_spans == test_case['expected_n_spans']
                    if test_case['expected_n_spans'] is not None
                    else True
                )

                if type_correct and n_spans_correct:
                    print("✓ 通过")
                    results.append(True)
                else:
                    print("✗ 失败")
                    if not type_correct:
                        print(f"  类型错误: 期望 {test_case['expected_type']}, 实际 {actual_type}")
                    if not n_spans_correct:
                        print(f"  跨数错误: 期望 {test_case['expected_n_spans']}, 实际 {actual_n_spans}")
                    results.append(False)

                # Print full design for debugging
                print(f"\n完整设计方案:")
                print(json.dumps(design, indent=2, ensure_ascii=False))

            else:
                print("✗ 失败: 无法提取设计方案")
                results.append(False)

        except Exception as e:
            print(f"✗ 失败: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    # Summary
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")

    if passed == total:
        print("\n✓✓✓ 所有测试通过! ✓✓✓")
        return True
    else:
        print(f"\n✗ {total - passed} 个测试失败")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_continuous_beam_recognition())
    sys.exit(0 if success else 1)
