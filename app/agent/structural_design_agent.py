"""
Structural Design Agent for OpenManus
Handles parameter collection and initial structural design
"""

import sys
import os
from typing import Dict, Any, Optional, List
import json
import re

# Add OpenManus to path for imports (temporary solution until proper package installation)
# CRITICAL: Must be at position 0 to override local 'app' package
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
_openmanus_path = os.path.join(os.path.dirname(_project_root), 'openmanus')

if os.path.exists(_openmanus_path):
    # Remove current project root from sys.path temporarily to avoid conflicts
    _paths_to_restore = []
    for path in list(sys.path):
        if os.path.abspath(path) == _project_root:
            sys.path.remove(path)
            _paths_to_restore.append(path)

    # Add OpenManus at position 0
    if _openmanus_path not in sys.path:
        sys.path.insert(0, _openmanus_path)

from app.agent.toolcall import ToolCallAgent
from app.tool.ask_human import AskHuman

# Restore removed paths after imports
if os.path.exists(_openmanus_path):
    for path in _paths_to_restore:
        if path not in sys.path:
            sys.path.append(path)


class StructuralDesignAgent(ToolCallAgent):
    """
    Agent responsible for structural design parameter collection and initial design

    This agent:
    1. Receives user requirements in natural language
    2. Uses AskHuman tool to collect missing parameters
    3. Calls LLM to generate initial design
    4. Outputs standardized DesignProposal

    Key Features:
    - Generic: handles all structure types (beam, frame, truss, etc.)
    - LLM-driven: leverages LLM's structural engineering knowledge
    - Interactive: asks user for missing parameters
    - Standardized output: always includes 'type' field for routing
    """

    def __init__(
        self,
        name: str = "StructuralDesignAgent",
        description: str = None,
        tools: Optional[List] = None,
        **kwargs
    ):
        """
        Initialize the Structural Design Agent

        Args:
            name: Agent name (default: "StructuralDesignAgent")
            description: Agent description
            tools: List of tools available to the agent
            **kwargs: Additional arguments passed to ToolCallAgent
        """
        if description is None:
            description = (
                "I am a structural design agent. I help collect design parameters "
                "and generate initial structural design proposals. I can design "
                "various structure types including beams, frames, trusses, and more. "
                "I will ask you questions to gather necessary information and then "
                "provide a complete design proposal."
            )

        # Initialize with AskHuman tool if not provided
        if tools is None:
            tools = [AskHuman()]
        elif not any(isinstance(tool, AskHuman) for tool in tools):
            tools.append(AskHuman())

        super().__init__(
            name=name,
            description=description,
            tools=tools,
            **kwargs
        )

        # System prompt for design generation
        self.design_system_prompt = self._create_design_system_prompt()

    def _create_design_system_prompt(self) -> str:
        """
        Create system prompt for LLM design generation

        Returns:
            System prompt string
        """
        return """You are an expert structural engineer with deep knowledge of:
- Structural mechanics and analysis
- Material properties and selection
- Load calculations and combinations
- Design codes and standards (GB, AISC, Eurocode)
- Various structure types: beams, frames, trusses, plates, shells, etc.

Your task is to generate initial structural design proposals based on user requirements.

CRITICAL OUTPUT FORMAT:
You MUST output a valid JSON object with the following structure:

{
  "type": "<structure_type>",  // REQUIRED: "beam", "frame", "truss", etc.
  "geometry": {
    "length": <number>,        // in meters
    "width": <number>,         // in meters (for cross-section)
    "height": <number>,        // in meters (for cross-section)
    "n_elements": <integer>    // number of finite elements (default: 20)
  },
  "material": {
    "E": <number>,             // Young's modulus in Pa (e.g., 30e9 for C30 concrete)
    "nu": <number>,            // Poisson's ratio (e.g., 0.2 for concrete)
    "fy": <number>,            // Yield strength in Pa (optional)
    "material_name": "<string>" // e.g., "C30", "Q235", "Grade 60"
  },
  "loads": {
    "distributed": [           // Distributed loads
      {
        "q": <number>,         // Load intensity in N/m (negative for downward)
        "direction": "y"       // "x" or "y"
      }
    ],
    "point": [                 // Point loads (optional)
      {
        "P": <number>,         // Load magnitude in N
        "location": <number>,  // Position along beam in m
        "direction": "y"       // "x" or "y"
      }
    ]
  },
  "constraints": {
    "support_type": "<type>"   // "simply_supported", "cantilever", "fixed_fixed"
  }
}

DESIGN GUIDELINES:
1. For beams:
   - Typical span-to-depth ratio: L/10 to L/15
   - Width typically 0.3-0.5m for concrete beams
   - Use C30 concrete (E=30GPa) or Q235 steel (E=200GPa) as defaults

2. For loads:
   - Residential: 2-3 kN/m² live load
   - Office: 3-4 kN/m² live load
   - Convert area loads to line loads based on tributary width

3. Material selection:
   - Concrete: E=30e9 Pa, nu=0.2, fy=14.3e6 Pa (C30)
   - Steel: E=200e9 Pa, nu=0.3, fy=235e6 Pa (Q235)

4. Always include the "type" field - this is CRITICAL for routing to the correct analyzer.

5. Use engineering judgment to fill in missing parameters with reasonable defaults.

OUTPUT ONLY THE JSON - no explanations before or after."""

    async def run(self, task: str, **kwargs) -> Dict[str, Any]:
        """
        Main execution method for the agent

        Args:
            task: User's design requirement in natural language
            **kwargs: Additional parameters

        Returns:
            Dict containing the design proposal
        """
        # Prepare the design generation prompt
        design_prompt = f"""User Requirement:
{task}

Please analyze the requirement and generate a complete structural design proposal.
If any critical information is missing, use the AskHuman tool to ask the user.

Remember to output ONLY a valid JSON object following the specified format."""

        # Call the parent run method with the design system prompt
        result = await super().run(
            task=design_prompt,
            system_prompt=self.design_system_prompt,
            **kwargs
        )

        return result

    def extract_design_proposal(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract DesignProposal JSON from LLM response

        Args:
            response: LLM response text

        Returns:
            Parsed design proposal dict, or None if extraction fails
        """
        try:
            # Try to find JSON block in the response
            # Pattern 1: ```json ... ```
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)

            # Pattern 2: ``` ... ```
            json_match = re.search(r'```\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)

            # Pattern 3: Direct JSON object
            json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)

            return None

        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            return None

    def validate_design_proposal(self, proposal: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate that the design proposal has all required fields

        Args:
            proposal: Design proposal dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = {
            'type': str,
            'geometry': dict,
            'material': dict,
            'loads': dict,
            'constraints': dict
        }

        # Check top-level required fields
        for field, field_type in required_fields.items():
            if field not in proposal:
                return False, f"Missing required field: {field}"
            if not isinstance(proposal[field], field_type):
                return False, f"Field '{field}' must be of type {field_type.__name__}"

        # Validate geometry
        geometry_required = ['length', 'width', 'height']
        for field in geometry_required:
            if field not in proposal['geometry']:
                return False, f"Missing required geometry field: {field}"

        # Validate material
        material_required = ['E', 'nu']
        for field in material_required:
            if field not in proposal['material']:
                return False, f"Missing required material field: {field}"

        # Validate loads
        if 'distributed' not in proposal['loads'] and 'point' not in proposal['loads']:
            return False, "Loads must contain at least 'distributed' or 'point' loads"

        # Validate constraints
        if 'support_type' not in proposal['constraints']:
            return False, "Missing required constraint field: support_type"

        return True, None

    def format_design_proposal_output(self, proposal: Dict[str, Any]) -> str:
        """
        Format design proposal for output to next agent

        Args:
            proposal: Design proposal dictionary

        Returns:
            Formatted JSON string
        """
        return json.dumps(proposal, indent=2, ensure_ascii=False)


# Register the agent for use in PlanningFlow
def create_structural_design_agent(**kwargs) -> StructuralDesignAgent:
    """
    Factory function to create StructuralDesignAgent instance

    Args:
        **kwargs: Arguments passed to StructuralDesignAgent constructor

    Returns:
        StructuralDesignAgent instance
    """
    return StructuralDesignAgent(**kwargs)
