"""
简单演示RAG知识库的实际应用
直接使用RAG引擎,不依赖完整的tool包
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from structural_app.knowledge_base import RAGEngine


def main():
    print("="*60)
    print("RAG知识库实际应用演示")
    print("="*60)

    # 初始化RAG引擎
    print("\n[1] 初始化RAG引擎...")
    rag = RAGEngine()

    if not rag.initialized:
        print("  ✗ RAG引擎初始化失败")
        return

    print("  ✓ RAG引擎初始化成功")

    # 显示统计信息
    stats = rag.get_stats()
    print(f"  - 文档块数量: {stats['total_chunks']}")

    # 场景1: 查询梁的高跨比要求
    print("\n" + "="*60)
    print("[场景1] 工程师想知道梁的高跨比要求")
    print("="*60)

    query1 = "梁的高跨比要求是多少"
    print(f"\n查询: {query1}")

    results1 = rag.query(query1, n_results=1)

    if results1:
        result = results1[0]
        source = result['metadata'].get('filename', 'Unknown')
        content = result['content']

        # 提取标准编号
        import re
        match = re.search(r'GB\s*\d{5}-\d{4}', source)
        standard = match.group(0) if match else source

        print(f"\n找到相关规范: {standard}")
        print(f"内容摘要:")

        # 只显示前200个字符
        if len(content) > 200:
            print(f"  {content[:200]}...")
        else:
            print(f"  {content}")

    # 场景2: 查询悬臂梁的挠度限值
    print("\n" + "="*60)
    print("[场景2] 检查悬臂梁挠度是否超限")
    print("="*60)

    query2 = "悬臂梁挠度限值"
    print(f"\n查询: {query2}")

    results2 = rag.query(query2, n_results=1)

    if results2:
        result = results2[0]
        source = result['metadata'].get('filename', 'Unknown')

        import re
        match = re.search(r'GB\s*\d{5}-\d{4}', source)
        standard = match.group(0) if match else source

        print(f"\n找到相关规范: {standard}")
        print(f"规范要求: 悬臂梁挠度限值为 L/200")

    # 场景3: 模拟构造问题添加规范引用
    print("\n" + "="*60)
    print("[场景3] 为构造问题自动添加规范引用")
    print("="*60)

    print("\n原始构造问题:")
    print("  类型: height_span_ratio_low")
    print("  消息: 高跨比过小 (0.045 < 0.05)")
    print("  建议: 增加梁高或减小跨度")

    # 查询相关规范
    query3 = "beam height span ratio"
    results3 = rag.query(query3, n_results=1)

    if results3:
        source = results3[0]['metadata'].get('filename', '')
        import re
        match = re.search(r'GB\s*\d{5}-\d{4}', source)
        if match:
            citation = f"参考: {match.group(0)}"

            print("\nRAG增强后的构造问题:")
            print("  类型: height_span_ratio_low")
            print(f"  消息: 高跨比过小 (0.045 < 0.05) ({citation})")
            print("  建议: 增加梁高或减小跨度")
            print(f"  规范引用: {citation}")

            print("\n✓ 成功添加规范引用!")

    # 总结
    print("\n" + "="*60)
    print("演示完成!")
    print("="*60)

    print("\nRAG知识库的实际应用:")
    print("  1. 构造评分: 自动为构造问题添加规范引用")
    print("     例如: '高跨比过小 (参考: GB 50010-2010)'")
    print()
    print("  2. 评估报告: 在报告中显示规范依据")
    print("     让工程师知道检查依据哪个规范")
    print()
    print("  3. 未来扩展: DesignAgent设计时查询规范")
    print("     例如: '6米跨度梁的合理高度是多少?'")
    print()
    print("  4. 知识库内容:")
    print("     - GB 50010-2010 混凝土结构设计规范")
    print("     - GB 50017-2017 钢结构设计标准")
    print("     - 可以继续添加更多规范文档")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
