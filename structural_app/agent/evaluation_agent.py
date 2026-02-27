"""
Evaluation Agent for OpenManus
Performs comprehensive design evaluation
"""

from typing import Dict, Any, Optional, List
import json

from app.agent.toolcall import ToolCallAgent
from app.tool.ask_human import AskHuman
from app.schema import Message
from app.tool import ToolCollection, CreateChatCompletion, Terminate

# Import EvaluationTool with path handling
import importlib.util
import os

# Add structural_app to path if needed
_structural_app_path = r'D:\structural-design-system\structural_app'
if _structural_app_path not in __import__('sys').path:
    __import__('sys').path.insert(0, _structural_app_path)

# Load EvaluationTool module directly
_evaluation_tool_path = os.path.join(_structural_app_path, 'tool', 'evaluation_tool.py')
_spec = importlib.util.spec_from_file_location("evaluation_tool", _evaluation_tool_path)
evaluation_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evaluation_module)
EvaluationTool = evaluation_module.EvaluationTool

# Get EvaluatorFactory from already-loaded EvaluationTool module
EvaluatorFactory = evaluation_module.EvaluatorFactory


class EvaluationAgent(ToolCallAgent):
    """
    Agent responsible for performing comprehensive design evaluation.

    This agent:
    1. Receives DesignProposal and AnalysisResults (from context)
    2. Calls EvaluationTool for 4-dimensional quantitative evaluation
    3. Returns EvaluationReport in JSON format with:
       - Comprehensive score (0-100)
       - Letter grade (A+/A/B+/B/C+/C/D)
       - 4 dimension scores (economy, efficiency, safety, sustainability)
       - Recommendations (if score < 75)

    Key Features:
    - Generic: handles all structure types (beam, frame, truss, etc.)
    - Uses EvaluationTool with factory pattern routing
    - Standardized input/output via EvaluationReport
    - No loop mode needed - evaluation is a single assessment
    """

    def __init__(
        self,
        name: str = "EvaluationAgent",
        description: str = None,
        tools: Optional[List] = None,
        **kwargs
    ):
        """
        Initialize the Evaluation Agent

        Args:
            name: Agent name (default: "EvaluationAgent")
            description: Agent description
            tools: List of tools available to the agent
            **kwargs: Additional arguments passed to ToolCallAgent
        """
        if description is None:
            description = (
                "I am an evaluation agent. I perform comprehensive design evaluation "
                "including economic, efficiency, safety, and sustainability dimensions. "
                "I receive design proposal and analysis results as input and return "
                "a quantitative evaluation report with comprehensive score and grade."
            )

        # Initialize with EvaluationTool and AskHuman if not provided
        if tools is None:
            tools = [EvaluationTool(), AskHuman()]
        else:
            # Add EvaluationTool if not present
            has_evaluation = any(isinstance(tool, EvaluationTool) for tool in tools)
            if not has_evaluation:
                tools.append(EvaluationTool())

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

        # Set system prompt for evaluation
        object.__setattr__(self, 'system_prompt', self._create_evaluation_system_prompt())

    def _create_evaluation_system_prompt(self) -> str:
        """
        Create system prompt for design evaluation

        Returns:
            System prompt string
        """
        return """You are an expert design evaluation agent.

Your task is to perform comprehensive design evaluation using the evaluation tool.

INPUT FORMAT:
You will receive DesignProposal and AnalysisResults in the conversation history.

DesignProposal format:
{
  "type": "<structure_type>",  // "beam", "frame", "truss", etc.
  "units": "m" or "mm",
  "geometry": {
    "length": <number>,
    "width": <number>,
    "height": <number>,
    "n_elements": <integer>
  },
  "material": {
    "E": <number>,
    "nu": <number>,
    "fy": <number>
  },
  "loads": {
    "distributed": [{"q": <number>, "direction": "y"}],
    "point": [{"P": <number>, "location": <number>, "direction": "y"}]
  },
  "constraints": {
    "support_type": "<type>"
  }
}

AnalysisResults format:
{
  "status": "success",
  "results": {
    "max_displacement": <number>,
    "max_displacement_mm": <number>,
    "max_stress": <number>,
    "max_stress_MPa": <number>,
    "max_moment": <number>,
    "max_moment_kNm": <number>,
    "max_shear": <number>,
    "max_shear_kN": <number>,
    "detailed_results": {...}
  },
  "code_check": {
    "compliant": <boolean>,
    "violations": [...],
    "safety_factors": {
      "stress": <number>,
      "deflection": <number>
    }
  }
}

OUTPUT FORMAT:
You MUST use the evaluation tool to perform the evaluation.
The evaluation tool will return EvaluationReport in this format:
{
  "status": "success",
  "comprehensive_score": <number>,  // 0-100
  "grade": "<grade>",               // A+/A/B+/B/C+/C/D
  "dimensions": {
    "economy": {
      "score": <number>,
      "indicators": {...}
    },
    "structural_efficiency": {
      "score": <number>,
      "indicators": {...}
    },
    "safety": {
      "score": <number>,
      "indicators": {...}
    },
    "sustainability": {
      "score": <number>,
      "indicators": {...}
    }
  },
  "recommendations": [...]          // List of suggestions if score < 75
}

IMPORTANT:
- Always use the evaluation tool to perform the evaluation
- Pass the complete DesignProposal and AnalysisResults to the evaluation tool
- Return the EvaluationReport exactly as provided by the evaluation tool
- The comprehensive score determines the grade:
  * A+: >= 95, A: 90-94, B+: 85-89, B: 80-84
  * C+: 75-79, C: 70-74, D: < 70

EVALUATION WORKFLOW:
1. Extract DesignProposal and AnalysisResults from the input
2. Call the evaluation tool with the extracted data
3. Return the EvaluationReport to the user
"""

    async def run(self, request: str, **kwargs) -> str:
        """
        Main execution method for the agent.

        Args:
            request: User's request (typically contains DesignProposal and AnalysisResults)
            **kwargs: Additional parameters

        Returns:
            String containing the evaluation report
        """
        # Prepare the evaluation prompt
        evaluation_prompt = f"""{request}

Use the evaluation tool to perform the comprehensive design evaluation.
Return the complete EvaluationReport."""

        # Call the parent run method (system_prompt is already set in __init__)
        result = await super().run(request=evaluation_prompt, **kwargs)

        return result

    def extract_evaluation_report(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract EvaluationReport JSON from LLM response

        Args:
            response: LLM response text (may contain evaluation tool output)

        Returns:
            Parsed evaluation report dict, or None if extraction fails
        """
        try:
            import re
            import json

            # Pattern 1: Extract from evaluation tool output
            pattern = r'evaluation.*?executed:\s*(\{.*?\})\s*(?:Step|\Z)'
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
            print(f"Failed to parse evaluation report JSON: {e}")
            return None


# Register the agent for use in PlanningFlow
def create_evaluation_agent(**kwargs) -> EvaluationAgent:
    """
    Factory function to create EvaluationAgent instance

    Args:
        **kwargs: Arguments passed to EvaluationAgent constructor

    Returns:
        EvaluationAgent instance
    """
    return EvaluationAgent(**kwargs)
