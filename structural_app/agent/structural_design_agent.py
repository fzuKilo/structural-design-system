"""
Structural Design Agent for OpenManus
Handles parameter collection and initial structural design
"""

from typing import Dict, Any, Optional, List
import json
import re

from app.agent.toolcall import ToolCallAgent
from app.tool.ask_human import AskHuman


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

        # Set system prompt for design generation
        self.system_prompt = self._create_design_system_prompt()

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

    async def run(self, request: str, **kwargs) -> str:
        """
        Main execution method for the agent

        Args:
            request: User's design requirement in natural language
            **kwargs: Additional parameters

        Returns:
            String containing the execution results
        """
        # Prepare the design generation prompt
        design_prompt = f"""User Requirement:
{request}

Please analyze the requirement and generate a complete structural design proposal.
If any critical information is missing, use the AskHuman tool to ask the user.

Remember to output ONLY a valid JSON object following the specified format."""

        # Call the parent run method (system_prompt is already set in __init__)
        result = await super().run(request=design_prompt, **kwargs)

        return result

    def extract_design_proposal(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract DesignProposal JSON from LLM response

        Args:
            response: LLM response text (may be wrapped in OpenManus execution logs)

        Returns:
            Parsed design proposal dict, or None if extraction fails
        """
        try:
            # Pattern 1: OpenManus execution log format
            # "Observed output of cmd `create_chat_completion` executed:\n{JSON}\nStep"
            match = re.search(r'create_chat_completion.*?executed:\s*(\{.*?\})\s*(?:Step|\Z)', response, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)

            # Pattern 2: ```json ... ```
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)

            # Pattern 3: ``` ... ```
            json_match = re.search(r'```\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)

            # Pattern 4: Direct JSON object
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
