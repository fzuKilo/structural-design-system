"""
OpenManus结构设计系统 - 主入口
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from structural_app.planning_flow import PlanningFlow, create_planning_flow
from structural_app.agent import (
    StructuralDesignAgent,
    FEAnalysisAgent,
    CADDrawingAgent,
    EvaluationAgent,
    ReportGenerationAgent,
)


async def run_sample_design():
    """Run a sample structural design workflow"""
    print("=" * 60)
    print("OpenManus结构设计系统 - 示例")
    print("=" * 60)
    print()

    # 创建 PlanningFlow 实例
    flow = create_planning_flow()

    # 示例请求
    request = """
请为一个跨度为12米的简支梁进行结构设计。

要求：
- 跨度：12米
- 荷载：10kN/m 均布荷载
- 材料：C30混凝土
- 设计应符合规范要求

请按照完整的 workflow 执行：
1. 设计方案生成
2. 有限元分析
3. CAD绘图
4. 设计评估
5. 报告生成
"""

    # 运行完整流程
    results = await flow.run_full_design(request, verbose=True)

    # 保存结果
    saved_file = flow.save_results()
    print(f"\n结果已保存到: {saved_file}")

    return results


def main():
    """主函数"""
    print("=" * 60)
    print("OpenManus结构设计系统")
    print("=" * 60)
    print()

    # 使用示例
    import asyncio
    asyncio.run(run_sample_design())


if __name__ == "__main__":
    main()
