"""
Structural Design Agent for OpenManus
Handles parameter collection and initial structural design
"""

from typing import Dict, Any, Optional, List
import json
import re

from app.agent.toolcall import ToolCallAgent
from app.tool.ask_human import AskHuman
from app.schema import Message
from app.tool import ToolCollection, CreateChatCompletion, Terminate

# Import validators directly to avoid full package import chain
import importlib.util
import os
import sys

# Get the directory where this file is located
_current_dir = os.path.dirname(os.path.abspath(__file__))
_structural_app_path = os.path.dirname(_current_dir)

# Build path to validators module
_validators_path = os.path.join(_structural_app_path, 'tool', 'validators', '__init__.py')

# Load validators module without triggering structural_app.tool.__init__
_spec = importlib.util.spec_from_file_location("validators", _validators_path)
validators_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validators_module)

ParameterValidator = validators_module.ParameterValidator
BeamValidator = validators_module.BeamValidator


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
        max_iterations: int = 3,
        **kwargs
    ):
        """
        Initialize the Structural Design Agent

        Args:
            name: Agent name (default: "StructuralDesignAgent")
            description: Agent description
            tools: List of tools available to the agent
            max_iterations: Maximum number of validation iterations
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

        # Override available_tools to include all tools including AskHuman
        # ToolCallAgent uses available_tools (not tools) for LLM tool options
        # Combine user-provided tools with default tools
        all_tools = tools + [CreateChatCompletion(), Terminate()]
        self.available_tools = ToolCollection(*all_tools)

        # Set system prompt for design generation
        self.system_prompt = self._create_design_system_prompt()

        # Validator mapping by structure type
        self._validator_map = {
            'beam': BeamValidator(),
            # Add more validators here as needed:
            # 'frame': FrameValidator(),
            # 'truss': TrussValidator(),
        }

        # Maximum iterations for validation loop
        self.max_iterations = max_iterations

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
  "type": "<structure_type>",  // REQUIRED: "beam", "cantilever_beam", "continuous_beam", "frame", "truss", etc.
  "units": "<units>",          // REQUIRED: "m" or "mm" (specifies units for geometry)
  "geometry": {
    "length": <number>,        // in specified units (m or mm)
    "width": <number>,         // in specified units (for cross-section)
    "height": <number>,        // in specified units (for cross-section)
    "n_elements": <integer>,   // number of finite elements (default: 20)
    "n_spans": <integer>       // ONLY for continuous_beam: number of spans (2-5)
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
        "location": <number>,  // Position along beam in same units as geometry
        "direction": "y"       // "x" or "y"
      }
    ]
  },
  "constraints": {
    "support_type": "<type>"   // "simply_supported", "cantilever", "fixed_fixed", "continuous"
  }
}

STRUCTURE TYPE SELECTION:
=========================
Choose the correct "type" based on the user's description:

1. "beam" - Simply supported beam (简支梁)
   - Single span with two supports (pinned + roller)
   - Use when user says: "简支梁", "单跨梁", "simple beam"

2. "cantilever_beam" - Cantilever beam (悬臂梁)
   - Fixed at one end, free at the other
   - Use when user says: "悬臂梁", "cantilever", "固定一端"

3. "continuous_beam" - Continuous beam (连续梁)
   - Multiple spans with intermediate supports
   - MUST include "n_spans" in geometry (2-5 spans)
   - "length" is TOTAL length across all spans
   - Use when user says: "连续梁", "多跨梁", "两跨", "三跨", "continuous beam"
   - Example: "两跨连续梁，跨度12m" means n_spans=2, length=24m (total)

4. "truss" - Truss structure (桁架)
   - Use when user says: "桁架", "truss"

5. "frame" - Frame structure (框架)
   - Use when user says: "框架", "frame", "刚架"

CRITICAL: For continuous beams:
- Set type to "continuous_beam" (NOT "beam")
- Add "n_spans" to geometry
- "length" is the TOTAL length (sum of all spans)
- Example: 两跨连续梁，每跨6m → type="continuous_beam", n_spans=2, length=12.0

UNITS GUIDELINES:
- Use "m" for meters (default for most structural engineering calculations)
- Use "mm" for millimeters (common in CAD drawings)
- ALL geometry dimensions must use the same units specified in the "units" field
- Load values have fixed units: q in N/m, P in N (independent of geometry units)

DESIGN GUIDELINES:
1. For simply supported beams (type="beam"):
   - Typical span-to-depth ratio: L/10 to L/15
   - Width typically 0.3-0.5m for concrete beams
   - Use C30 concrete (E=30GPa) or Q235 steel (E=200GPa) as defaults

2. For cantilever beams (type="cantilever_beam"):
   - More conservative span-to-depth ratio: L/6 to L/10
   - Larger sections needed due to higher moments
   - Fixed support at one end

3. For continuous beams (type="continuous_beam"):
   - Can use more slender sections: L/12 to L/20
   - MUST specify n_spans (2-5)
   - Total length = n_spans × span_length
   - More economical than simply supported beams
   - Example: "两跨连续梁12m" → n_spans=2, length=12.0 (if 12m is total)
   - Example: "两跨连续梁每跨6m" → n_spans=2, length=12.0 (6m × 2)

4. For loads:
   - Residential: 2-3 kN/m² live load
   - Office: 3-4 kN/m² live load
   - Convert area loads to line loads based on tributary width

5. Material selection:
   - Concrete: E=30e9 Pa, nu=0.2, fy=14.3e6 Pa (C30)
   - Steel: E=200e9 Pa, nu=0.3, fy=235e6 Pa (Q235)

6. Always include the "type" field - this is CRITICAL for routing to the correct analyzer.

7. For continuous beams, ALWAYS include "n_spans" in geometry.

CRITICAL: UNITS FIELD IS MANDATORY:
====================================
You MUST always include the "units" field in your JSON output. This is REQUIRED.
- If geometry values are in meters, set "units": "m"
- If geometry values are in millimeters, set "units": "mm"
- ALL geometry dimensions (length, width, height) must use the same units

Example 1 (using meters):
{
  "type": "beam",
  "units": "m",
  "geometry": {"length": 6.0, "width": 0.3, "height": 0.6},
  ...
}

Example 2 (using millimeters):
{
  "type": "beam",
  "units": "mm",
  "geometry": {"length": 6000, "width": 300, "height": 600},
  ...
}

Example 3 (continuous beam with 2 spans):
{
  "type": "continuous_beam",
  "units": "m",
  "geometry": {
    "length": 12.0,
    "width": 0.3,
    "height": 0.6,
    "n_elements": 40,
    "n_spans": 2
  },
  "material": {
    "E": 30e9,
    "nu": 0.2,
    "fy": 14.3e6,
    "material_name": "C30"
  },
  "loads": {
    "distributed": [{"q": -10000, "direction": "y"}],
    "point": []
  },
  "constraints": {
    "support_type": "continuous"
  }
}

Example 4 (cantilever beam):
{
  "type": "cantilever_beam",
  "units": "m",
  "geometry": {"length": 3.0, "width": 0.3, "height": 0.5},
  "constraints": {"support_type": "cantilever"},
  ...
}

CRITICAL RULES FOR PARAMETER COLLECTION:
=========================================

[HOW TO HANDLE MISSING PARAMETERS]
When the user's request is missing critical information, you MUST use the AskHuman tool.

What constitutes "critical information" depends on the structure type:
- For beams: span/length, loads, and support type are ALWAYS required
- For other structures: critical parameters may vary

[WHEN TO USE AskHuman TOOL]
Use the ask_human tool when:
1. User request doesn't specify critical design parameters
2. User request is ambiguous about loads (e.g., "承受荷载" but no magnitude)
3. User request doesn't specify support conditions
4. You cannot make reasonable engineering assumptions without user input

[HOW TO USE AskHuman TOOL]
Call the ask_human tool with a clear, specific inquiry that asks for the missing information.
The tool will display your question to the user and return their response.

Example inquiry for a beam without span:
"请补充以下信息：1. 跨度（长度）是多少米？2. 荷载是多少？3. 支座类型是什么？"

OUTPUT FORMAT:
IMPORTANT: You MUST use the create_chat_completion tool to return your final answer.
The JSON should be returned as the content of the create_chat_completion tool.
- If you have all required information: Use create_chat_completion to return a valid JSON object.
- If you need more information: Use the ask_human tool FIRST.

CRITICAL: Do NOT use the terminate tool. Always use create_chat_completion to return your final answer.
"""

    async def run(self, request: str, **kwargs) -> str:
        """
        Main execution method for the agent.

        The agent uses OpenManus's ReAct loop to:
        1. Analyze user requirements
        2. Call AskHuman tool if parameters are missing
        3. Generate design proposal with valid JSON

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
Follow the rules in the system prompt for determining which parameters must be asked.

Remember to output ONLY a valid JSON object following the specified format."""

        # Call the parent run method (system_prompt is already set in __init__)
        # The parent class handles the ReAct loop with AskHuman tool
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
            import re
            import json

            # Pattern 1: ```json ... ``` 代码块格式（优先处理）
            # 匹配从 ```json 开始到 ``` 结束之间的所有内容
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
                # 检查是否以换行+}结尾
                if json_str.endswith('\n}'):
                    return json.loads(json_str)

            # Pattern 2: OpenManus execution log format with create_chat_completion
            # "Observed output of cmd `create_chat_completion` executed:\n{JSON}\nStep"
            match = re.search(r'create_chat_completion.*?executed:[\s\S]*?(\{[\s\S]*?\n\})\s*(?:Step|\Z)', response, re.DOTALL)
            if match:
                json_str = match.group(1)
                # 检查是否是完整的 JSON（排除带省略号的情况）
                if '...' not in json_str:
                    return json.loads(json_str)

            # Pattern 3: ``` ... ``` 普通代码块
            json_match = re.search(r'```\s*([\s\S]*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
                if json_str.endswith('\n}'):
                    return json.loads(json_str)

            # Pattern 4: Direct JSON object - 匹配包含 type 字段的 JSON 对象
            json_match = re.search(r'(\{[\s\S]*?"type":[\s\S]*?\n\})\s*(?:,|\n|\Z)', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
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

        # Validate units field (MANDATORY)
        if 'units' not in proposal:
            return False, "Missing required 'units' field. You MUST specify 'units': 'm' or 'units': 'mm'"

        if proposal['units'] not in ['m', 'mm']:
            return False, "Invalid 'units' value. Must be 'm' (meters) or 'mm' (millimeters)"

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
