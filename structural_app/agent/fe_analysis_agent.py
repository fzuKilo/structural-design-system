"""
FE Analysis Agent for OpenManus
Performs finite element analysis on structural designs
"""

from typing import Dict, Any, Optional, List
import json

from app.agent.toolcall import ToolCallAgent
from app.tool.ask_human import AskHuman
from app.schema import Message
from app.tool import ToolCollection, CreateChatCompletion, Terminate

# Import FEAnalysisTool with path handling
import importlib.util
import os

# Add structural_app to path if needed
_structural_app_path = r'D:\structural-design-system\structural_app'
if _structural_app_path not in __import__('sys').path:
    __import__('sys').path.insert(0, _structural_app_path)

# Load FEAnalysisTool module directly
_fe_tool_path = os.path.join(_structural_app_path, 'tool', 'fe_analysis_tool.py')
_spec = importlib.util.spec_from_file_location("fe_analysis_tool", _fe_tool_path)
fe_analysis_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fe_analysis_module)
FEAnalysisTool = fe_analysis_module.FEAnalysisTool


class FEAnalysisAgent(ToolCallAgent):
    """
    Agent responsible for performing finite element analysis on structural designs.

    This agent:
    1. Receives a DesignProposal (from context or user input)
    2. Calls FEAnalysisTool to perform FE analysis
    3. Returns AnalysisResults in JSON format

    Key Features:
    - Generic: handles all structure types (beam, frame, truss, etc.)
    - Uses FEAnalysisTool with factory pattern routing
    - Standardized input/output via DesignProposal/AnalysisResults
    """

    def __init__(
        self,
        name: str = "FEAnalysisAgent",
        description: str = None,
        tools: Optional[List] = None,
        **kwargs
    ):
        """
        Initialize the FE Analysis Agent

        Args:
            name: Agent name (default: "FEAnalysisAgent")
            description: Agent description
            tools: List of tools available to the agent
            **kwargs: Additional arguments passed to ToolCallAgent
        """
        if description is None:
            description = (
                "I am an FE analysis agent. I perform finite element analysis on structural designs. "
                "I receive a structural design proposal as input and return comprehensive analysis "
                "results including displacement, stress, moment, shear forces, and code compliance checks."
            )

        # Initialize with FEAnalysisTool and AskHuman if not provided
        if tools is None:
            tools = [FEAnalysisTool(), AskHuman()]
        else:
            # Add FEAnalysisTool if not present
            has_fe_analysis = any(isinstance(tool, FEAnalysisTool) for tool in tools)
            if not has_fe_analysis:
                tools.append(FEAnalysisTool())

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
        self.available_tools = ToolCollection(*all_tools)

        # Set system prompt for FE analysis
        self.system_prompt = self._create_fe_analysis_system_prompt()

    def _create_fe_analysis_system_prompt(self) -> str:
        """
        Create system prompt for FE analysis

        Returns:
            System prompt string
        """
        return """You are an expert finite element analysis agent.

Your task is to perform finite element analysis on structural designs.

INPUT FORMAT:
You will receive a DesignProposal in JSON format with the following structure:
{
  "type": "<structure_type>",  // "beam", "frame", "truss", etc.
  "geometry": {
    "length": <number>,        // in meters
    "width": <number>,         // in meters
    "height": <number>,        // in meters
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
You MUST use the fe_analysis tool to perform the analysis.
The fe_analysis tool will return AnalysisResults in this format:
{
  "status": "success",
  "results": {
    "max_displacement": <number>,      // in meters
    "max_displacement_mm": <number>,   // in millimeters
    "max_stress": <number>,            // in Pa
    "max_stress_MPa": <number>,        // in MPa
    "max_moment": <number>,            // in N*m
    "max_moment_kNm": <number>,        // in kN*m
    "max_shear": <number>,             // in N
    "max_shear_kN": <number>,          // in kN
    "detailed_results": {...}          // Full analysis results
  },
  "code_check": {
    "compliant": <boolean>,
    "violations": [...],
    "safety_factors": {...}
  }
}

IMPORTANT:
- Always use the fe_analysis tool to perform the analysis
- Do not try to calculate results manually
- Pass the complete DesignProposal to the fe_analysis tool
- Return the AnalysisResults exactly as provided by the fe_analysis tool

ANALYSIS WORKFLOW:
1. Extract the DesignProposal from the input
2. Call the fe_analysis tool with the DesignProposal
3. Return the AnalysisResults to the user
"""

    async def run(self, request: str, **kwargs) -> str:
        """
        Main execution method for the agent.

        Args:
            request: User's request (typically contains a DesignProposal)
            **kwargs: Additional parameters

        Returns:
            String containing the analysis results
        """
        # Prepare the analysis prompt
        analysis_prompt = f"""Analyze the following structural design:

{request}

Use the fe_analysis tool to perform the finite element analysis.
Return the complete AnalysisResults."""

        # Call the parent run method (system_prompt is already set in __init__)
        result = await super().run(request=analysis_prompt, **kwargs)

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
            match = __import__('re').search(r'create_chat_completion.*?executed:\s*(\{.*?\})\s*(?:Step|\Z)', response, __import__('re').DOTALL)
            if match:
                json_str = match.group(1)
                return __import__('json').loads(json_str)

            # Pattern 2: ```json ... ```
            json_match = __import__('re').search(r'```json\s*(\{.*?\})\s*```', response, __import__('re').DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return __import__('json').loads(json_str)

            # Pattern 3: ``` ... ```
            json_match = __import__('re').search(r'```\s*(\{.*?\})\s*```', response, __import__('re').DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return __import__('json').loads(json_str)

            # Pattern 4: Direct JSON object
            json_match = __import__('re').search(r'\{.*?\}', response, __import__('re').DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return __import__('json').loads(json_str)

            return None

        except __import__('json').JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            return None

    def extract_analysis_results(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract AnalysisResults JSON from LLM response

        Args:
            response: LLM response text (may contain fe_analysis tool output)

        Returns:
            Parsed analysis results dict, or None if extraction fails
        """
        try:
            re = __import__('re')
            json = __import__('json')

            # Pattern 1: Extract from fe_analysis tool output
            # Match the JSON object after "fe_analysis ... executed:"
            # Use a greedy approach to match everything until "Step" or end of string
            pattern = r'fe_analysis.*?executed:\s*(\{.*?\})\s*(?:Step|\Z)'
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
            # Match JSON objects containing "status"
            matches = re.findall(r'\{[^}]*"status"[^}]*\}', response, re.DOTALL)
            if matches:
                json_str = matches[-1]  # Get last match
                return json.loads(json_str)

            return None

        except json.JSONDecodeError as e:
            print(f"Failed to parse analysis results JSON: {e}")
            return None


# Register the agent for use in PlanningFlow
def create_fe_analysis_agent(**kwargs) -> FEAnalysisAgent:
    """
    Factory function to create FEAnalysisAgent instance

    Args:
        **kwargs: Arguments passed to FEAnalysisAgent constructor

    Returns:
        FEAnalysisAgent instance
    """
    return FEAnalysisAgent(**kwargs)
