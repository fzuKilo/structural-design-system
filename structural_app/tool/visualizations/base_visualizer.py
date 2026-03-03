"""
Base visualizer for structural design results
Defines the abstract interface for all structure type visualizers
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import os
from pathlib import Path


class BaseVisualizer(ABC):
    """
    Abstract base class for structure visualizers

    All concrete visualizers (BeamVisualizer, FrameVisualizer, etc.) must inherit
    from this class and implement the abstract methods.
    """

    def __init__(self):
        """Initialize the visualizer"""
        self.structure_type = self._get_structure_type()
        # Use project root relative path for output_dir
        # Find project root by looking for common marker files/folders
        _project_root = self._find_project_root()
        self.output_dir = _project_root / "output" / "visualizations"
        os.makedirs(self.output_dir, exist_ok=True)

    def _find_project_root(self) -> Path:
        """
        Find the project root directory by searching for common markers.

        Walks up the directory tree from the current file location until
        it finds a marker file/folder indicating the project root.

        Returns:
            Path to the project root directory
        """
        _current_file = Path(__file__).resolve()
        _project_root = _current_file.parent

        # Walk up the directory tree
        while _project_root.parent != _project_root:  # Not at root yet
            # Check for common project markers
            if (_current_file.parent.parent.parent.parent == _project_root and
                (_project_root / "structural_app").exists()):
                # Found structural_app at parent of parent of parent of current file
                return _project_root

            # Alternative: check for config.toml or other project markers
            if (_project_root / "config.toml").exists():
                return _project_root

            if (_project_root / "README.md").exists() and (_project_root / "structural_app").exists():
                return _project_root

            _project_root = _project_root.parent

        # Fallback to structural_app parent if we can't find a better root
        return _current_file.parent.parent.parent.parent

    def _get_structure_type(self) -> str:
        """
        Return the structure type identifier

        Returns:
            Structure type string (e.g., "beam", "frame", "truss")
        """
        return self.__class__.__name__.replace('Visualizer', '').lower()

    @abstractmethod
    def generate_static_visualizations(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate static visualizations using matplotlib

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary mapping visualization type to file path:
                - displacement_contour: Displacement contour plot (PNG)
                - moment_contour: Moment contour plot (PNG)
                - stress_contour: Stress contour plot (PNG)
                - moment_diagram: Moment diagram (PNG)
        """
        pass

    @abstractmethod
    def generate_interactive_visualizations(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate interactive visualizations using Plotly

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary mapping visualization type to file path:
                - displacement_html: Interactive displacement plot (HTML)
                - moment_html: Interactive moment plot (HTML)
                - stress_html: Interactive stress plot (HTML)
        """
        pass

    def generate_all_visualizations(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate all visualizations

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary containing both static and interactive visualizations
        """
        static = self.generate_static_visualizations(design, results)
        interactive = self.generate_interactive_visualizations(design, results)

        return {
            'static': static,
            'interactive': interactive
        }

    def set_output_directory(self, directory: str) -> None:
        """
        Set the output directory for generated visualizations

        Args:
            directory: Path to output directory
        """
        self.output_dir = directory
        os.makedirs(self.output_dir, exist_ok=True)
