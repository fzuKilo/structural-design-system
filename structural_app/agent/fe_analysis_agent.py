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

# Get AnalyzerFactory from already-loaded FEAnalysisTool module
# FEAnalysisTool already imports AnalyzerFactory, so we can access it from there
AnalyzerFactory = fe_analysis_module.AnalyzerFactory


class FEAnalysisAgent(ToolCallAgent):
    """
    Agent responsible for performing finite element analysis on structural designs.

    This agent:
    1. Receives a DesignProposal (from context or user input)
    2. Calls FEAnalysisTool to perform FE analysis
    3. Returns AnalysisResults in JSON format
    4. Supports loop mode: when code_check fails, automatically ask user for improvements
       and re-analyze until compliant or user cancels

    Key Features:
    - Generic: handles all structure types (beam, frame, truss, etc.)
    - Uses FEAnalysisTool with factory pattern routing
    - Standardized input/output via DesignProposal/AnalysisResults
    - Loop mode: automatic improvement cycle with AskHuman
    """

    def __init__(
        self,
        name: str = "FEAnalysisAgent",
        description: str = None,
        tools: Optional[List] = None,
        enable_loop: bool = False,
        max_loop_count: int = 3,
        **kwargs
    ):
        """
        Initialize the FE Analysis Agent

        Args:
            name: Agent name (default: "FEAnalysisAgent")
            description: Agent description
            tools: List of tools available to the agent
            enable_loop: If True, automatically enter improvement loop when code_check fails
            max_loop_count: Maximum number of improvement cycles
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

        # Set custom attributes AFTER super().__init__() to avoid Pydantic conflict
        object.__setattr__(self, 'enable_loop', enable_loop)
        object.__setattr__(self, 'max_loop_count', max_loop_count)

        # Override available_tools to include all tools
        all_tools = tools + [CreateChatCompletion(), Terminate()]
        object.__setattr__(self, 'available_tools', ToolCollection(*all_tools))

        # Set system prompt for FE analysis
        object.__setattr__(self, 'system_prompt', self._create_fe_analysis_system_prompt())

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

        Supports two modes:
        1. Normal mode: Analyze once and return results
        2. Loop mode: When code_check fails, automatically ask user for improvements
           and re-analyze until compliant or max_loop_count reached

        Args:
            request: User's request (typically contains a DesignProposal)
            **kwargs: Additional parameters (loop_request: str for re-analysis with improvements)

        Returns:
            String containing the analysis results
        """
        # Check if this is a re-analysis request with improvements
        loop_request = kwargs.get('loop_request')
        if loop_request:
            # Append user's improvements to the request
            request = f"""{request}

USER IMPROVEMENTS:
{loop_request}

Please update the design based on these improvements and re-analyze."""

        # 新增：在分析前先检查设计类型是否支持
        # 从 request 中提取 DesignProposal
        design_proposal = self.extract_design_proposal(request)
        if design_proposal:
            structure_type = design_proposal.get('type')
            if structure_type and not AnalyzerFactory.is_registered(structure_type):
                available_types = AnalyzerFactory.get_available_types()
                error_result = {
                    'status': 'error',
                    'error': f"当前未支持的结构类型: '{structure_type}'。\n可用类型: {available_types}\n请使用已支持的类型，或参考 docs/how_to_add_new_structure_type.md 添加新类型支持。"
                }
                # 直接返回错误结果，不进入分析流程
                import json as json_module
                return f"""FEAnalysisTool 执行失败：
{json_module.dumps(error_result, ensure_ascii=False)}
"""

        # Prepare the analysis prompt
        # Use the request directly as the analysis prompt to avoid nested instructions
        analysis_prompt = f"""{request}

Use the fe_analysis tool to perform the finite element analysis.
Return the complete AnalysisResults."""

        # Remove loop_request and _loop_count from kwargs before passing to parent
        parent_kwargs = {k: v for k, v in kwargs.items() if k not in ('loop_request', '_loop_count')}

        # Call the parent run method (system_prompt is already set in __init__)
        result = await super().run(request=analysis_prompt, **parent_kwargs)

        # Extract analysis results to check code compliance
        analysis_results = self.extract_analysis_results(result)

        if analysis_results is not None:
            status = analysis_results.get('status')
            code_check = analysis_results.get('code_check', {})

            # If analysis failed (e.g., unsupported structure type), do not enter loop
            if status == 'error':
                return result

            # If loop mode is enabled and code check fails, enter improvement cycle
            if self.enable_loop and not code_check.get('compliant', False):
                # Get start_loop_count from kwargs for recursive calls
                start_loop_count = kwargs.get('_loop_count', 0)
                result = await self._enter_improvement_loop(request, result, analysis_results, start_loop_count)

        return result

    async def _enter_improvement_loop(
        self,
        original_request: str,
        initial_result: str,
        analysis_results: Dict[str, Any],
        start_loop_count: int = 0
    ) -> str:
        """
        Enter improvement loop when code_check fails.
        Ask user for improvements and re-analyze until compliant or max_loop_count reached.

        Args:
            original_request: Original analysis request
            initial_result: Initial analysis result string (for appending loop summaries)
            analysis_results: Results from initial analysis
            start_loop_count: Starting loop count (for recursive calls)

        Returns:
            Final analysis results (either compliant or after max loops)
        """
        loop_count = start_loop_count
        current_request = original_request
        last_results = analysis_results
        result = initial_result  # Initialize result from initial analysis

        while loop_count < self.max_loop_count:
            loop_count += 1

            # Extract details for AskHuman prompt
            code_check = last_results.get('code_check', {})
            results = last_results.get('results', {})
            violations = code_check.get('violations', [])

            # Get design parameters from detailed_results
            detailed_results = results.get('detailed_results', {})
            geometry = detailed_results.get('geometry') or {}
            material = detailed_results.get('material') or {}
            loads = detailed_results.get('loads') or {}
            constraints = detailed_results.get('constraints') or {}

            # Build violation message
            violation_text = "\n".join([f"  - {v.get('description', 'Unknown violation')}" for v in violations])

            # Build AskHuman prompt
            ask_human_prompt = f"""**有限元分析结果 - 规范校核未通过** (第 {loop_count}/{self.max_loop_count} 轮)

您的设计方案未通过规范校核。具体违规如下：
{violation_text}

关键结果：
- 最大位移: {results.get('max_displacement_mm', 'N/A')} mm
- 最大应力: {results.get('max_stress_MPa', 'N/A')} MPa
- 最大弯矩: {results.get('max_moment_kNm', 'N/A')} kN*m

当前设计参数：
- 跨度: {geometry.get('length', 'N/A')} m
- 截面: {geometry.get('width', 'N/A')} x {geometry.get('height', 'N/A')} m
- 材料: {material.get('material_name', 'N/A')}

请根据以上信息，提供具体的设计改进方案：
1. 直接输入改进后的设计参数（JSON格式）
2. 描述需要调整的地方（如：增加截面高度到0.5m，改用C40混凝土）
3. 输入 "skip" 跳过改进，直接返回当前结果

请输入您的改进方案（第 {loop_count}/{self.max_loop_count} 轮）："""

            try:
                # Use AskHuman tool to get user input
                ask_human_tool = next(
                    t for t in self.available_tools.tool_map.values()
                    if hasattr(t, 'name') and t.name == 'ask_human'
                )

                user_input_result = await ask_human_tool.execute(inquire=ask_human_prompt)
                user_input = user_input_result.output if hasattr(user_input_result, 'output') else str(user_input_result)

                # Check if user wants to skip
                if user_input.strip().lower() == 'skip':
                    # Append skip message to result
                    return f"""{result}

---
**循环中止：用户选择跳过改进**
"""

                # Re-analyze with user's improvements
                loop_request = f"""{user_input}

Please update the design and re-analyze."""

                # Call run recursively with loop_request, passing current loop_count
                result = await self.run(original_request, loop_request=loop_request, _loop_count=loop_count)

                # Check if the new result is compliant
                new_results = self.extract_analysis_results(result)
                if new_results and new_results.get('code_check', {}).get('compliant', False):
                    # Success! Append loop summary
                    return f"""{result}

---
**循环完成：设计通过规范校核** (共 {loop_count} 轮)
"""

                # Not compliant yet, continue loop
                last_results = new_results

            except StopIteration:
                # AskHuman tool not found, return result with warning
                return f"""{result}

---
**警告: 无法使用 AskHuman 工具进行交互**
"""
            except Exception as e:
                # Error during AskHuman, return result with error
                return f"""{result}

---
**错误: 循环交互失败 - {str(e)}**
"""

        # Max loop count reached
        return f"""{result}

---
**循环中止：达到最大轮数 ({self.max_loop_count} 轮)**
"""

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
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
                if json_str.endswith('\n}'):
                    return json.loads(json_str)

            # Pattern 2: OpenManus execution log format with create_chat_completion
            match = re.search(r'create_chat_completion.*?executed:[\s\S]*?(\{[\s\S]*?\n\})\s*(?:Step|\Z)', response, re.DOTALL)
            if match:
                json_str = match.group(1)
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
            # Use a more specific pattern to avoid matching other JSON
            matches = re.findall(r'\{[^}]*"status"[^}]*\}', response, re.DOTALL)
            if matches:
                json_str = matches[-1]  # Get last match
                return json.loads(json_str)

            # Pattern 4: Extract the entire JSON object from error message
            # This handles cases where the response is just an error JSON
            json_match = re.search(r'(\{.*?"status".*?\})\s*$', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
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
