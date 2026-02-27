"""
Report Generation Agent for OpenManus
Generates comprehensive design reports with visualizations
"""

from typing import Dict, Any, Optional, List
import json

from app.agent.toolcall import ToolCallAgent
from app.tool.ask_human import AskHuman
from app.schema import Message
from app.tool import ToolCollection, CreateChatCompletion, Terminate

# Import ReportGenerationTool with dynamic path detection
import importlib.util
import os
import sys

# Get the directory where this file is located
_current_dir = os.path.dirname(os.path.abspath(__file__))
_structural_app_path = os.path.dirname(_current_dir)

# Add structural_app to path if not already present
if _structural_app_path not in sys.path:
    sys.path.insert(0, _structural_app_path)

# Load ReportTool and VisualizationTool modules directly
_report_tool_path = os.path.join(_structural_app_path, 'tool', 'report_tool.py')
_visualization_tool_path = os.path.join(_structural_app_path, 'tool', 'visualization_tool.py')

# Import ReportTool
if os.path.exists(_report_tool_path):
    _report_spec = importlib.util.spec_from_file_location("report_tool", _report_tool_path)
    report_module = importlib.util.module_from_spec(_report_spec)
    _report_spec.loader.exec_module(report_module)
    ReportTool = report_module.ReportTool
else:
    from structural_app.tool.report_tool import ReportTool

# Import VisualizationTool
if os.path.exists(_visualization_tool_path):
    _viz_spec = importlib.util.spec_from_file_location("visualization_tool", _visualization_tool_path)
    viz_module = importlib.util.module_from_spec(_viz_spec)
    _viz_spec.loader.exec_module(viz_module)
    VisualizationTool = viz_module.VisualizationTool
else:
    from structural_app.tool.visualization_tool import VisualizationTool


class ReportGenerationAgent(ToolCallAgent):
    """
    Agent responsible for generating comprehensive design reports.

    This agent:
    1. Receives DesignProposal, AnalysisResults, EvaluationReport, DrawingResults (from context)
    2. Calls VisualizationTool to generate static and interactive visualizations
    3. Calls ReportTool to generate structured Markdown report
    4. Returns ReportResults in JSON format with:
       - Report file path
       - Visualization file paths (static PNG and interactive HTML)
       - Summary information

    Key Features:
    - Generic: handles all structure types (beam, frame, truss, etc.)
    - Uses VisualizationTool and ReportTool with factory pattern routing
    - Standardized input/output via ReportResults
    - Supports smart decision making (ask human if score < 75)
    """

    def __init__(
        self,
        name: str = "ReportGenerationAgent",
        description: str = None,
        tools: Optional[List] = None,
        **kwargs
    ):
        """
        Initialize the Report Generation Agent

        Args:
            name: Agent name (default: "ReportGenerationAgent")
            description: Agent description
            tools: List of tools available to the agent
            **kwargs: Additional arguments passed to ToolCallAgent
        """
        if description is None:
            description = (
                "I am a report generation agent. I generate comprehensive design reports "
                "including visualizations and structured documentation. "
                "I receive design proposal, analysis results, evaluation report, and drawing results "
                "as input and return a complete report package."
            )

        # Initialize with ReportTool, VisualizationTool, and AskHuman if not provided
        if tools is None:
            tools = [ReportTool(), VisualizationTool(), AskHuman()]
        else:
            # Add ReportTool if not present
            has_report = any(isinstance(tool, ReportTool) for tool in tools)
            if not has_report:
                tools.append(ReportTool())

            # Add VisualizationTool if not present
            has_visualization = any(isinstance(tool, VisualizationTool) for tool in tools)
            if not has_visualization:
                tools.append(VisualizationTool())

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

        # Set system prompt for report generation
        object.__setattr__(self, 'system_prompt', self._create_report_system_prompt())

    def _create_report_system_prompt(self) -> str:
        """
        Create system prompt for report generation

        Returns:
            System prompt string
        """
        return """You are an expert report generation agent.

Your task is to generate comprehensive design reports using the report and visualization tools.

INPUT FORMAT:
You will receive DesignProposal, AnalysisResults, EvaluationReport, and DrawingResults in the conversation history.

DesignProposal format:
{
  "type": "<structure_type>",
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
  "loads": {...},
  "constraints": {...}
}

AnalysisResults format:
{
  "status": "success",
  "results": {
    "max_displacement_mm": <number>,
    "max_stress_MPa": <number>,
    "max_moment_kNm": <number>,
    "max_shear_kN": <number>
  },
  "code_check": {
    "compliant": <boolean>,
    "safety_factors": {...}
  }
}

EvaluationReport format:
{
  "status": "success",
  "comprehensive_score": <number>,
  "grade": "<grade>",
  "dimensions": {...},
  "recommendations": [...]
}

DrawingResults format:
{
  "status": "success",
  "files": {...},
  "metadata": {...}
}

OUTPUT FORMAT:
You MUST use the tools to generate the report.

Step 1: Use visualization tool to generate visualizations
Step 2: Use report tool to generate the report
Step 3: Return ReportResults in this format:
{
  "status": "success",
  "report_file": "<path>",
  "visualizations": {
    "static": {
      "moment_diagram": "<path>",
      "shear_diagram": "<path>",
      "deflection_curve": "<path>"
    },
    "interactive": {
      "moment_html": "<path>",
      "shear_html": "<path>",
      "deflection_html": "<path>"
    }
  },
  "summary": {
    "structure_type": "<type>",
    "design_grade": "<grade>",
    "comprehensive_score": <number>,
    "code_compliant": <boolean>
  }
}

IMPORTANT:
- Always use the visualization tool first to generate plots
- Then use the report tool to generate the Markdown report
- Return the complete ReportResults with all file paths
- If evaluation score < 75, consider asking the user for design improvements

REPORT GENERATION WORKFLOW:
1. Extract DesignProposal, AnalysisResults, EvaluationReport, DrawingResults from the input
2. Call the visualization tool with the extracted data
3. Call the report tool with all results
4. Return the ReportResults to the user
"""

    async def run(self, request: str, **kwargs) -> str:
        """
        Main execution method for the agent.

        Args:
            request: User's request (typically contains all design results)
            **kwargs: Additional parameters

        Returns:
            String containing the report results
        """
        # Prepare the report generation prompt
        report_prompt = f"""{request}

Use the visualization tool to generate visualizations first,
then use the report tool to generate the comprehensive report.
Return the complete ReportResults."""

        # Call the parent run method (system_prompt is already set in __init__)
        result = await super().run(request=report_prompt, **kwargs)

        return result

    def _find_balanced_json(self, response: str) -> Optional[str]:
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

    def extract_report_results(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract ReportResults JSON from LLM response

        Args:
            response: LLM response text (may contain report tool output)

        Returns:
            Parsed report results dict, or None if extraction fails
        """
        try:
            import re
            import json

            # Pattern 1: Extract from report tool output
            # Find the JSON block after "report" tool execution
            pattern = r'report.*?executed:\s*(\{[\s\S]*?\n\})\s*(?:Step|\Z)'
            matches = re.findall(pattern, response)

            if matches:
                # Get the last match (most recent execution)
                json_str = matches[-1]
                return json.loads(json_str)

            # Pattern 2: Extract from code block
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)

            # Pattern 3: Direct JSON object with status field (fallback)
            # Find balanced JSON containing status
            balanced_json = self._find_balanced_json(response)
            if balanced_json:
                try:
                    return json.loads(balanced_json)
                except json.JSONDecodeError:
                    pass

            return None

        except json.JSONDecodeError as e:
            print(f"Failed to parse report results JSON: {e}")
            return None

    def extract_comprehensive_score(self, response: str) -> Optional[float]:
        """
        Extract comprehensive score from response for decision making

        Args:
            response: LLM response text

        Returns:
            Comprehensive score if found, None otherwise
        """
        report = self.extract_report_results(response)
        if report and 'summary' in report:
            return report['summary'].get('comprehensive_score')
        return None


# Register the agent for use in PlanningFlow
def create_report_generation_agent(**kwargs) -> ReportGenerationAgent:
    """
    Factory function to create ReportGenerationAgent instance

    Args:
        **kwargs: Arguments passed to ReportGenerationAgent constructor

    Returns:
        ReportGenerationAgent instance
    """
    return ReportGenerationAgent(**kwargs)
