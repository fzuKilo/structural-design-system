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

CRITICAL PARAMETER HANDLING:
When calling the cad_drawing tool, you MUST extract parameters from the DesignProposal and pass them to the tool.

IMPORTANT - DO NOT CONVERT OR MODIFY PARAMETERS:
1. Pass geometry parameters EXACTLY as they appear in the DesignProposal
   - If DesignProposal has "span", pass "span" (do NOT convert to "length")
   - If DesignProposal has "n_panels", pass "n_panels" (do NOT convert to "n_elements")
   - If DesignProposal has "nodal" loads, pass "nodal" (do NOT convert to "point" or "distributed")
2. DO NOT add missing fields with default values (like "width": 0.0)
3. DO NOT replace one parameter with another (like replacing n_panels with n_elements)
4. The cad_drawing tool accepts parameters in their original format

TRUSS-SPECIFIC NOTES:
For truss structures, the DesignProposal uses:
- geometry.span (NOT "length")
- geometry.n_panels (NOT "n_elements")
- loads.nodal (NOT "point" or "distributed")

Example of CORRECT parameter extraction for truss:
Input DesignProposal:
{
  "type": "truss",
  "geometry": {"span": 6.0, "height": 1.2, "n_panels": 6},
  "loads": {"nodal": [...]},
  ...
}

CORRECT cad_drawing tool call:
{
  "structure_type": "truss",
  "geometry": {"span": 6.0, "height": 1.2, "n_panels": 6},  // Keep original parameter names!
  "loads": {"nodal": [...]},  // Keep original format!
  ...
}

WRONG cad_drawing tool call (DO NOT DO THIS):
{
  "structure_type": "truss",
  "geometry": {"length": 6.0, "width": 0.0, "height": 1.2, "n_elements": 25},  // ❌ Wrong! Converted parameters
  "loads": {"distributed": [], "point": []},  // ❌ Wrong! Converted load format
  ...
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
    "generated_at": "<timestamp>",
    "plan_preview": "<path_to_png_or_null>",
    "elevation_preview": "<path_to_png_or_null>",
    "detail_preview": "<path_to_png_or_null>"
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
            # Modified to handle JSON that may or may not have trailing newline
            pattern = r'cad_drawing.*?executed:\s*(\{[\s\S]*?\})\s*(?:Step|\Z)'
            matches = re.findall(pattern, response, re.DOTALL)

            if matches:
                # Get the last match (most recent execution)
                json_str = matches[-1]
                return json.loads(json_str)

            # Pattern 2: Extract from code block
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)

            # Pattern 3: Direct JSON object with status field (fallback)
            # Find balanced JSON objects containing "status" field
            balanced_json = self._find_balanced_json_with_status(response)
            if balanced_json:
                return json.loads(balanced_json)

            return None

        except json.JSONDecodeError as e:
            print(f"Failed to parse drawing results JSON: {e}")
            return None

    def _find_balanced_json_with_status(self, response: str) -> Optional[str]:
        """
        Find balanced JSON object containing status field

        Args:
            response: LLM response text

        Returns:
            Balanced JSON string, or None if not found
        """
        i = 0
        while i < len(response):
            if response[i] == '{':
                # Found opening brace, find matching closing brace
                brace_count = 0
                start = i
                for j in range(i, len(response)):
                    if response[j] == '{':
                        brace_count += 1
                    elif response[j] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = response[start:j+1]
                            if '"status"' in json_str:
                                return json_str
                            break
                i = j + 1
            else:
                i += 1
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
