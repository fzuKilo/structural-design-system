"""
Initialize and test the RAG knowledge base
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from structural_app.knowledge_base import RAGEngine, DocumentLoader


def initialize_knowledge_base():
    """Initialize the knowledge base with standard documents"""
    print("="*80)
    print("Initializing RAG Knowledge Base")
    print("="*80)

    # Step 1: Load documents
    print("\n[Step 1] Loading documents...")
    loader = DocumentLoader(documents_dir="knowledge_base/documents")
    documents = loader.load_documents()
    print(f"  Loaded {len(documents)} documents")

    for doc in documents:
        filename = doc['metadata']['filename']
        content_length = len(doc['content'])
        print(f"    - {filename}: {content_length} characters")

    # Step 2: Initialize RAG engine
    print("\n[Step 2] Initializing RAG engine...")
    rag = RAGEngine(
        collection_name="structural_standards",
        persist_directory="knowledge_base/chroma_db"
    )

    if not rag.initialized:
        print("  [ERROR] RAG engine initialization failed")
        print("  Please install required packages:")
        print("    pip install chromadb langchain")
        return None

    # Step 3: Add documents to vector database
    print("\n[Step 3] Adding documents to vector database...")
    success = rag.add_documents(documents)

    if success:
        print("  [SUCCESS] Documents added successfully")
    else:
        print("  [ERROR] Failed to add documents")
        return None

    # Step 4: Show statistics
    print("\n[Step 4] Knowledge base statistics:")
    stats = rag.get_stats()
    for key, value in stats.items():
        print(f"    {key}: {value}")

    return rag


def test_queries(rag: RAGEngine):
    """Test various queries"""
    print("\n" + "="*80)
    print("Testing Knowledge Base Queries")
    print("="*80)

    test_cases = [
        {
            'name': 'Test 1: Beam height-span ratio',
            'query': 'beam height span ratio requirements',
            'n_results': 2
        },
        {
            'name': 'Test 2: Cantilever beam deflection limit',
            'query': 'cantilever beam deflection limit',
            'n_results': 2
        },
        {
            'name': 'Test 3: Steel material strength',
            'query': 'Q345 steel strength design value',
            'n_results': 2
        },
        {
            'name': 'Test 4: Concrete strength',
            'query': 'C30 concrete strength',
            'n_results': 2
        },
        {
            'name': 'Test 5: Truss slenderness ratio',
            'query': 'truss member slenderness ratio limit',
            'n_results': 2
        }
    ]

    for test in test_cases:
        print(f"\n{test['name']}")
        print(f"  Query: {test['query']}")
        print(f"  Results:")

        results = rag.query(test['query'], n_results=test['n_results'])

        if not results:
            print("    [No results found]")
            continue

        for idx, result in enumerate(results, 1):
            content = result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
            source = result['metadata'].get('filename', 'Unknown')
            distance = result.get('distance', 'N/A')

            print(f"\n    Result {idx}:")
            print(f"      Source: {source}")
            print(f"      Distance: {distance}")
            print(f"      Content: {content}")


def test_standard_queries(rag: RAGEngine):
    """Test structure-specific standard queries"""
    print("\n" + "="*80)
    print("Testing Structure-Specific Standard Queries")
    print("="*80)

    test_cases = [
        {
            'structure_type': 'beam',
            'check_type': 'height_span_ratio'
        },
        {
            'structure_type': 'cantilever_beam',
            'check_type': 'deflection_limit'
        },
        {
            'structure_type': 'truss',
            'check_type': 'slenderness_ratio'
        }
    ]

    for test in test_cases:
        print(f"\n[Query] Structure: {test['structure_type']}, Check: {test['check_type']}")

        results = rag.query_standard(
            structure_type=test['structure_type'],
            check_type=test['check_type'],
            n_results=2
        )

        if not results:
            print("  [No results found]")
            continue

        for idx, result in enumerate(results, 1):
            content = result['content'][:150] + "..." if len(result['content']) > 150 else result['content']
            source = result['metadata'].get('filename', 'Unknown')

            print(f"\n  Result {idx}:")
            print(f"    Source: {source}")
            print(f"    Content: {content}")


def main():
    """Main function"""
    # Initialize knowledge base
    rag = initialize_knowledge_base()

    if rag is None:
        print("\n[FAILED] Knowledge base initialization failed")
        return False

    # Test queries
    test_queries(rag)

    # Test structure-specific queries
    test_standard_queries(rag)

    print("\n" + "="*80)
    print("[SUCCESS] Knowledge base initialization and testing complete!")
    print("="*80)

    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
