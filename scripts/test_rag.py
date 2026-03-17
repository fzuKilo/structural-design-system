"""
Test RAG knowledge base functionality
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from structural_app.knowledge_base import RAGEngine


def main():
    """Test RAG functionality"""
    print("=" * 60)
    print("RAG Knowledge Base Test")
    print("=" * 60)
    print()

    # Initialize RAG engine
    print("Initializing RAG engine...")
    rag = RAGEngine(
        collection_name="structural_standards",
        persist_directory="knowledge_base/chroma_db"
    )

    if not rag.initialized:
        print("[ERROR] Failed to initialize RAG engine")
        return False

    print("[OK] RAG engine initialized")
    print()

    # Show stats
    stats = rag.get_stats()
    print(f"Knowledge base stats:")
    print(f"  - Collection: {stats.get('collection_name')}")
    print(f"  - Total chunks: {stats.get('total_chunks')}")
    print()

    # Test queries
    test_queries = [
        "梁的高跨比要求",
        "混凝土强度等级",
        "钢筋保护层厚度",
        "beam height span ratio",
        "deflection limit"
    ]

    print("Testing queries:")
    print("-" * 60)

    for query in test_queries:
        print(f"\nQuery: {query}")
        results = rag.query(query, n_results=2)

        if results:
            print(f"  Found {len(results)} results")
            for i, result in enumerate(results, 1):
                content_preview = result['content'][:100].replace('\n', ' ')
                source = result['metadata'].get('filename', 'Unknown')
                distance = result.get('distance', 'N/A')
                print(f"  [{i}] Source: {source}")
                print(f"      Distance: {distance}")
                print(f"      Preview: {content_preview}...")
        else:
            print("  [WARNING] No results found")

    print()
    print("=" * 60)
    print("Test Complete!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
