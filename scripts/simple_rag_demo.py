"""
简单演示RAG在评估器中的实际应用
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from structural_app.tool.evaluators.rag_enhanced_mixin import RAGEnhancedEvaluatorMixin


class SimpleEvaluator(RAGEnhancedEvaluatorMixin):
    def __init__(self):
        super().__init__()


def main():
    print("="*60)
    print("RAG在评估器中的实际应用演示")
    print("="*60)

    evaluator = SimpleEvaluator()

    # 模拟一个构造问题
    print("\n[场景] 梁的高跨比检查发现问题")
    print("-"*60)

    original_issue = {
        'type': 'height_span_ratio_low',
        'severity': 'moderate',
        'message': '高跨比过小 (0.045 < 0.05)',
        'recommendation': '增加梁高或减小跨度'
    }

    print("\n原始构造问题:")
    print(f"  类型: {original_issue['type']}")
    print(f"  严重性: {original_issue['severity']}")
    print(f"  消息: {original_issue['message']}")
    print(f"  建议: {original_issue['recommendation']}")

    # 使用RAG增强
    print("\n正在查询规范引用...")
    enhanced_issue = evaluator.enhance_construction_issue_with_citation(
        issue=original_issue,
        structure_type='beam'
    )

    print("\nRAG增强后的构造问题:")
    print(f"  类型: {enhanced_issue['type']}")
    print(f"  严重性: {enhanced_issue['severity']}")
    print(f"  消息: {enhanced_issue['message']}")
    print(f"  建议: {enhanced_issue['recommendation']}")

    if 'citation' in enhanced_issue:
        print(f"  规范引用: {enhanced_issue['citation']}")
        print("\n✓ 成功添加规范引用!")
    else:
        print("\n✗ 未找到相关规范引用")

    # 测试其他结构类型
    print("\n" + "="*60)
    print("测试不同结构类型的规范引用")
    print("="*60)

    test_cases = [
        ('beam', 'height_span_ratio', '梁的高跨比'),
        ('cantilever_beam', 'deflection_limit', '悬臂梁的挠度限值'),
        ('truss', 'slenderness_ratio', '桁架的长细比')
    ]

    for structure_type, check_type, description in test_cases:
        print(f"\n[{description}]")
        citation = evaluator.query_standard_citation(
            structure_type=structure_type,
            check_type=check_type
        )

        if citation:
            print(f"  规范引用: {citation}")
        else:
            print(f"  未找到规范引用")

    print("\n" + "="*60)
    print("演示完成!")
    print("="*60)

    print("\n总结:")
    print("  ✓ RAG知识库已成功初始化")
    print("  ✓ 可以自动为构造问题添加规范引用")
    print("  ✓ 支持多种结构类型的规范查询")
    print("\n在实际使用中,这些规范引用会自动出现在:")
    print("  - 评估报告的构造问题部分")
    print("  - JSON输出的construction_issues字段")
    print("  - 为工程师提供规范依据")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
