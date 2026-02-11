"""
Agent module for structural design system
"""

# Lazy imports to avoid namespace conflicts with OpenManus
# Import directly when needed instead of at module level

__all__ = [
    'StructuralDesignAgent',
    'create_structural_design_agent',
]

def __getattr__(name):
    """Lazy import to avoid early namespace conflicts"""
    if name == 'StructuralDesignAgent':
        from .structural_design_agent import StructuralDesignAgent
        return StructuralDesignAgent
    elif name == 'create_structural_design_agent':
        from .structural_design_agent import create_structural_design_agent
        return create_structural_design_agent
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
