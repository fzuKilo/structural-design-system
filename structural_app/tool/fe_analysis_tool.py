"""
Finite Element Analysis Tool for OpenManus
Provides FE analysis capability to agents through factory pattern
"""

from typing import Dict, Any, Optional

from openmanus.app.tool.base import BaseTool, ToolResult
from .analyzers.analyzer_factory import AnalyzerFactory
from .analyzers.base_analyzer import StructureAnalyzer


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
                "structure_type": {
                    "type": "string",
                    "description": f"Type of structure to analyze. Available: {AnalyzerFactory.get_available_types()}",
                    "enum": AnalyzerFactory.get_available_types()
                },
                "geometry": {
                    "type": "object",
                    "description": "Geometric parameters (length, width, height, etc.)",
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
                    "description": "Material properties",
                    "properties": {
                        "E": {"type": "number", "description": "Young's modulus in Pa"},
                        "nu": {"type": "number", "description": "Poisson's ratio"},
                        "fy": {"type": "number", "description": "Yield strength in Pa (optional)"}
                    },
                    "required": ["E", "nu"]
                },
                "loads": {
                    "type": "object",
                    "description": "Load cases",
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
                    "description": "Boundary conditions",
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
            "required": ["structure_type", "geometry", "material", "loads", "constraints"]
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

        Returns:
            ToolResult containing analysis results or error
        """
        try:
            # Extract parameters
            structure_type = kwargs.get('structure_type')
            geometry = kwargs.get('geometry')
            material = kwargs.get('material')
            loads = kwargs.get('loads')
            constraints = kwargs.get('constraints')

            # Validate structure type
            if not AnalyzerFactory.is_registered(structure_type):
                return ToolResult(
                    error=f"Unknown structure type: {structure_type}. Available: {AnalyzerFactory.get_available_types()}"
                )

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

                return ToolResult(output=str(output_data))
            else:
                return ToolResult(error=result['error'])

        except Exception as e:
            return ToolResult(error=f"Tool execution error: {str(e)}")

    def get_available_structure_types(self) -> list[str]:
        """
        Get list of available structure types

        Returns:
            List of structure type identifiers
        """
        return AnalyzerFactory.get_available_types()
