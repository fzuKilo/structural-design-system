"""
CAD Drawing Tool for OpenManus
Provides CAD drawing capability to agents through factory pattern
"""

from typing import Dict, Any, Optional

try:
    from openmanus.app.tool.base import BaseTool, ToolResult
except ImportError:
    # For development without OpenManus installed
    # This allows testing the tool logic independently
    class BaseTool:
        """Mock BaseTool for development"""
        def __init__(self, name: str = "", description: str = ""):
            self.name = name
            self.description = description

    class ToolResult:
        """Mock ToolResult for development"""
        def __init__(self, output: str = "", error: str = ""):
            self.output = output
            self.error = error


# Use absolute imports for drawer modules
from structural_app.tool.drawers.drawer_factory import DrawerFactory
from structural_app.tool.drawers.base_drawer import StructureDrawer


class CADDrawingTool(BaseTool):
    """
    Tool for performing CAD drawing on structural designs

    This tool uses the factory pattern to route drawing requests
    to the appropriate drawer based on structure type.

    Supports: beam, frame, truss, etc. (extensible)
    """

    def __init__(self):
        """Initialize the CAD drawing tool"""
        super().__init__(
            name="cad_drawing",
            description=(
                "Generate CAD drawings for structural designs. "
                "Supports various structure types (beam, frame, truss, etc.). "
                "Returns DXF files for plan view, elevation view, and detail views."
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
                    "description": f"Type of structure to draw. Available: {DrawerFactory.get_available_types()}",
                    "enum": DrawerFactory.get_available_types()
                },
                "geometry": {
                    "type": "object",
                    "description": "Geometric parameters (length, width, height, etc.)",
                    "properties": {
                        "length": {"type": "number", "description": "Length in meters"},
                        "width": {"type": "number", "description": "Width in meters"},
                        "height": {"type": "number", "description": "Height in meters"},
                        "n_elements": {"type": "integer", "description": "Number of finite elements (optional)"}
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
        Execute CAD drawing generation

        Args:
            structure_type: Type of structure
            geometry: Geometric parameters
            material: Material properties
            loads: Load cases
            constraints: Boundary conditions

        Returns:
            ToolResult containing drawing results or error
        """
        try:
            # Extract parameters
            structure_type = kwargs.get('structure_type')
            geometry = kwargs.get('geometry')
            material = kwargs.get('material')
            loads = kwargs.get('loads')
            constraints = kwargs.get('constraints')

            # Validate structure type
            if not DrawerFactory.is_registered(structure_type):
                available_types = DrawerFactory.get_available_types()
                error_msg = (
                    f"当前未支持的结构类型: '{structure_type}'。\n"
                    f"可用类型: {available_types}\n"
                    f"请使用已支持的类型，或参考 docs/how_to_add_new_structure_type.md 添加新类型支持。"
                )
                return ToolResult(error=error_msg)

            # Create drawer using factory
            drawer = DrawerFactory.create(structure_type)

            # Prepare design parameters
            design = {
                'type': structure_type,
                'geometry': geometry,
                'material': material,
                'loads': loads,
                'constraints': constraints
            }

            # Generate all drawings
            results = drawer.generate_drawings(design)

            # Format results for agent consumption
            output_data = {
                'status': 'success',
                'files': results.get_files(),
                'metadata': {
                    'structure_type': results.structure_type,
                    'drawing_standard': results.drawing_standard,
                    'scale': results.scale,
                    'units': results.units,
                    'generated_at': results.generated_at
                },
                'notes': results.notes
            }

            return ToolResult(output=str(output_data))

        except Exception as e:
            return ToolResult(error=f"Tool execution error: {str(e)}")

    def get_available_structure_types(self) -> list[str]:
        """
        Get list of available structure types

        Returns:
            List of structure type identifiers
        """
        return DrawerFactory.get_available_types()
