"""
Agent module for structural design system
"""

# Lazy imports to avoid namespace conflicts with OpenManus
# Import directly when needed instead of at module level

__all__ = [
    'StructuralDesignAgent',
    'create_structural_design_agent',
    'FEAnalysisAgent',
    'create_fe_analysis_agent',
    'CADDrawingAgent',
    'create_cad_drawing_agent',
]

def __getattr__(name):
    """Lazy import to avoid early namespace conflicts"""
    if name == 'StructuralDesignAgent':
        from .structural_design_agent import StructuralDesignAgent
        return StructuralDesignAgent
    elif name == 'create_structural_design_agent':
        from .structural_design_agent import create_structural_design_agent
        return create_structural_design_agent
    elif name == 'FEAnalysisAgent':
        from .fe_analysis_agent import FEAnalysisAgent
        return FEAnalysisAgent
    elif name == 'create_fe_analysis_agent':
        from .fe_analysis_agent import create_fe_analysis_agent
        return create_fe_analysis_agent
    elif name == 'CADDrawingAgent':
        from .cad_drawing_agent import CADDrawingAgent
        return CADDrawingAgent
    elif name == 'create_cad_drawing_agent':
        from .cad_drawing_agent import create_cad_drawing_agent
        return create_cad_drawing_agent
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
