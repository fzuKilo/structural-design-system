"""
Report Generation Agent for OpenManus
Generates comprehensive design reports with visualizations
"""

from typing import Dict, Any, Optional, List
import json
import json

from app.agent.toolcall import ToolCallAgent
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

        # Initialize with ReportTool and VisualizationTool if not provided
        # 移除 AskHuman：ReportGenerationAgent 应该直接从上下文提取数据，不需要询问用户
        if tools is None:
            tools = [ReportTool(), VisualizationTool()]
        else:
            # Add ReportTool if not present
            has_report = any(isinstance(tool, ReportTool) for tool in tools)
            if not has_report:
                tools.append(ReportTool())

            # Add VisualizationTool if not present
            has_visualization = any(isinstance(tool, VisualizationTool) for tool in tools)
            if not has_visualization:
                tools.append(VisualizationTool())

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
You will receive DesignProposal, AnalysisResults, EvaluationReport, DrawingResults, and optionally BimResults and IfcResults in the conversation history.

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

BimResults format (optional):
{
  "status": "success",
  "url": "<speckle_url>",
  "model_id": "<model_id>"
}

IfcResults format (optional):
{
  "status": "success",
  "path": "<ifc_file_path>"
}

OUTPUT FORMAT:
You MUST use the tools to generate the report.

CRITICAL WORKFLOW:
Step 1: ALWAYS call visualization tool first to generate NEW visualizations
        - NEVER skip this step
        - NEVER assume visualizations already exist
        - ALWAYS generate fresh visualizations for each report
        - Pass design_proposal and analysis_results to the tool
Step 2: Call report tool to generate the comprehensive Markdown report
        - Serialize ALL data into a single JSON string and pass as report_data:
          report(report_data=<json_string>)
        - The json_string must contain: design_proposal, analysis_results, evaluation_report,
          drawing_results, and optionally bim_results, ifc_results
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
- MUST call the visualization tool first to generate NEW plots before calling report tool
- MUST call the report tool to generate the Markdown report
- MUST return the complete ReportResults with all file paths for both visualizations and report
- NEVER call ask_human - always extract data from the conversation history
- If visualization tool is not called, the report will be incomplete
- If required data is missing or invalid, return an error ReportResults
- DO NOT use old visualization files - always generate new ones

INPUT STRUCTURE:
The input request is a JSON object containing:
- "design_proposal": The design proposal object
- "analysis_results": The analysis results object
- "evaluation_report": The evaluation report object
- "drawing_results": The drawing results object
- "bim_results": The BIM export results (optional, may be null)
- "ifc_results": The IFC export results (optional, may be null)

EXAMPLE CALL:
If the input is:
{"design_proposal": {...}, "analysis_results": {...}, "evaluation_report": {...}, "drawing_results": {...}}

Then call:
visualization(design_proposal=..., analysis_results=...)
report(report_data='{"design_proposal":..., "analysis_results":..., "evaluation_report":..., "drawing_results":...}')

REPORT GENERATION WORKFLOW:
1. Read the input request - it is a JSON object with design_proposal, analysis_results, evaluation_report, drawing_results
2. Extract all four objects from the JSON
3. CRITICAL: Call the visualization tool with design_proposal and analysis_results to generate NEW visualizations
4. Call the report tool with all four objects
5. Return the ReportResults to the user
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
        # First, call visualization tool to generate visualizations
        # Skip if report_only mode is enabled
        visualization_output = None
        visualization_success = False
        visualization_error = None

        try:
            import re
            import json

            # Extract design_proposal and analysis_results from request
            design_proposal = None
            analysis_results = None
            skip_visualization = False

            # Try to extract from JSON
            try:
                request_obj = json.loads(request)
                design_proposal = request_obj.get('design_proposal')
                # Prefer full arrays for visualization; fall back to stripped version
                analysis_results = (request_obj.get('analysis_results_full')
                                    or request_obj.get('analysis_results'))
                skip_visualization = request_obj.get('skip_visualization', False)
            except json.JSONDecodeError:
                pass

            # Check if we should skip visualization (report_only mode)
            if skip_visualization:
                print("[ReportGenerationAgent] Skipping visualization (report_only mode)")
                visualization_error = "Skipped in report_only mode"
            elif design_proposal and analysis_results:
                viz_tool = next((t for t in self.available_tools.tool_map.values()
                               if hasattr(t, '__class__') and 'visualization' in t.__class__.__name__.lower()), None)
                if viz_tool:
                    try:
                        print(f"[ReportGenerationAgent] Pre-executing visualization tool...")
                        viz_result = await viz_tool.execute(design_proposal=design_proposal,
                                                           analysis_results=analysis_results)
                        visualization_output = str(viz_result)
                        visualization_success = True
                        print(f"[ReportGenerationAgent] Visualization tool pre-execution SUCCESS")
                    except Exception as e:
                        visualization_error = str(e)
                        print(f"[ReportGenerationAgent] Visualization tool pre-execution FAILED: {e}")
                else:
                    visualization_error = "Visualization tool not found"
                    print(f"[ReportGenerationAgent] Visualization tool not found in available tools")
            else:
                visualization_error = "Missing design_proposal or analysis_results"
                print(f"[ReportGenerationAgent] Cannot pre-execute visualization: missing data")
        except Exception as e:
            visualization_error = str(e)
            print(f"[ReportGenerationAgent] Visualization pre-execution exception: {e}")

        # Prepare the report generation prompt with clear instructions
        # Include visualization output if available
        if skip_visualization:
            report_prompt = f"""{request}

REPORT_ONLY MODE: Visualization generation is DISABLED.

IMPORTANT: The input is a JSON object with keys: design_proposal, analysis_results, evaluation_report, drawing_results.

CRITICAL STEPS:
Step 1: SKIP visualization tool (report_only mode)
Step 2: Call report tool EXACTLY like this:
  report(report_data='{{"design_proposal":<obj>, "analysis_results":<obj>, "evaluation_report":<obj>, "drawing_results":<obj>, "bim_results":<obj_or_null>, "ifc_results":<obj_or_null>}}')
  Serialize the entire dict to a JSON string and pass as report_data.
Step 3: Return the ReportResults (without visualization files)

DO NOT call the visualization tool in report_only mode.
"""
        elif visualization_success and visualization_output:
            report_prompt = f"""{request}

VISUALIZATION RESULTS (already generated by pre-execution):
{visualization_output}

IMPORTANT: The input is a JSON object with keys: design_proposal, analysis_results, evaluation_report, drawing_results.
Extract each object from the JSON and pass them to the report tool.

Step 1: Visualizations have been generated successfully (see above). DO NOT call visualization tool again.
Step 2: Call report tool EXACTLY like this:
  report(report_data='{{"design_proposal":<obj>, "analysis_results":<obj>, "evaluation_report":<obj>, "drawing_results":<obj>, "bim_results":<obj_or_null>, "ifc_results":<obj_or_null>}}')
  Serialize all data to a single JSON string and pass as report_data.
Step 3: Return the complete ReportResults with both visualization and report file paths.
"""
        elif visualization_error:
            report_prompt = f"""{request}

WARNING: Visualization pre-execution FAILED with error: {visualization_error}

IMPORTANT: The input is a JSON object with keys: design_proposal, analysis_results, evaluation_report, drawing_results.

CRITICAL RECOVERY STEPS:
Step 1: Call visualization tool with design_proposal and analysis_results to generate NEW visualizations.
Step 2: Call report tool EXACTLY like this:
  report(report_data='{{"design_proposal":<obj>, "analysis_results":<obj>, "evaluation_report":<obj>, "drawing_results":<obj>, "bim_results":<obj_or_null>, "ifc_results":<obj_or_null>}}')
  Serialize all data to a single JSON string and pass as report_data.
Step 3: Return the complete ReportResults with both visualization and report file paths.

CRITICAL: You MUST call both the visualization tool and the report tool. Do not skip either step.
"""
        else:
            report_prompt = f"""{request}

IMPORTANT: The input is a JSON object with keys: design_proposal, analysis_results, evaluation_report, drawing_results.
Extract each object from the JSON and pass them to the visualization and report tools.

CRITICAL STEPS:
Step 1: You MUST call visualization tool with design_proposal and analysis_results to generate NEW visualizations
        - Do NOT use old visualization files
        - Always generate fresh visualizations for each test run
Step 2: MUST call report tool with design_proposal, analysis_results, evaluation_report, and drawing_results
Step 3: Return the complete ReportResults with both visualization and report file paths

CRITICAL: You MUST call both the visualization tool and the report tool. Do not skip either step.
"""

        # Call the parent run method (system_prompt is already set in __init__)
        result = await super().run(request=report_prompt, **kwargs)

        return result

    def _extract_json_by_pattern(self, response: str, field_pattern: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON object containing a specific field pattern

        Args:
            response: Response string to search in
            field_pattern: Field pattern to look for (e.g., '"type"', '"status"')

        Returns:
            Extracted JSON dict, or None if not found
        """
        try:
            import re

            # Find balanced JSON containing the pattern
            i = 0
            while i < len(response):
                if response[i] == '{':
                    brace_count = 0
                    start = i
                    for j in range(i, len(response)):
                        if response[j] == '{':
                            brace_count += 1
                        elif response[j] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = response[start:j+1]
                                if field_pattern and field_pattern in json_str:
                                    try:
                                        return json.loads(json_str)
                                    except json.JSONDecodeError:
                                        pass
                                break
                    i = j + 1
                else:
                    i += 1
            return None
        except Exception:
            return None

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
            response: LLM response text (may contain visualization and report tool outputs)

        Returns:
            Parsed report results dict, or None if extraction fails
        """
        try:
            import re
            import json

            # Extract visualization results (static and interactive files)
            visualization_results = self._extract_visualization_results(response)

            # Extract report results (report file path)
            report_results = self._extract_report_file_results(response)

            # If no results found, return None
            if not report_results and not visualization_results:
                return None

            # Build combined ReportResults
            # visualization_results is already the visualizations object (static/interactive),
            # not wrapped in another 'visualizations' key
            combined_results = {
                'status': 'success',
                'report_file': report_results.get('report_file') if report_results else None,
                'visualizations': visualization_results if visualization_results else {},
                'summary': {}
            }

            # Add summary information from report_results if available
            if report_results:
                # Try to extract summary-like information
                if 'report_file' in report_results:
                    # The report file path is available
                    combined_results['report_file'] = report_results['report_file']

            return combined_results

        except json.JSONDecodeError as e:
            print(f"Failed to parse report results JSON: {e}")
            return None

    def _extract_visualization_results(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract visualization results from LLM response or from output directory

        Args:
            response: LLM response text

        Returns:
            Visualization results dict with static and interactive file paths
        """
        try:
            import re
            import json
            import os

            # Pattern 1: Extract from visualization tool output
            pattern = r'visualization.*?executed:\s*(\{[\s\S]*?\})\s*(?:Step|\Z)'
            matches = re.findall(pattern, response, re.DOTALL)

            if matches:
                json_str = matches[-1]
                result = json.loads(json_str)
                # Return the visualizations object if it exists
                return result.get('visualizations', result)

            # Pattern 2: Extract from code block
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
                return result.get('visualizations', result)

            # No visualization results found - this is an error condition
            print(f"[ReportGenerationAgent] ERROR: No visualization results found in response")
            print(f"[ReportGenerationAgent] This indicates the visualization tool was not called or failed")
            return None

        except Exception as e:
            print(f"[ReportGenerationAgent] ERROR: Failed to extract visualization results: {e}")
            return None

    def _extract_report_file_results(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract report file results from LLM response

        Args:
            response: LLM response text

        Returns:
            Report results dict with report_file path
        """
        try:
            import re
            import json

            # Pattern 1: Extract from report tool output
            pattern = r'report.*?executed:\s*(\{[\s\S]*?\})\s*(?:Step|\Z)'
            matches = re.findall(pattern, response, re.DOTALL)

            if matches:
                json_str = matches[-1]
                return json.loads(json_str)

            # Pattern 2: Extract from code block
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)

            return None

        except Exception:
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
