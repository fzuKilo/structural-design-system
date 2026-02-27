"""
Visualization Tool for OpenManus
Provides visualization capability to agents through factory pattern
"""

from typing import Dict, Any
import json

# Import from structural_app.tool.base
from structural_app.tool.base import BaseTool, ToolResult

# Use absolute imports for visualization modules
from structural_app.tool.visualizations.visualizer_factory import VisualizerFactory
from structural_app.tool.visualizations.base_visualizer import BaseVisualizer


class VisualizationTool(BaseTool):
    """
    Tool for generating visualizations of structural analysis results

    This tool uses the factory pattern to route visualization requests
    to the appropriate visualizer based on structure type.

    Supports:
    - Static visualizations (matplotlib PNG)
    - Interactive visualizations (Plotly HTML)

    Visualizations include:
    - Moment diagrams
    - Shear diagrams
    - Deflection curves
    - Stress contours (future)
    """

    def __init__(self):
        """Initialize the visualization tool"""
        super().__init__(
            name="visualization",
            description=(
                "Generate visualizations for structural analysis results. "
                "Supports various structure types (beam, frame, truss, etc.). "
                "Returns file paths for static (PNG) and interactive (HTML) visualizations."
            )
        )

    def _define_parameters(self) -> Dict[str, Any]:
        """
        Define tool parameters

        Returns:
            Parameter schema for the tool
        """
        return {
            "type": "object",
            "properties": {
                "visualization_data": {
                    "type": "string",
                    "description": "Complete visualization data in JSON format containing 'design_proposal' and 'analysis_results'."
                },
                "structure_type": {
                    "type": "string",
                    "description": f"Type of structure to visualize. Available: {VisualizerFactory.get_available_types()}."
                },
                "design_proposal": {
                    "type": "object",
                    "description": "The design proposal to visualize."
                },
                "analysis_results": {
                    "type": "object",
                    "description": "Analysis results from FE analysis."
                }
            },
            "required": []
        }

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute visualization generation

        Args:
            structure_type: Type of structure
            design_proposal: The design proposal
            analysis_results: Analysis results from FE analysis
            OR
            visualization_data: Complete data in JSON string format

        Returns:
            ToolResult containing visualization file paths or error
        """
        try:
            # Extract parameters
            visualization_data = kwargs.get('visualization_data')

            if visualization_data and isinstance(visualization_data, str):
                # Parse JSON string
                try:
                    parsed_data = json.loads(visualization_data)
                    design_proposal = parsed_data.get('design_proposal')
                    analysis_results = parsed_data.get('analysis_results')
                except json.JSONDecodeError as e:
                    return ToolResult(output=json.dumps({
                        'status': 'error',
                        'error': f"Failed to parse visualization_data JSON: {e}"
                    }, ensure_ascii=False))
            elif visualization_data and isinstance(visualization_data, dict):
                design_proposal = visualization_data.get('design_proposal')
                analysis_results = visualization_data.get('analysis_results')
            else:
                design_proposal = kwargs.get('design_proposal')
                analysis_results = kwargs.get('analysis_results')

            # Validate required data
            if not design_proposal:
                return ToolResult(output=json.dumps({
                    'status': 'error',
                    'error': "Missing required parameter: 'design_proposal'"
                }, ensure_ascii=False))

            if not analysis_results:
                return ToolResult(output=json.dumps({
                    'status': 'error',
                    'error': "Missing required parameter: 'analysis_results'"
                }, ensure_ascii=False))

            # Get structure type
            structure_type = design_proposal.get('type')

            # Validate structure type
            if not VisualizerFactory.is_registered(structure_type):
                available_types = VisualizerFactory.get_available_types()
                error_result = {
                    'status': 'error',
                    'error': f"当前未支持的结构类型: '{structure_type}'。\n"
                            f"可用类型: {available_types}\n"
                            f"请使用已支持的类型，或参考 docs/how_to_add_new_structure_type.md 添加新类型支持。"
                }
                return ToolResult(output=json.dumps(error_result, ensure_ascii=False))

            # Create visualizer using factory
            visualizer = VisualizerFactory.create(structure_type)

            # Generate visualizations
            visualization_results = visualizer.generate_all_visualizations(design_proposal, analysis_results)

            # Format results
            output_data = {
                'status': 'success',
                'visualizations': visualization_results
            }

            return ToolResult(output=json.dumps(output_data, ensure_ascii=False))

        except Exception as e:
            error_result = {
                'status': 'error',
                'error': f"Tool execution error: {str(e)}"
            }
            return ToolResult(output=json.dumps(error_result, ensure_ascii=False))

    def get_available_structure_types(self) -> list[str]:
        """Get list of available structure types"""
        return VisualizerFactory.get_available_types()
