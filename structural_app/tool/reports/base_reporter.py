"""
Base reporter for structural design reports
Defines the abstract interface for all structure type reporters
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import os


class BaseReporter(ABC):
    """
    Abstract base class for structure reporters

    All concrete reporters (BeamReporter, FrameReporter, etc.) must inherit
    from this class and implement the abstract methods.
    """

    def __init__(self):
        """Initialize the reporter"""
        self.structure_type = self._get_structure_type()
        self.output_dir = "output/reports"
        os.makedirs(self.output_dir, exist_ok=True)

    def _get_structure_type(self) -> str:
        """
        Return the structure type identifier

        Returns:
            Structure type string (e.g., "beam", "frame", "truss")
        """
        return self.__class__.__name__.replace('Reporter', '').lower()

    @abstractmethod
    def generate_report(self, design: Dict[str, Any], results: Dict[str, Any],
                       evaluation: Dict[str, Any] = None, drawings: Dict[str, Any] = None) -> str:
        """
        Generate a structured report

        Args:
            design: Design proposal
            results: Analysis results
            evaluation: Evaluation report (optional)
            drawings: Drawing results (optional)

        Returns:
            Path to the generated report file
        """
        pass

    def set_output_directory(self, directory: str) -> None:
        """
        Set the output directory for generated reports

        Args:
            directory: Path to output directory
        """
        self.output_dir = directory
        os.makedirs(self.output_dir, exist_ok=True)
