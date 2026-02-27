"""
Base visualizer for structural design results
Defines the abstract interface for all structure type visualizers
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import os


class BaseVisualizer(ABC):
    """
    Abstract base class for structure visualizers

    All concrete visualizers (BeamVisualizer, FrameVisualizer, etc.) must inherit
    from this class and implement the abstract methods.
    """

    def __init__(self):
        """Initialize the visualizer"""
        self.structure_type = self._get_structure_type()
        self.output_dir = "output/visualizations"
        os.makedirs(self.output_dir, exist_ok=True)

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
