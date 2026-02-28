"""
CAD Drawing Agent for OpenManus
Generates CAD drawings for structural designs
"""

from typing import Dict, Any, Optional, List
import json

from app.agent.toolcall import ToolCallAgent
from app.tool.ask_human import AskHuman
from app.schema import Message
from app.tool import ToolCollection, CreateChatCompletion, Terminate

# Import CADDrawingTool with path handling
import importlib.util
import os

# Get the directory where this file is located
_current_dir = os.path.dirname(os.path.abspath(__file__))
_structural_app_path = os.path.dirname(_current_dir)

# Load CADDrawingTool module directly
_cad_tool_path = os.path.join(_structural_app_path, 'tool', 'cad_drawing_tool.py')
_spec = importlib.util.spec_from_file_location("cad_drawing_tool", _cad_tool_path)
cad_drawing_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cad_drawing_module)
CADDrawingTool = cad_drawing_module.CADDrawingTool

# Get DrawerFactory from already-loaded CADDrawingTool module
DrawerFactory = cad_drawing_module.DrawerFactory


class CADDrawingAgent(ToolCallAgent):
    """
    Agent responsible for generating CAD drawings for structural designs.

    This agent:
    1. Receives a DesignProposal (from context or user input)
    2. Calls CADDrawingTool to generate CAD drawings
    3. Returns DrawingResults in JSON format
    4. Supports loop mode: when drawing fails, ask user for corrections

    Key Features:
    - Generic: handles all structure types (beam, frame, truss, etc.)
    - Uses CADDrawingTool with factory pattern routing
    - Standardized input/output via DesignProposal/DrawingResults
    """

    def __init__(
        self,
        name: str = "CADDrawingAgent",
        description: str = None,
        tools: Optional[List] = None,
        **kwargs
    ):
        """
        Initialize the CAD Drawing Agent

        Args:
            name: Agent name (default: "CADDrawingAgent")
            description: Agent description
            tools: List of tools available to the agent
            **kwargs: Additional arguments passed to ToolCallAgent
        """
        if description is None:
            description = (
                "I am a CAD drawing agent. I generate CAD drawings for structural designs. "
                "I receive a structural design proposal as input and return comprehensive "
                "drawing files including plan view, elevation view, and detail views."
            )

        # Initialize with CADDrawingTool and AskHuman if not provided
        if tools is None:
            tools = [CADDrawingTool(), AskHuman()]
        else:
            # Add CADDrawingTool if not present
            has_cad_drawing = any(isinstance(tool, CADDrawingTool) for tool in tools)
            if not has_cad_drawing:
                tools.append(CADDrawingTool())

            # Add AskHuman if not present
            has_ask_human = any(isinstance(tool, AskHuman) for tool in tools)
            if not has_ask_human:
                tools.append(AskHuman())

        super().__init__(
            name=name,
            description=description,
            tools=tools,
            **kwargs
        )

        # Override available_tools to include all tools
        all_tools = tools + [CreateChatCompletion(), Terminate()]
        object.__setattr__(self, 'available_tools', ToolCollection(*all_tools))

        # Set system prompt for CAD drawing
        object.__setattr__(self, 'system_prompt', self._create_cad_drawing_system_prompt())

    def _create_cad_drawing_system_prompt(self) -> str:
        """
        Create system prompt for CAD drawing

        Returns:
            System prompt string
        """
        return """You are an expert CAD drawing agent.

Your task is to generate CAD drawings for structural designs.

INPUT FORMAT:
You will receive a DesignProposal in JSON format with the following structure:
{
  "type": "<structure_type>",  // "beam", "frame", "truss", etc.
  "units": "m" or "mm",        // Units for geometry values (default: "m")
  "geometry": {
    "length": <number>,        // in specified units (m or mm)
    "width": <number>,         // in specified units (for cross-section)
    "height": <number>,        // in specified units (for cross-section)
    "n_elements": <integer>    // number of finite elements
  },
  "material": {
    "E": <number>,             // Young's modulus in Pa
    "nu": <number>,            // Poisson's ratio
    "fy": <number>             // Yield strength in Pa (optional)
  },
  "loads": {
    "distributed": [           // Distributed loads
      {"q": <number>, "direction": "y"}
    ],
    "point": [                 // Point loads (optional)
      {"P": <number>, "location": <number>, "direction": "y"}
    ]
  },
  "constraints": {
    "support_type": "<type>"   // "simply_supported", "cantilever", "fixed_fixed"
  }
}

OUTPUT FORMAT:
You MUST use the cad_drawing tool to generate the drawings.
The cad_drawing tool will return DrawingResults in this format:
{
  "status": "success",
  "files": {
    "plan_view": "<path_to_dxf>",
    "elevation_view": "<path_to_dxf>",
    "section_view": "<path_to_dxf>",
    "detail_view": "<path_to_dxf>"
  },
  "metadata": {
    "structure_type": "<type>",
    "drawing_standard": "GB/T 50001-2017",
    "scale": "1:50",
    "units": "mm",
    "generated_at": "<timestamp>"
  },
  "notes": [...]
}

IMPORTANT:
- Always use the cad_drawing tool to generate the drawings
- Do not try to create drawings manually
- Pass the complete DesignProposal to the cad_drawing tool
- **CRITICAL: The DesignProposal MUST include the "units" field** ("m" for meters or "mm" for millimeters)
- Return the DrawingResults exactly as provided by the cad_drawing tool

DRAWING WORKFLOW:
1. Extract the DesignProposal from the input
2. Call the cad_drawing tool with the DesignProposal
3. Return the DrawingResults to the user
"""

    async def run(self, request: str, **kwargs) -> str:
        """
        Main execution method for the agent.

        Args:
            request: User's request (typically contains a DesignProposal)
            **kwargs: Additional parameters

        Returns:
            String containing the drawing results
        """
        # Prepare the drawing prompt
        drawing_prompt = f"""{request}

Use the cad_drawing tool to generate the CAD drawings.
Return the complete DrawingResults."""

        # Call the parent run method (system_prompt is already set in __init__)
        result = await super().run(request=drawing_prompt, **kwargs)

        return result

    def extract_drawing_results(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract DrawingResults JSON from LLM response

        Args:
            response: LLM response text (may contain cad_drawing tool output)

        Returns:
            Parsed drawing results dict, or None if extraction fails
        """
        try:
            import re
            import json

            # Pattern 1: Extract from cad_drawing tool output
            pattern = r'cad_drawing.*?executed:\s*(\{.*?\})\s*(?:Step|\Z)'
            matches = re.findall(pattern, response, re.DOTALL)

            if matches:
                # Get the last match (most recent execution)
                json_str = matches[-1]
                return json.loads(json_str)

            # Pattern 2: Extract from code block
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)

            # Pattern 3: Direct JSON object with status field (fallback)
            matches = re.findall(r'\{[^}]*"status"[^}]*\}', response, re.DOTALL)
            if matches:
                json_str = matches[-1]
                return json.loads(json_str)

            return None

        except json.JSONDecodeError as e:
            print(f"Failed to parse drawing results JSON: {e}")
            return None


# Register the agent for use in PlanningFlow
def create_cad_drawing_agent(**kwargs) -> CADDrawingAgent:
    """
    Factory function to create CADDrawingAgent instance

    Args:
        **kwargs: Arguments passed to CADDrawingAgent constructor

    Returns:
        CADDrawingAgent instance
    """
    return CADDrawingAgent(**kwargs)
