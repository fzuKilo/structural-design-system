"""
Base reporter for structural design reports
Defines the abstract interface for all structure type reporters
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import os
from pathlib import Path


class BaseReporter(ABC):
    """
    Abstract base class for structure reporters

    All concrete reporters (BeamReporter, FrameReporter, etc.) must inherit
    from this class and implement the abstract methods.
    """

    def __init__(self):
        """Initialize the reporter"""
        # Set structure type first (must be done before _find_project_root if needed)
        self.structure_type = self._get_structure_type()
        # Find project root dynamically to avoid hardcoding
        _project_root = self._find_project_root()
        self.output_dir = _project_root / "output" / "reports"
        os.makedirs(self.output_dir, exist_ok=True)

    def _get_structure_type(self) -> str:
        """
        Return the structure type identifier

        Returns:
            Structure type string (e.g., "beam", "frame", "truss")
        """
        return self.__class__.__name__.replace('Reporter', '').lower()

    def _find_project_root(self) -> Path:
        """
        Find the project root directory by searching for common markers.

        Returns:
            Path to the project root directory
        """
        _current_file = Path(__file__).resolve()
        _project_root = _current_file.parent

        while _project_root.parent != _project_root:
            if (_current_file.parent.parent.parent == _project_root and
                (_project_root / "structural_app").exists()):
                return _project_root

            if (_project_root / "config.toml").exists():
                return _project_root

            if (_project_root / "README.md").exists() and (_project_root / "structural_app").exists():
                return _project_root

            _project_root = _project_root.parent

        return _current_file.parent.parent.parent
