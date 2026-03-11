"""
Factory for creating structure visualizers
"""

from typing import Dict, Type
from .base_visualizer import BaseVisualizer
from .beam_visualizer import BeamVisualizer


class VisualizerFactory:
    """
    Factory for creating structure type visualizers

    Uses registration pattern to map structure types to visualizer classes.
    """

    _registry: Dict[str, Type[BaseVisualizer]] = {}

    @classmethod
    def register(cls, structure_type: str, visualizer_class: Type[BaseVisualizer]):
        """
        Register a visualizer class for a structure type

        Args:
            structure_type: Structure type identifier (e.g., "beam", "frame")
            visualizer_class: Visualizer class to register
        """
        cls._registry[structure_type] = visualizer_class

    @classmethod
    def create(cls, structure_type: str) -> BaseVisualizer:
        """
        Create a visualizer instance for the given structure type

        Args:
            structure_type: Structure type identifier

        Returns:
            Visualizer instance

        Raises:
            ValueError: If structure type is not registered
        """
        if structure_type not in cls._registry:
            raise ValueError(
                f"Unknown structure type: '{structure_type}'. "
                f"Available types: {cls.get_available_types()}"
            )
        return cls._registry[structure_type]()

    @classmethod
    def is_registered(cls, structure_type: str) -> bool:
        """
        Check if a structure type is registered

        Args:
            structure_type: Structure type identifier

        Returns:
            True if registered, False otherwise
        """
        return structure_type in cls._registry

    @classmethod
    def get_available_types(cls) -> list[str]:
        """
        Get list of registered structure types

        Returns:
            List of structure type identifiers
        """
        return list(cls._registry.keys())


# Register default visualizers
VisualizerFactory.register("beam", BeamVisualizer)
VisualizerFactory.register("cantilever_beam", BeamVisualizer)  # Reuse BeamVisualizer (same 1D beam visualization)
VisualizerFactory.register("continuous_beam", BeamVisualizer)  # Reuse BeamVisualizer (same 1D beam visualization)
VisualizerFactory.register("truss", BeamVisualizer)  # Reuse BeamVisualizer (2D planar structure, similar visualization)
# VisualizerFactory.register("frame", FrameVisualizer)  # Future extension
