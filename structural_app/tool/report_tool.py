"""
Report Tool for OpenManus
Provides report generation capability to agents through factory pattern
"""

from typing import Dict, Any
import json

# Import from structural_app.tool.base
from structural_app.tool.base import BaseTool, ToolResult

# Use absolute imports for report modules
from structural_app.tool.reports.reporter_factory import ReporterFactory
from structural_app.tool.reports.base_reporter import BaseReporter


class ReportTool(BaseTool):
    """
    Tool for generating structured design reports

    This tool uses the factory pattern to route report requests
    to the appropriate reporter based on structure type.

    Generates comprehensive Markdown reports including:
    - Design parameters
    - Analysis results
    - Evaluation results
    - CAD drawing information
    """

    def __init__(self):
        """Initialize the report tool"""
        super().__init__(
            name="report",
            description=(
                "Generate structured design reports. "
                "Supports various structure types (beam, frame, truss, etc.). "
                "Returns file path for the generated Markdown report."
            )
        )
        object.__setattr__(self, 'parameters', self._define_parameters())
        self._custom_output_dir = None

    def _define_parameters(self) -> Dict[str, Any]:
        """
        Define tool parameters

        Returns:
            Parameter schema for the tool
        """
        return {
            "type": "object",
            "properties": {
                "report_data": {
                    "type": "string",
                    "description": "Complete report data in JSON format containing 'design_proposal', 'analysis_results', 'evaluation_report', 'drawing_results', 'bim_results', and 'ifc_results'."
                },
                "structure_type": {
                    "type": "string",
                    "description": f"Type of structure to report. Available: {ReporterFactory.get_available_types()}."
                },
                "design_proposal": {
                    "type": "object",
                    "description": "The design proposal."
                },
                "analysis_results": {
                    "type": "object",
                    "description": "Analysis results from FE analysis."
                },
                "evaluation_report": {
                    "type": "object",
                    "description": "Evaluation report (optional)."
                },
                "drawing_results": {
                    "type": "object",
                    "description": "Drawing results (optional)."
                },
                "bim_results": {
                    "type": "object",
                    "description": "BIM export results with Speckle URL (optional)."
                },
                "ifc_results": {
                    "type": "object",
                    "description": "IFC export results with file path (optional)."
                }
            },
            "required": []
        }

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute report generation

        Args:
            structure_type: Type of structure
            design_proposal: The design proposal
            analysis_results: Analysis results
            evaluation_report: Evaluation report (optional)
            drawing_results: Drawing results (optional)
            OR
            report_data: Complete data in JSON string format

        Returns:
            ToolResult containing report file path or error
        """
        try:
            # Extract parameters
            report_data = kwargs.get('report_data')

            if report_data and isinstance(report_data, str):
                # Parse JSON string
                try:
                    parsed_data = json.loads(report_data)
                    design_proposal = parsed_data.get('design_proposal')
                    analysis_results = parsed_data.get('analysis_results')
                    evaluation_report = parsed_data.get('evaluation_report')
                    drawing_results = parsed_data.get('drawing_results')
                    bim_results = parsed_data.get('bim_results')
                    ifc_results = parsed_data.get('ifc_results')
                except json.JSONDecodeError as e:
                    return ToolResult(output=json.dumps({
                        'status': 'error',
                        'error': f"Failed to parse report_data JSON: {e}"
                    }, ensure_ascii=False))
            else:
                design_proposal = kwargs.get('design_proposal')
                analysis_results = kwargs.get('analysis_results')
                evaluation_report = kwargs.get('evaluation_report')
                drawing_results = kwargs.get('drawing_results')
                bim_results = kwargs.get('bim_results')
                ifc_results = kwargs.get('ifc_results')

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
            if not ReporterFactory.is_registered(structure_type):
                available_types = ReporterFactory.get_available_types()
                error_result = {
                    'status': 'error',
                    'error': f"当前未支持的结构类型: '{structure_type}'。\n"
                            f"可用类型: {available_types}\n"
                            f"请使用已支持的类型，或参考 docs/how_to_add_new_structure_type.md 添加新类型支持。"
                }
                return ToolResult(output=json.dumps(error_result, ensure_ascii=False))

            # Create reporter using factory
            reporter = ReporterFactory.create(structure_type)

            # Set custom output directory if specified
            if self._custom_output_dir:
                reporter.set_output_directory(self._custom_output_dir, None)

            # Generate report
            report_path = reporter.generate_report(
                design_proposal,
                analysis_results,
                evaluation_report,
                drawing_results,
                bim_results,
                ifc_results
            )

            # Format results
            output_data = {
                'status': 'success',
                'report_file': report_path
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
        return ReporterFactory.get_available_types()

    def set_output_directory(self, directory: str, subdirectory: str = None) -> None:
        """
        Set the output directory for generated reports

        Args:
            directory: Path to output directory
            subdirectory: Optional subdirectory (ignored, kept for compatibility)
        """
        self._custom_output_dir = directory
