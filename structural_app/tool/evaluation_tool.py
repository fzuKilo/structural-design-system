"""
Evaluation Tool for OpenManus
Provides design evaluation capability to agents through factory pattern
"""

from typing import Dict, Any, Optional
import json

# Import from structural_app.tool.base
from structural_app.tool.base import BaseTool, ToolResult

# Use absolute imports for evaluator modules
from structural_app.tool.evaluators.evaluator_factory import EvaluatorFactory
from structural_app.tool.evaluators.base_evaluator import DesignEvaluator


class EvaluationTool(BaseTool):
    """
    Tool for performing comprehensive design evaluation

    This tool uses the factory pattern to route evaluation requests
    to the appropriate evaluator based on structure type.

    Implements 4-dimensional evaluation:
    - Economy: Material usage, cost efficiency
    - Structural Efficiency: Stress utilization, redundancy
    - Safety: Safety factors, deflection margins
    - Sustainability: Carbon emissions, recyclability

    Supports: beam, frame, truss, etc. (extensible)
    """

    def __init__(self):
        """Initialize the evaluation tool"""
        super().__init__(
            name="evaluation",
            description=(
                "Perform comprehensive design evaluation. "
                "Supports various structure types (beam, frame, truss, etc.). "
                "Returns comprehensive score (0-100), letter grade (A+/A/B+/B/C+/C/D), "
                "and 4-dimensional evaluation results."
            )
        )
        object.__setattr__(self, 'parameters', self._define_parameters())

    def _define_parameters(self) -> Dict[str, Any]:
        """
        Define tool parameters

        Returns:
            Parameter schema for the tool
        """
        return {
            "type": "object",
            "properties": {
                # Alternative format: Accept complete design proposal and results as JSON string
                "evaluation_data": {
                    "type": "string",
                    "description": "Complete evaluation data in JSON format containing 'design_proposal' and 'analysis_results'. This is an alternative to passing individual parameters."
                },
                # Individual parameters format
                "structure_type": {
                    "type": "string",
                    "description": f"Type of structure to evaluate. Available: {EvaluatorFactory.get_available_types()}. Use this OR evaluation_data, not both.",
                    "enum": EvaluatorFactory.get_available_types()
                },
                "design_proposal": {
                    "type": "object",
                    "description": "The design proposal to evaluate. Use this OR evaluation_data, not both.",
                    "properties": {
                        "type": {"type": "string", "description": "Structure type"},
                        "geometry": {"type": "object", "description": "Geometric parameters"},
                        "material": {"type": "object", "description": "Material properties"},
                        "loads": {"type": "object", "description": "Load cases"},
                        "constraints": {"type": "object", "description": "Boundary conditions"}
                    }
                },
                "analysis_results": {
                    "type": "object",
                    "description": "Analysis results from FE analysis. Use this OR evaluation_data, not both.",
                    "properties": {
                        "status": {"type": "string", "description": "Analysis status"},
                        "results": {"type": "object", "description": "Analysis results data"},
                        "code_check": {"type": "object", "description": "Code compliance results"}
                    }
                }
            },
            # Make evaluation_data mutually exclusive with individual parameters
            "required": []
        }

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute design evaluation

        Args:
            structure_type: Type of structure
            design_proposal: The design proposal to evaluate
            analysis_results: Analysis results from FE analysis
            OR
            evaluation_data: Complete evaluation data in JSON string format

        Returns:
            ToolResult containing evaluation results or error
        """
        try:
            # Extract parameters - support multiple formats
            # Format 1: evaluation_data as JSON string
            # Format 2: individual parameters (structure_type, design_proposal, analysis_results)

            # First try evaluation_data
            evaluation_data = kwargs.get('evaluation_data')

            if evaluation_data and isinstance(evaluation_data, str):
                # Parse JSON string
                try:
                    parsed_data = json.loads(evaluation_data)
                    design_proposal = parsed_data.get('design_proposal')
                    analysis_results = parsed_data.get('analysis_results')
                except json.JSONDecodeError as e:
                    return ToolResult(output=json.dumps({
                        'status': 'error',
                        'error': f"Failed to parse evaluation_data JSON: {e}"
                    }, ensure_ascii=False))
            elif evaluation_data and isinstance(evaluation_data, dict):
                # Extract from evaluation_data dict
                design_proposal = evaluation_data.get('design_proposal')
                analysis_results = evaluation_data.get('analysis_results')
            else:
                # Format 2: Individual parameters
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

            # Get structure type from design proposal
            structure_type = design_proposal.get('type')

            # Validate structure type
            if not EvaluatorFactory.is_registered(structure_type):
                available_types = EvaluatorFactory.get_available_types()
                error_result = {
                    'status': 'error',
                    'error': f"当前未支持的结构类型: '{structure_type}'。\n"
                            f"可用类型: {available_types}\n"
                            f"请使用已支持的类型，或参考 docs/how_to_add_new_structure_type.md 添加新类型支持。"
                }
                return ToolResult(output=json.dumps(error_result, ensure_ascii=False))

            # Create evaluator using factory
            evaluator = EvaluatorFactory.create(structure_type)

            # Perform comprehensive evaluation
            evaluation_result = evaluator.evaluate_comprehensive(design_proposal, analysis_results)

            # Format results for agent consumption
            if evaluation_result['status'] == 'success':
                output_data = {
                    'status': 'success',
                    'comprehensive_score': evaluation_result['comprehensive_score'],
                    'grade': evaluation_result['grade'],
                    'dimensions': evaluation_result['dimensions'],
                    'recommendations': evaluation_result['recommendations']
                }
            else:
                output_data = evaluation_result

            # Use json.dumps to ensure valid JSON string output
            return ToolResult(output=json.dumps(output_data, ensure_ascii=False))

        except Exception as e:
            error_result = {
                'status': 'error',
                'error': f"Tool execution error: {str(e)}"
            }
            return ToolResult(output=json.dumps(error_result, ensure_ascii=False))

    def get_available_structure_types(self) -> list[str]:
        """
        Get list of available structure types

        Returns:
            List of structure type identifiers
        """
        return EvaluatorFactory.get_available_types()
