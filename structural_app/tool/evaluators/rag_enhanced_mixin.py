"""
RAG-enhanced evaluator mixin
Provides standard citation capabilities for construction checks
"""

from typing import List, Dict, Any, Optional
import os


class RAGEnhancedEvaluatorMixin:
    """
    Mixin class to add RAG capabilities to evaluators

    Usage:
        class BeamEvaluator(DesignEvaluator, RAGEnhancedEvaluatorMixin):
            ...
    """

    def __init__(self):
        """Initialize RAG engine (lazy loading)"""
        super().__init__()
        self._rag_engine = None
        self._rag_enabled = False

    def _get_rag_engine(self):
        """Get or initialize RAG engine (lazy loading)"""
        if self._rag_engine is None:
            try:
                from structural_app.knowledge_base import RAGEngine

                self._rag_engine = RAGEngine(
                    collection_name="structural_standards",
                    persist_directory="knowledge_base/chroma_db"
                )

                if self._rag_engine.initialized:
                    self._rag_enabled = True
                    print("[RAG] Knowledge base loaded successfully")
                else:
                    self._rag_enabled = False
                    print("[RAG] Knowledge base not available")

            except Exception as e:
                print(f"[RAG] Failed to initialize: {e}")
                self._rag_enabled = False

        return self._rag_engine

    def query_standard_citation(
        self,
        structure_type: str,
        check_type: str,
        n_results: int = 1
    ) -> Optional[str]:
        """
        Query standard citation for a specific check

        Args:
            structure_type: Structure type (e.g., 'beam', 'truss')
            check_type: Check type (e.g., 'height_span_ratio')
            n_results: Number of results to retrieve

        Returns:
            Standard citation string or None
        """
        if not self._rag_enabled:
            rag = self._get_rag_engine()
            if not self._rag_enabled:
                return None

        try:
            results = self._rag_engine.query_standard(
                structure_type=structure_type,
                check_type=check_type,
                n_results=n_results
            )

            if results:
                content = results[0]['content']
                source = results[0]['metadata'].get('filename', 'Unknown')
                standard_num = self._extract_standard_number(source)

                # Extract clause number and first meaningful sentence from content
                clause = self._extract_clause_number(content)
                snippet = self._extract_snippet(content)

                parts = []
                if standard_num:
                    parts.append(standard_num)
                if clause:
                    parts.append(f"第{clause}条")
                if snippet:
                    parts.append(f"— {snippet}")

                return " ".join(parts) if parts else f"参考: {source}"

            return None

        except Exception as e:
            print(f"[RAG] Query error: {e}")
            return None

    def query_standard_requirement(
        self,
        structure_type: str,
        check_type: str,
        n_results: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Query detailed standard requirements

        Args:
            structure_type: Structure type
            check_type: Check type
            n_results: Number of results to retrieve

        Returns:
            List of requirement dictionaries
        """
        if not self._rag_enabled:
            rag = self._get_rag_engine()
            if not self._rag_enabled:
                return []

        try:
            results = self._rag_engine.query_standard(
                structure_type=structure_type,
                check_type=check_type,
                n_results=n_results
            )

            requirements = []
            for result in results:
                requirements.append({
                    'content': result['content'],
                    'source': result['metadata'].get('filename', 'Unknown'),
                    'standard': self._extract_standard_number(
                        result['metadata'].get('filename', '')
                    )
                })

            return requirements

        except Exception as e:
            print(f"[RAG] Query error: {e}")
            return []

    def _extract_standard_number(self, filename: str) -> Optional[str]:
        """Extract standard number from filename, e.g. 'GB 50010-2010'"""
        import re
        pattern = r'(GB\s*\d{5}-\d{4})'
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            std_num = match.group(1)
            std_num = re.sub(r'GB\s*(\d{5})', r'GB \1', std_num, flags=re.IGNORECASE)
            return std_num
        return None

    def _extract_clause_number(self, content: str) -> Optional[str]:
        """Extract first clause number (e.g. '9.1.1') from retrieved content."""
        import re
        match = re.search(r'\b(\d+\.\d+(?:\.\d+)?)\b', content)
        return match.group(1) if match else None

    def _extract_snippet(self, content: str, max_len: int = 40) -> Optional[str]:
        """Extract first meaningful sentence from retrieved content."""
        for line in content.splitlines():
            line = line.strip()
            # Skip headings, empty lines, table rows
            if not line or line.startswith('#') or line.startswith('|') or line.startswith('-'):
                continue
            # Truncate to max_len
            return line[:max_len] + ('…' if len(line) > max_len else '')
        return None

    def enhance_construction_issue_with_citation(
        self,
        issue: Dict[str, Any],
        structure_type: str
    ) -> Dict[str, Any]:
        """
        Enhance construction issue with standard citation

        Args:
            issue: Construction issue dictionary
            structure_type: Structure type

        Returns:
            Enhanced issue dictionary with citation
        """
        check_type = issue.get('type', '')

        # Query citation
        citation = self.query_standard_citation(
            structure_type=structure_type,
            check_type=check_type
        )

        # Add citation to issue only (do not append to message to avoid duplication)
        if citation:
            enhanced_issue = issue.copy()
            enhanced_issue['citation'] = citation
            return enhanced_issue

        return issue
