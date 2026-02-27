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
    'EvaluationAgent',
    'create_evaluation_agent',
    'ReportGenerationAgent',
    'create_report_generation_agent',
    'PlanningFlow',
    'create_planning_flow',
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
    elif name == 'EvaluationAgent':
        from .evaluation_agent import EvaluationAgent
        return EvaluationAgent
    elif name == 'create_evaluation_agent':
        from .evaluation_agent import create_evaluation_agent
        return create_evaluation_agent
    elif name == 'ReportGenerationAgent':
        from .report_generation_agent import ReportGenerationAgent
        return ReportGenerationAgent
    elif name == 'create_report_generation_agent':
        from .report_generation_agent import create_report_generation_agent
        return create_report_generation_agent
    elif name == 'PlanningFlow':
        from ..planning_flow import PlanningFlow
        return PlanningFlow
    elif name == 'create_planning_flow':
        from ..planning_flow import create_planning_flow
        return create_planning_flow
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
