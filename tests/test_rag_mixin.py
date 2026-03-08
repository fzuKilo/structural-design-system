"""
Test RAG-enhanced evaluator
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from structural_app.tool.evaluators.rag_enhanced_mixin import RAGEnhancedEvaluatorMixin


class TestEvaluator(RAGEnhancedEvaluatorMixin):
    """Test evaluator with RAG capabilities"""

    def __init__(self):
        super().__init__()


def test_rag_mixin():
    """Test RAG mixin functionality"""
    print("="*80)
    print("Testing RAG-Enhanced Evaluator Mixin")
    print("="*80)

    # Create test evaluator
    evaluator = TestEvaluator()

    # Test 1: Query standard citation
    print("\n[Test 1] Query standard citation")
    print("-"*80)

    test_cases = [
        ('beam', 'height_span_ratio'),
        ('cantilever_beam', 'deflection_limit'),
        ('truss', 'slenderness_ratio')
    ]

    for structure_type, check_type in test_cases:
        print(f"\nStructure: {structure_type}, Check: {check_type}")

        citation = evaluator.query_standard_citation(
            structure_type=structure_type,
            check_type=check_type
        )

        if citation:
            print(f"  Citation: {citation}")
        else:
            print(f"  Citation: Not found")

    # Test 2: Query standard requirements
    print("\n\n[Test 2] Query standard requirements")
    print("-"*80)

    requirements = evaluator.query_standard_requirement(
        structure_type='beam',
        check_type='height_span_ratio',
        n_results=2
    )

    if requirements:
        print(f"\nFound {len(requirements)} requirements:")
        for idx, req in enumerate(requirements, 1):
            print(f"\n  Requirement {idx}:")
            print(f"    Standard: {req['standard']}")
            print(f"    Source: {req['source']}")
            content = req['content'][:200] + "..." if len(req['content']) > 200 else req['content']
            print(f"    Content: {content}")
    else:
        print("\n  No requirements found")

    # Test 3: Enhance construction issue
    print("\n\n[Test 3] Enhance construction issue with citation")
    print("-"*80)

    test_issue = {
        'type': 'height_span_ratio_low',
        'severity': 'moderate',
        'message': '高跨比过小 (0.045 < 0.05)',
        'recommendation': '增加梁高或减小跨度'
    }

    print(f"\nOriginal issue:")
    print(f"  Type: {test_issue['type']}")
    print(f"  Message: {test_issue['message']}")

    enhanced_issue = evaluator.enhance_construction_issue_with_citation(
        issue=test_issue,
        structure_type='beam'
    )

    print(f"\nEnhanced issue:")
    print(f"  Type: {enhanced_issue['type']}")
    print(f"  Message: {enhanced_issue['message']}")
    if 'citation' in enhanced_issue:
        print(f"  Citation: {enhanced_issue['citation']}")

    print("\n" + "="*80)
    print("[SUCCESS] RAG mixin testing complete!")
    print("="*80)


if __name__ == '__main__':
    try:
        test_rag_mixin()
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
