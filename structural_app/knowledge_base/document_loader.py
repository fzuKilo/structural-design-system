"""
Document loader for structural design standards
Supports PDF, TXT, and MD formats
"""

import os
from typing import List, Dict, Any
from pathlib import Path


class DocumentLoader:
    """
    Load and preprocess structural design standard documents

    Supports:
    - PDF files (engineering standards)
    - TXT files (plain text standards)
    - MD files (markdown documentation)
    """

    def __init__(self, documents_dir: str = "knowledge_base/documents"):
        """
        Initialize document loader

        Args:
            documents_dir: Directory containing standard documents
        """
        self.documents_dir = Path(documents_dir)
        self.documents_dir.mkdir(parents=True, exist_ok=True)

    def load_documents(self) -> List[Dict[str, Any]]:
        """
        Load all documents from the documents directory

        Returns:
            List of document dictionaries with 'content' and 'metadata'
        """
        documents = []

        # Load TXT files
        for txt_file in self.documents_dir.glob("**/*.txt"):
            doc = self._load_txt(txt_file)
            if doc:
                documents.append(doc)

        # Load MD files
        for md_file in self.documents_dir.glob("**/*.md"):
            doc = self._load_md(md_file)
            if doc:
                documents.append(doc)

        # Load PDF files (if available)
        for pdf_file in self.documents_dir.glob("**/*.pdf"):
            doc = self._load_pdf(pdf_file)
            if doc:
                documents.append(doc)

        return documents

    def _load_txt(self, file_path: Path) -> Dict[str, Any]:
        """Load TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return {
                'content': content,
                'metadata': {
                    'source': str(file_path),
                    'filename': file_path.name,
                    'type': 'txt'
                }
            }
        except Exception as e:
            print(f"Error loading TXT file {file_path}: {e}")
            return None

    def _load_md(self, file_path: Path) -> Dict[str, Any]:
        """Load MD file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return {
                'content': content,
                'metadata': {
                    'source': str(file_path),
                    'filename': file_path.name,
                    'type': 'md'
                }
            }
        except Exception as e:
            print(f"Error loading MD file {file_path}: {e}")
            return None

    def _load_pdf(self, file_path: Path) -> Dict[str, Any]:
        """
        Load PDF file

        Note: Requires PyPDF2 or pdfplumber for PDF parsing
        For now, returns None if PDF parsing is not available
        """
        try:
            # Try PyPDF2 first
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    content = ""
                    for page in pdf_reader.pages:
                        content += page.extract_text() + "\n"

                return {
                    'content': content,
                    'metadata': {
                        'source': str(file_path),
                        'filename': file_path.name,
                        'type': 'pdf',
                        'pages': len(pdf_reader.pages)
                    }
                }
            except ImportError:
                pass

            # Try pdfplumber as fallback
            try:
                import pdfplumber
                content = ""
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        content += page.extract_text() + "\n"

                return {
                    'content': content,
                    'metadata': {
                        'source': str(file_path),
                        'filename': file_path.name,
                        'type': 'pdf',
                        'pages': len(pdf.pages)
                    }
                }
            except ImportError:
                print(f"Warning: PDF parsing libraries not available. Install PyPDF2 or pdfplumber to load PDF files.")
                return None

        except Exception as e:
            print(f"Error loading PDF file {file_path}: {e}")
            return None

    def add_document(self, content: str, filename: str, doc_type: str = 'txt') -> bool:
        """
        Add a new document to the knowledge base

        Args:
            content: Document content
            filename: Filename to save as
            doc_type: Document type ('txt', 'md')

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self.documents_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error adding document {filename}: {e}")
            return False
