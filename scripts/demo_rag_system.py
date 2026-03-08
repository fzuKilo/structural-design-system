"""
RAG Knowledge Base Demo
Demonstrates the complete workflow of the RAG system
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def demo_workflow():
    """Demonstrate complete RAG workflow"""
    print("="*80)
    print("RAG Knowledge Base Demo")
    print("="*80)

    # Step 1: Check if knowledge base exists
    print("\n[Step 1] Checking knowledge base status...")

    from pathlib import Path
    kb_path = Path("knowledge_base/chroma_db")

    if not kb_path.exists() or not list(kb_path.glob("*")):
        print("  Knowledge base not found. Initializing...")
        print("\n  Please run: python scripts/initialize_knowledge_base.py")
        print("  Then run this demo again.")
        return False

    print("  Knowledge base found!")

    # Step 2: Load RAG engine
    print("\n[Step 2] Loading RAG engine...")

    from structural_app.knowledge_base import RAGEngine

    rag = RAGEngine()

    if not rag.initialized:
        print("  [ERROR] RAG engine failed to initialize")
        return False

    print("  RAG engine loaded successfully!")

    # Show stats
    stats = rag.get_stats()
    print(f"\n  Statistics:")
    print(f"    Collection: {stats.get('collection_name', 'N/A')}")
    print(f"    Total chunks: {stats.get('total_chunks', 0)}")

    # Step 3: Demo queries
    print("\n[Step 3] Running demo queries...")

    demo_queries = [
        {
            'title': 'Query 1: Beam Design Requirements',
            'query': 'What are the height-span ratio requirements for beams?',
            'n_results': 2
        },
        {
            'title': 'Query 2: Cantilever Beam Deflection',
            'query': 'What is the deflection limit for cantilever beams?',
            'n_results': 2
        },
        {
            'title': 'Query 3: Material Strength',
            'query': 'What is the design strength of C30 concrete?',
            'n_results': 2
        }
    ]

    for demo in demo_queries:
        print(f"\n  {demo['title']}")
        print(f"  Query: {demo['query']}")
        print(f"  Results:")

        results = rag.query(demo['query'], n_results=demo['n_results'])

        if not results:
            print("    [No results found]")
            continue

        for idx, result in enumerate(results, 1):
            source = result['metadata'].get('filename', 'Unknown')
            content = result['content']

            # Truncate long content
            if len(content) > 150:
                content = content[:150] + "..."

            print(f"\n    Result {idx}:")
            print(f"      Source: {source}")
            print(f"      Content: {content}")

    # Step 4: Demo structure-specific queries
    print("\n[Step 4] Running structure-specific queries...")

    structure_queries = [
        ('beam', 'height_span_ratio'),
        ('cantilever_beam', 'deflection_limit'),
        ('truss', 'slenderness_ratio')
    ]

    for structure_type, check_type in structure_queries:
        print(f"\n  Structure: {structure_type}, Check: {check_type}")

        results = rag.query_standard(
            structure_type=structure_type,
            check_type=check_type,
            n_results=1
        )

        if results:
            result = results[0]
            source = result['metadata'].get('filename', 'Unknown')
            content = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']

            print(f"    Source: {source}")
            print(f"    Content: {content}")
        else:
            print(f"    [No results found]")

    # Step 5: Demo RAG-enhanced evaluator
    print("\n[Step 5] Demonstrating RAG-enhanced evaluator...")

    from structural_app.tool.evaluators.rag_enhanced_mixin import RAGEnhancedEvaluatorMixin

    class DemoEvaluator(RAGEnhancedEvaluatorMixin):
        def __init__(self):
            super().__init__()

    evaluator = DemoEvaluator()

    # Create a sample construction issue
    sample_issue = {
        'type': 'height_span_ratio_low',
        'severity': 'moderate',
        'message': 'Height-span ratio too small (0.045 < 0.05)',
        'recommendation': 'Increase beam height or reduce span'
    }

    print(f"\n  Original issue:")
    print(f"    Type: {sample_issue['type']}")
    print(f"    Message: {sample_issue['message']}")

    # Enhance with citation
    enhanced_issue = evaluator.enhance_construction_issue_with_citation(
        issue=sample_issue,
        structure_type='beam'
    )

    print(f"\n  Enhanced issue:")
    print(f"    Type: {enhanced_issue['type']}")
    print(f"    Message: {enhanced_issue['message']}")

    if 'citation' in enhanced_issue:
        print(f"    Citation: {enhanced_issue['citation']}")

    # Summary
    print("\n" + "="*80)
    print("[SUCCESS] RAG Knowledge Base Demo Complete!")
    print("="*80)

    print("\nKey Features Demonstrated:")
    print("  ✓ Vector-based semantic search")
    print("  ✓ Structure-specific standard queries")
    print("  ✓ Automatic standard citation extraction")
    print("  ✓ Construction issue enhancement with citations")

    print("\nNext Steps:")
    print("  1. Add more standard documents to knowledge_base/documents/")
    print("  2. Integrate RAG into your evaluators using RAGEnhancedEvaluatorMixin")
    print("  3. Use standard citations in construction checks")

    return True


if __name__ == '__main__':
    try:
        success = demo_workflow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
