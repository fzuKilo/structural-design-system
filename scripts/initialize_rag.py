"""
Initialize RAG knowledge base by loading standard documents into ChromaDB
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


ALL_TYPES = ["beam", "cantilever_beam", "continuous_beam", "frame", "truss"]

# Chapter heading keywords → applicable structure types
# Order matters: more specific rules first
_CHAPTER_TYPE_RULES = [
    # GB50017 specific chapters
    (["第11章", "桁架"],                          ["truss"]),
    (["第12章", "框架"],                          ["frame"]),
    (["第7章", "轴心受压"],                        ["truss", "frame"]),
    (["第8章", "轴心受拉"],                        ["truss", "frame"]),
    # GB50010 specific chapters
    (["第10章", "受压构件"],                       ["frame"]),
    (["第11章", "受拉构件"],                       ["truss"]),
    (["第9章", "受弯构件"],                        ["beam", "cantilever_beam", "continuous_beam"]),
    (["附录B", "B.1", "梁的构造"],                 ["beam", "cantilever_beam", "continuous_beam"]),
    (["附录B", "B.2", "柱的构造"],                 ["frame"]),
    # Beam-related sections in GB50017 ch5
    (["第5章", "受弯构件"],                        ["beam", "cantilever_beam", "continuous_beam", "frame"]),
]


def _infer_structure_type_flags(heading: str) -> dict:
    """
    Infer applicable structure types from a chapter/section heading.
    Returns a dict of bool flags, one per type — e.g. {'frame': True, 'truss': False, ...}.
    ChromaDB supports $eq on bool fields, so this enables precise filtered queries.
    Falls back to all True for general/appendix sections.
    """
    for keywords, types in _CHAPTER_TYPE_RULES:
        if any(kw in heading for kw in keywords):
            return {t: (t in types) for t in ALL_TYPES}
    # General section: applicable to all types
    return {t: True for t in ALL_TYPES}


def load_documents_from_directory(directory: Path):
    """
    Load markdown documents split by ## chapter sections.
    Each chunk gets per-type bool flags in metadata for filtered retrieval.
    e.g. {'frame': True, 'truss': False, 'beam': False, ...}
    """
    import re
    documents = []

    for file_path in directory.glob("*.md"):
        print(f"Loading: {file_path.name}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split on ## headings (keep the heading with its content)
        sections = re.split(r'(?=\n## )', content)

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Extract the heading line for type inference
            first_line = section.splitlines()[0].strip()
            type_flags = _infer_structure_type_flags(first_line)

            documents.append({
                'content': section,
                'metadata': {
                    'filename': file_path.name,
                    'source': 'standard_document',
                    'type': 'regulation',
                    **type_flags,
                }
            })

        print(f"  → {len([s for s in re.split(r'(?=\n## )', content) if s.strip()])} sections")

    return documents


def main(force_reload=False):
    """Main function to initialize RAG knowledge base

    Args:
        force_reload: If True, clear existing data without prompting
    """
    print("=" * 60)
    print("RAG Knowledge Base Initialization")
    print("=" * 60)
    print()

    # Initialize RAG engine
    print("Step 1: Initializing RAG engine...")
    rag = RAGEngine(
        collection_name="structural_standards",
        persist_directory="knowledge_base/chroma_db"
    )

    if not rag.initialized:
        print("[ERROR] Failed to initialize RAG engine")
        return False

    print("[OK] RAG engine initialized")
    print()

    # Check current stats
    stats = rag.get_stats()
    print(f"Current knowledge base stats:")
    print(f"  - Collection: {stats.get('collection_name')}")
    print(f"  - Total chunks: {stats.get('total_chunks')}")
    print()

    # Ask if user wants to clear existing data
    if stats.get('total_chunks', 0) > 0:
        if force_reload:
            print("Force reload enabled. Clearing existing data...")
            rag.clear()
            print("[OK] Data cleared")
            print()
        else:
            print("Knowledge base already contains data.")
            print("Run with --force to clear and reload")
            print("Skipping reload...")
            return True

    # Load documents
    print("Step 2: Loading standard documents...")
    documents_dir = project_root / "knowledge_base" / "documents"

    if not documents_dir.exists():
        print(f"[ERROR] Documents directory not found: {documents_dir}")
        return False

    documents = load_documents_from_directory(documents_dir)
    print(f"[OK] Loaded {len(documents)} documents")
    print()

    # Add documents to RAG
    print("Step 3: Adding documents to vector database...")
    print("(This may take a few minutes for embedding generation)")

    success = rag.add_documents(documents)

    if success:
        print("[OK] Documents added successfully")
    else:
        print("[ERROR] Failed to add documents")
        return False

    print()

    # Show final stats
    print("Step 4: Final statistics...")
    stats = rag.get_stats()
    print(f"  - Collection: {stats.get('collection_name')}")
    print(f"  - Total chunks: {stats.get('total_chunks')}")
    print(f"  - Persist directory: {stats.get('persist_directory')}")
    print()

    # Test query
    print("Step 5: Testing query...")
    test_query = "梁的高跨比要求"
    results = rag.query(test_query, n_results=2)

    if results:
        print(f"[OK] Query test successful (found {len(results)} results)")
        print(f"\nSample result for '{test_query}':")
        print(f"  Content preview: {results[0]['content'][:200]}...")
        print(f"  Source: {results[0]['metadata'].get('filename')}")
    else:
        print("[WARNING] Query returned no results")

    print()
    print("=" * 60)
    print("RAG Initialization Complete!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Initialize RAG knowledge base')
    parser.add_argument('--force', action='store_true', help='Force reload, clear existing data')
    args = parser.parse_args()

    success = main(force_reload=args.force)
    sys.exit(0 if success else 1)
