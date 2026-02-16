"""
Finite Element Analysis Tool for OpenManus
Provides FE analysis capability to agents through factory pattern
"""

from typing import Dict, Any, Optional
import json

# Handle OpenManus import with path fallback
try:
    from openmanus.app.tool.base import BaseTool, ToolResult
except ImportError:
    from app.tool.base import BaseTool, ToolResult
# Use absolute imports for analyzer modules
from structural_app.tool.analyzers.analyzer_factory import AnalyzerFactory
from structural_app.tool.analyzers.base_analyzer import StructureAnalyzer


class FEAnalysisTool(BaseTool):
    """
    Tool for performing finite element analysis on structures

    This tool uses the factory pattern to route analysis requests
    to the appropriate analyzer based on structure type.

    Supports: beam, frame, truss, etc. (extensible)
    """

    def __init__(self):
        """Initialize the FE analysis tool"""
        super().__init__(
            name="fe_analysis",
            description=(
                "Perform finite element analysis on structural designs. "
                "Supports various structure types (beam, frame, truss, etc.). "
                "Returns displacement, stress, moment, shear results and code compliance check."
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
                # Alternative format: Accept complete design proposal as JSON string
                "design_proposal": {
                    "type": "string",
                    "description": "Complete design proposal in JSON format. This is an alternative to passing individual parameters. If provided, this will be used instead of individual parameters."
                },
                # Individual parameters (traditional format)
                "structure_type": {
                    "type": "string",
                    "description": f"Type of structure to analyze. Available: {AnalyzerFactory.get_available_types()}. Use this OR design_proposal, not both.",
                    "enum": AnalyzerFactory.get_available_types()
                },
                "geometry": {
                    "type": "object",
                    "description": "Geometric parameters (length, width, height, etc). Use this OR design_proposal, not both.",
                    "properties": {
                        "length": {"type": "number", "description": "Length in meters"},
                        "width": {"type": "number", "description": "Width in meters"},
                        "height": {"type": "number", "description": "Height in meters"},
                        "n_elements": {"type": "integer", "description": "Number of finite elements (optional, default 20)"}
                    },
                    "required": ["length", "width", "height"]
                },
                "material": {
                    "type": "object",
                    "description": "Material properties. Use this OR design_proposal, not both.",
                    "properties": {
                        "E": {"type": "number", "description": "Young's modulus in Pa"},
                        "nu": {"type": "number", "description": "Poisson's ratio"},
                        "fy": {"type": "number", "description": "Yield strength in Pa (optional)"}
                    },
                    "required": ["E", "nu"]
                },
                "loads": {
                    "type": "object",
                    "description": "Load cases. Use this OR design_proposal, not both.",
                    "properties": {
                        "distributed": {
                            "type": "array",
                            "description": "Distributed loads",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "q": {"type": "number", "description": "Load intensity in N/m"},
                                    "direction": {"type": "string", "enum": ["x", "y"], "description": "Load direction"}
                                },
                                "required": ["q"]
                            }
                        },
                        "point": {
                            "type": "array",
                            "description": "Point loads",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "P": {"type": "number", "description": "Load magnitude in N"},
                                    "location": {"type": "number", "description": "Position along beam in m"},
                                    "direction": {"type": "string", "enum": ["x", "y"], "description": "Load direction"}
                                },
                                "required": ["P", "location"]
                            }
                        }
                    }
                },
                "constraints": {
                    "type": "object",
                    "description": "Boundary conditions. Use this OR design_proposal, not both.",
                    "properties": {
                        "support_type": {
                            "type": "string",
                            "enum": ["simply_supported", "cantilever", "fixed_fixed"],
                            "description": "Type of support"
                        }
                    },
                    "required": ["support_type"]
                }
            },
            # Make design_proposal mutually exclusive with individual parameters
            # At least one format must be provided
            "required": []
        }

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute finite element analysis

        Args:
            structure_type: Type of structure
            geometry: Geometric parameters
            material: Material properties
            loads: Load cases
            constraints: Boundary conditions
            OR
            design_proposal: Complete design proposal in JSON string format (alternative)

        Returns:
            ToolResult containing analysis results or error
        """
        try:
            import json as json_module

            # Extract parameters - support both formats
            # Format 1: Individual parameters (structure_type, geometry, etc.)
            # Format 2: design_proposal as JSON string (from agent)

            design_proposal = kwargs.get('design_proposal')

            if design_proposal and isinstance(design_proposal, str):
                # Parse JSON string
                try:
                    parsed_proposal = json_module.loads(design_proposal)
                    structure_type = parsed_proposal.get('type')
                    geometry = parsed_proposal.get('geometry')
                    material = parsed_proposal.get('material')
                    loads = parsed_proposal.get('loads')
                    constraints = parsed_proposal.get('constraints')
                except json_module.JSONDecodeError as e:
                    return ToolResult(output=json_module.dumps({
                        'status': 'error',
                        'error': f"Failed to parse design_proposal JSON: {e}"
                    }, ensure_ascii=False))
            elif design_proposal and isinstance(design_proposal, dict):
                # Extract from design_proposal dict
                structure_type = design_proposal.get('type')
                geometry = design_proposal.get('geometry')
                material = design_proposal.get('material')
                loads = design_proposal.get('loads')
                constraints = design_proposal.get('constraints')
            else:
                # Format 1: Individual parameters
                structure_type = kwargs.get('structure_type')
                geometry = kwargs.get('geometry')
                material = kwargs.get('material')
                loads = kwargs.get('loads')
                constraints = kwargs.get('constraints')

            # Validate structure type
            if not AnalyzerFactory.is_registered(structure_type):
                error_result = {
                    'status': 'error',
                    'error': f"Unknown structure type: {structure_type}. Available: {AnalyzerFactory.get_available_types()}"
                }
                return ToolResult(output=json.dumps(error_result, ensure_ascii=False))

            # Create analyzer using factory
            analyzer = AnalyzerFactory.create(structure_type)

            # Prepare design parameters
            design = {
                'type': structure_type,
                'geometry': geometry,
                'material': material,
                'loads': loads,
                'constraints': constraints
            }

            # Run full analysis (validate -> build -> analyze -> check)
            result = analyzer.run_full_analysis(design)

            # Format results for agent consumption
            if result['status'] == 'success':
                analysis_results = result['results']
                code_check = result['code_check']

                output_data = {
                    'status': 'success',
                    'results': {
                        'max_displacement': analysis_results.max_displacement,
                        'max_displacement_mm': analysis_results.max_displacement * 1000,
                        'max_stress': analysis_results.max_stress,
                        'max_stress_MPa': analysis_results.max_stress / 1e6,
                        'max_moment': analysis_results.max_moment,
                        'max_moment_kNm': analysis_results.max_moment / 1000,
                        'max_shear': analysis_results.max_shear,
                        'max_shear_kN': analysis_results.max_shear / 1000,
                        'structure_type': analysis_results.structure_type,
                        'detailed_results': analysis_results.to_dict()
                    },
                    'code_check': code_check
                }

                # Use json.dumps to ensure valid JSON string output
                return ToolResult(output=json.dumps(output_data, ensure_ascii=False))
            else:
                error_result = {
                    'status': 'error',
                    'error': result['error']
                }
                return ToolResult(output=json.dumps(error_result, ensure_ascii=False))

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
        return AnalyzerFactory.get_available_types()
