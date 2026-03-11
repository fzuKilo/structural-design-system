"""
Factory for creating structure analyzers
Implements the Factory Pattern for extensibility
"""

from typing import Dict, Type, Optional
from .base_analyzer import StructureAnalyzer
from .beam_analyzer import BeamAnalyzer
from .cantilever_beam_analyzer import CantileverBeamAnalyzer
from .continuous_beam_analyzer import ContinuousBeamAnalyzer
from .truss_analyzer import TrussAnalyzer


class AnalyzerFactory:
    """
    Factory class for creating structure analyzers

    This factory uses a registry pattern to allow easy extension
    with new structure types without modifying existing code.
    """

    # Registry of structure types to analyzer classes
    _registry: Dict[str, Type[StructureAnalyzer]] = {}

    @classmethod
    def register(cls, structure_type: str, analyzer_class: Type[StructureAnalyzer]) -> None:
        """
        Register a new analyzer type

        Args:
            structure_type: Type identifier (e.g., "beam", "frame", "truss")
            analyzer_class: Analyzer class (must inherit from StructureAnalyzer)

        Raises:
            TypeError: If analyzer_class is not a subclass of StructureAnalyzer
        """
        if not issubclass(analyzer_class, StructureAnalyzer):
            raise TypeError(f"{analyzer_class.__name__} must inherit from StructureAnalyzer")

        cls._registry[structure_type] = analyzer_class
        print(f"Registered analyzer: {structure_type} -> {analyzer_class.__name__}")

    @classmethod
    def create(cls, structure_type: str) -> Optional[StructureAnalyzer]:
        """
        Create an analyzer instance for the given structure type

        Args:
            structure_type: Type identifier (e.g., "beam", "frame", "truss")

        Returns:
            Analyzer instance, or None if type not found

        Raises:
            ValueError: If structure_type is not registered
        """
        if structure_type not in cls._registry:
            available_types = list(cls._registry.keys())
            # 友好错误提示：包含未知类型和可用类型列表
            raise ValueError(
                f"当前未支持的结构类型: '{structure_type}'。\n"
                f"可用类型: {available_types}\n"
                f"请使用已支持的类型，或参考 docs/how_to_add_new_structure_type.md 添加新类型支持。"
            )

        analyzer_class = cls._registry[structure_type]
        return analyzer_class()

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


# Register built-in analyzers
AnalyzerFactory.register("beam", BeamAnalyzer)
AnalyzerFactory.register("cantilever_beam", CantileverBeamAnalyzer)
AnalyzerFactory.register("continuous_beam", ContinuousBeamAnalyzer)
AnalyzerFactory.register("truss", TrussAnalyzer)

# Future registrations will be added here:
# AnalyzerFactory.register("frame", FrameAnalyzer)
