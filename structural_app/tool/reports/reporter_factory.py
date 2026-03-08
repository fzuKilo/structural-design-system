"""
Factory for creating structure reporters
"""

from typing import Dict, Type
from .base_reporter import BaseReporter
from .beam_reporter import BeamReporter


class ReporterFactory:
    """
    Factory for creating structure type reporters

    Uses registration pattern to map structure types to reporter classes.
    """

    _registry: Dict[str, Type[BaseReporter]] = {}

    @classmethod
    def register(cls, structure_type: str, reporter_class: Type[BaseReporter]):
        """
        Register a reporter class for a structure type

        Args:
            structure_type: Structure type identifier (e.g., "beam", "frame")
            reporter_class: Reporter class to register
        """
        cls._registry[structure_type] = reporter_class

    @classmethod
    def create(cls, structure_type: str) -> BaseReporter:
        """
        Create a reporter instance for the given structure type

        Args:
            structure_type: Structure type identifier

        Returns:
            Reporter instance

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


# Register default reporters
ReporterFactory.register("beam", BeamReporter)
ReporterFactory.register("cantilever_beam", BeamReporter)  # Reuse BeamReporter (same report format)
ReporterFactory.register("continuous_beam", BeamReporter)  # Reuse BeamReporter (same report format)
# ReporterFactory.register("frame", FrameReporter)  # Future extension
# ReporterFactory.register("truss", TrussReporter)  # Future extension
