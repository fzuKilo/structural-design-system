"""
Factory for creating structure drawers
Implements the Factory Pattern for extensibility
"""

from typing import Dict, Type, Optional
from .base_drawer import StructureDrawer
from .beam_drawer import BeamDrawer


class DrawerFactory:
    """
    Factory class for creating structure drawers

    This factory uses a registry pattern to allow easy extension
    with new structure types without modifying existing code.
    """

    # Registry of structure types to drawer classes
    _registry: Dict[str, Type[StructureDrawer]] = {}

    @classmethod
    def register(cls, structure_type: str, drawer_class: Type[StructureDrawer]) -> None:
        """
        Register a new drawer type

        Args:
            structure_type: Type identifier (e.g., "beam", "frame", "truss")
            drawer_class: Drawer class (must inherit from StructureDrawer)

        Raises:
            TypeError: If drawer_class is not a subclass of StructureDrawer
        """
        if not issubclass(drawer_class, StructureDrawer):
            raise TypeError(f"{drawer_class.__name__} must inherit from StructureDrawer")

        cls._registry[structure_type] = drawer_class
        print(f"Registered drawer: {structure_type} -> {drawer_class.__name__}")

    @classmethod
    def create(cls, structure_type: str) -> Optional[StructureDrawer]:
        """
        Create a drawer instance for the given structure type

        Args:
            structure_type: Type identifier (e.g., "beam", "frame", "truss")

        Returns:
            Drawer instance, or None if type not found

        Raises:
            ValueError: If structure_type is not registered
        """
        if structure_type not in cls._registry:
            available_types = list(cls._registry.keys())
            raise ValueError(
                f"Unknown structure type: '{structure_type}'. "
                f"Available types: {available_types}"
            )

        drawer_class = cls._registry[structure_type]
        return drawer_class()

    @classmethod
    def get_available_types(cls) -> list[str]:
        """
        Get list of registered structure types

        Returns:
            List of structure type identifiers
        """
        return list(cls._registry.keys())

    @classmethod
    def is_registered(cls, structure_type: str) -> bool:
        """
        Check if a structure type is registered

        Args:
            structure_type: Type identifier to check

        Returns:
            True if registered, False otherwise
        """
        return structure_type in cls._registry


# Register built-in drawers
DrawerFactory.register("beam", BeamDrawer)

# Future registrations will be added here:
# DrawerFactory.register("frame", FrameDrawer)
# DrawerFactory.register("truss", TrussDrawer)
# DrawerFactory.register("cantilever_beam", CantileverBeamDrawer)
