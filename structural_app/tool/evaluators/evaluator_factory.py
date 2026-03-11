"""
Factory for creating structure evaluators
Implements the Factory Pattern for extensibility
"""

from typing import Dict, Type
from .base_evaluator import DesignEvaluator
from .beam_evaluator import BeamEvaluator
from .cantilever_beam_evaluator import CantileverBeamEvaluator
from .continuous_beam_evaluator import ContinuousBeamEvaluator
from .truss_evaluator import TrussEvaluator


class EvaluatorFactory:
    """
    Factory class for creating structure evaluators

    This factory uses a registry pattern to allow easy extension
    with new structure types without modifying existing code.
    """

    # Registry of structure types to evaluator classes
    _registry: Dict[str, Type[DesignEvaluator]] = {}

    @classmethod
    def register(cls, structure_type: str, evaluator_class: Type[DesignEvaluator]) -> None:
        """
        Register a new evaluator type

        Args:
            structure_type: Type identifier (e.g., "beam", "frame", "truss")
            evaluator_class: Evaluator class (must inherit from DesignEvaluator)

        Raises:
            TypeError: If evaluator_class is not a subclass of DesignEvaluator
        """
        if not issubclass(evaluator_class, DesignEvaluator):
            raise TypeError(f"{evaluator_class.__name__} must inherit from DesignEvaluator")

        cls._registry[structure_type] = evaluator_class
        print(f"Registered evaluator: {structure_type} -> {evaluator_class.__name__}")

    @classmethod
    def create(cls, structure_type: str) -> DesignEvaluator:
        """
        Create an evaluator instance for the given structure type

        Args:
            structure_type: Type identifier (e.g., "beam", "frame", "truss")

        Returns:
            Evaluator instance

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

        evaluator_class = cls._registry[structure_type]
        return evaluator_class()

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


# Register built-in evaluators
EvaluatorFactory.register("beam", BeamEvaluator)
EvaluatorFactory.register("cantilever_beam", CantileverBeamEvaluator)
EvaluatorFactory.register("continuous_beam", ContinuousBeamEvaluator)
EvaluatorFactory.register("truss", TrussEvaluator)

# Future registrations will be added here:
# EvaluatorFactory.register("frame", FrameEvaluator)
