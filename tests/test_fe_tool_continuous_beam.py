"""
测试FEAnalysisTool是否正确处理continuous_beam的n_spans参数
"""

import sys
import os
import json

# Add project root to path
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _project_root not in sys.path:
    sys.path.append(_project_root)

from structural_app.tool.fe_analysis_tool import FEAnalysisTool
import asyncio


async def test_continuous_beam_n_spans():
    """测试连续梁n_spans参数是否正确传递"""
    print("=" * 80)
    print("测试FEAnalysisTool - 连续梁n_spans参数传递")
    print("=" * 80)

    tool = FEAnalysisTool()

    # Test case: 2-span continuous beam
    design_proposal = {
        "type": "continuous_beam",
        "units": "m",
        "geometry": {
            "length": 12.0,
            "width": 0.3,
            "height": 0.6,
            "n_elements": 40,
            "n_spans": 2
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
            "support_type": "continuous"
        }
    }

    print("\n[测试] 两跨连续梁")
    print(f"输入设计方案:")
    print(json.dumps(design_proposal, indent=2, ensure_ascii=False))

    try:
        # Execute tool
        result = await tool.execute(design_proposal=json.dumps(design_proposal))

        # Parse result
        result_data = json.loads(result.output)

        print(f"\n[结果]")
        print(f"状态: {result_data.get('status')}")

        if result_data.get('status') == 'success':
            print("✓ 分析成功")
            results = result_data.get('results', {})
            print(f"  - 最大位移: {results.get('max_displacement_mm', 0):.2f} mm")
            print(f"  - 最大弯矩: {results.get('max_moment_kNm', 0):.2f} kN·m")
            print(f"  - 最大应力: {results.get('max_stress_MPa', 0):.2f} MPa")

            code_check = result_data.get('code_check', {})
            print(f"  - 规范校核: {'通过' if code_check.get('compliant') else '未通过'}")

            return True
        else:
            print(f"✗ 分析失败: {result_data.get('error')}")
            return False

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_continuous_beam_n_spans())
    print("\n" + "=" * 80)
    if success:
        print("✓ 测试通过")
    else:
        print("✗ 测试失败")
    print("=" * 80)
    sys.exit(0 if success else 1)
