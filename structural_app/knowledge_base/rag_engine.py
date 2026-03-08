"""
RAG (Retrieval-Augmented Generation) Engine for structural design standards
Uses ChromaDB for vector storage and retrieval
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path


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

            # Create ChromaDB client (new API)
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory)
            )

            # Get or create collection
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

    def query_standard(
        self,
        structure_type: str,
        check_type: str,
        n_results: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Query specific standard requirements

        Args:
            structure_type: Structure type (e.g., 'beam', 'truss')
            check_type: Check type (e.g., 'height_span_ratio', 'slenderness_ratio')
            n_results: Number of results to return

        Returns:
            List of relevant standard clauses
        """
        # Construct query
        query_text = f"{structure_type} {check_type} requirements standard"

        return self.query(query_text, n_results=n_results)

    def _split_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into chunks with overlap

        Args:
            text: Text to split
            chunk_size: Maximum chunk size in characters
            overlap: Overlap between chunks in characters

        Returns:
            List of text chunks
        """
        if not text:
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size

            # Try to break at paragraph or sentence boundary
            if end < text_length:
                # Look for paragraph break
                paragraph_break = text.rfind('\n\n', start, end)
                if paragraph_break > start:
                    end = paragraph_break
                else:
                    # Look for sentence break
                    sentence_break = text.rfind('。', start, end)
                    if sentence_break == -1:
                        sentence_break = text.rfind('.', start, end)
                    if sentence_break > start:
                        end = sentence_break + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap if end < text_length else text_length

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
