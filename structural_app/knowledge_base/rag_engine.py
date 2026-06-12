"""
RAG (Retrieval-Augmented Generation) Engine for structural design standards
Uses ChromaDB for vector storage and retrieval
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path

# NumPy 2.0 compatibility shim: chromadb 0.4.24 (pinned to avoid an httpx conflict
# with specklepy) references np.float_/np.int_, which were removed in NumPy 2.0.
# Restore them as aliases before chromadb is imported, otherwise the RAG engine
# fails to initialize and all code-clause citations silently disappear.
try:
    import numpy as _np
    if not hasattr(_np, "float_"):
        _np.float_ = _np.float64
    if not hasattr(_np, "int_"):
        _np.int_ = _np.int64
    if not hasattr(_np, "uint"):
        _np.uint = _np.uint64
except Exception:
    pass


class RAGEngine:
    """
    RAG Engine for querying structural design standards

    Features:
    - Vector-based semantic search
    - Context-aware retrieval
    - Standard citation support
    """

    def __init__(
        self,
        collection_name: str = "structural_standards",
        persist_directory: str = "knowledge_base/chroma_db",
        embedding_model: str = "text-embedding-ada-002"
    ):
        """
        Initialize RAG engine

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist the vector database
            embedding_model: OpenAI embedding model to use
        """
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.embedding_model = embedding_model

        # Initialize ChromaDB client
        self.client = None
        self.collection = None
        self.initialized = False

        # Try to initialize
        self._initialize()

    def _initialize(self):
        """Initialize ChromaDB and collection"""
        try:
            import chromadb

            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory)
            )

            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Structural design standards and regulations"}
            )

            self.initialized = True
            print(f"RAG Engine initialized with collection: {self.collection_name}")

        except ImportError as e:
            print(f"Warning: ChromaDB not available. Install with: pip install chromadb")
            print(f"RAG features will be disabled. Error: {e}")
            self.initialized = False
        except Exception as e:
            print(f"Error initializing RAG engine: {e}")
            self.initialized = False

    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Add documents to the vector database

        Args:
            documents: List of document dictionaries with 'content' and 'metadata'

        Returns:
            True if successful, False otherwise
        """
        if not self.initialized:
            print("RAG Engine not initialized. Cannot add documents.")
            return False

        try:
            # Split documents into chunks
            chunks = []
            metadatas = []
            ids = []

            for idx, doc in enumerate(documents):
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})

                # Split content into chunks (simple splitting by paragraphs)
                doc_chunks = self._split_text(content)

                for chunk_idx, chunk in enumerate(doc_chunks):
                    chunks.append(chunk)
                    metadatas.append({
                        **metadata,
                        'chunk_index': chunk_idx,
                        'total_chunks': len(doc_chunks)
                    })
                    ids.append(f"doc_{idx}_chunk_{chunk_idx}")

            # Add to collection
            if chunks:
                self.collection.add(
                    documents=chunks,
                    metadatas=metadatas,
                    ids=ids
                )
                print(f"Added {len(chunks)} chunks from {len(documents)} documents")
                return True
            else:
                print("No chunks to add")
                return False

        except Exception as e:
            print(f"Error adding documents: {e}")
            return False

    def query(
        self,
        query_text: str,
        n_results: int = 3,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Query the knowledge base

        Args:
            query_text: Query string
            n_results: Number of results to return
            filter_metadata: Optional metadata filter

        Returns:
            List of relevant document chunks with metadata
        """
        if not self.initialized:
            print("RAG Engine not initialized. Returning empty results.")
            return []

        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=filter_metadata
            )

            # Format results
            formatted_results = []
            if results and results['documents']:
                for idx in range(len(results['documents'][0])):
                    formatted_results.append({
                        'content': results['documents'][0][idx],
                        'metadata': results['metadatas'][0][idx] if results['metadatas'] else {},
                        'distance': results['distances'][0][idx] if results['distances'] else None
                    })

            return formatted_results

        except Exception as e:
            print(f"Error querying knowledge base: {e}")
            return []

    # Chinese query map for common check types
    _QUERY_MAP = {
        'width_too_small':          '梁最小宽度要求 截面尺寸限值',
        'height_too_small':         '梁最小高度要求 截面尺寸限值',
        'height_span_ratio_low':    '梁高跨比要求 连续梁简支梁',
        'height_span_ratio_high':   '梁高跨比要求 截面高度',
        'width_height_ratio_high':  '梁宽高比要求 截面宽度高度',
        'width_height_ratio_low':   '梁宽高比要求 截面宽度高度',
        'slenderness_ratio':        '柱长细比要求 稳定性',
        'axial_ratio':              '柱轴压比限值',
        'deflection':               '受弯构件挠度限值',
        'crack_width':              '裂缝宽度限值',
        'shear':                    '斜截面受剪承载力',
        'stress_ratio':             '应力比限值 强度验算',
        'truss_slenderness':        '桁架杆件长细比要求',
        'node_connection':          '节点连接构造要求',
    }

    def query_standard(
        self,
        structure_type: str,
        check_type: str,
        n_results: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Query specific standard requirements, filtered to chunks relevant
        to the given structure_type (uses the structure_types metadata tag
        written at ingest time).

        Args:
            structure_type: Structure type (e.g., 'beam', 'truss')
            check_type: Check type (e.g., 'height_span_ratio', 'slenderness_ratio')
            n_results: Number of results to return

        Returns:
            List of relevant standard clauses
        """
        # Build Chinese query text
        query_text = self._QUERY_MAP.get(check_type)
        if not query_text:
            type_cn = {'beam': '梁', 'frame': '框架', 'truss': '桁架',
                       'cantilever_beam': '悬臂梁', 'continuous_beam': '连续梁'}.get(structure_type, structure_type)
            query_text = f"{type_cn} {check_type} 构造要求"

        # Filter to chunks tagged for this structure_type.
        # Metadata uses per-type bool flags (e.g. {'frame': True, 'truss': False}).
        # ChromaDB supports $eq on bool fields.
        filter_metadata = {structure_type: {"$eq": True}}

        results = self.query(query_text, n_results=n_results, filter_metadata=filter_metadata)

        # Graceful fallback: if the filter yields nothing (e.g. old data without tags),
        # retry without filter so citations still appear rather than silently disappearing.
        if not results:
            results = self.query(query_text, n_results=n_results)

        return results

    def _split_text(self, text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
        """
        Split text into chunks by markdown section headings first,
        then by size if a section is still too large.
        """
        if not text:
            return []

        import re
        # Split on ## or ### headings to keep each section together
        sections = re.split(r'(?=\n#{1,3} )', text)
        chunks = []
        for section in sections:
            section = section.strip()
            if not section:
                continue
            if len(section) <= chunk_size:
                chunks.append(section)
            else:
                # Further split large sections by size
                start = 0
                while start < len(section):
                    end = start + chunk_size
                    if end < len(section):
                        break_pos = section.rfind('\n', start, end)
                        if break_pos > start:
                            end = break_pos
                    chunk = section[start:end].strip()
                    if chunk:
                        chunks.append(chunk)
                    start = end - overlap if end < len(section) else len(section)
        return chunks

    def get_stats(self) -> Dict[str, Any]:
        """
        Get knowledge base statistics

        Returns:
            Dictionary with statistics
        """
        if not self.initialized:
            return {
                'initialized': False,
                'total_chunks': 0
            }

        try:
            count = self.collection.count()
            return {
                'initialized': True,
                'collection_name': self.collection_name,
                'total_chunks': count,
                'persist_directory': str(self.persist_directory)
            }
        except Exception as e:
            return {
                'initialized': True,
                'error': str(e)
            }

    def clear(self) -> bool:
        """
        Clear all documents from the knowledge base

        Returns:
            True if successful, False otherwise
        """
        if not self.initialized:
            return False

        try:
            # Delete and recreate collection
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Structural design standards and regulations"}
            )
            print(f"Cleared collection: {self.collection_name}")
            return True
        except Exception as e:
            print(f"Error clearing knowledge base: {e}")
            return False
