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
                # Extract citation from first result
                content = results[0]['content']
                source = results[0]['metadata'].get('filename', 'Unknown')

                # Try to extract standard number from source filename
                standard_num = self._extract_standard_number(source)

                # Format citation
                if standard_num:
                    citation = f"参考: {standard_num}"
                else:
                    citation = f"参考: {source}"

                return citation

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
        """
        Extract standard number from filename

        Args:
            filename: Filename (e.g., 'GB50010-2010_concrete_standard.md')

        Returns:
            Standard number (e.g., 'GB 50010-2010') or None
        """
        import re

        # Pattern: GB50010-2010 or GB 50010-2010
        pattern = r'(GB\s*\d{5}-\d{4})'
        match = re.search(pattern, filename, re.IGNORECASE)

        if match:
            std_num = match.group(1)
            # Normalize format: GB 50010-2010
            std_num = re.sub(r'GB\s*(\d{5})', r'GB \1', std_num, flags=re.IGNORECASE)
            return std_num

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

        # Add citation to issue
        if citation:
            enhanced_issue = issue.copy()
            enhanced_issue['citation'] = citation

            # Append citation to message
            if 'message' in enhanced_issue:
                enhanced_issue['message'] = f"{enhanced_issue['message']} ({citation})"

            return enhanced_issue

        return issue
