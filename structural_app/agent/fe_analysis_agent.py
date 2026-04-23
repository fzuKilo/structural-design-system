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

# Get the directory where this file is located
_current_dir = os.path.dirname(os.path.abspath(__file__))
_structural_app_path = os.path.dirname(_current_dir)

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
        enable_visual_validation: bool = True,
        **kwargs
    ):
        """
        Initialize the FE Analysis Agent

        Args:
            name: Agent name (default: "FEAnalysisAgent")
            description: Agent description
            tools: List of tools available to the agent
            enable_loop: If True, automatically enter improvement loop when code_check fails
            **kwargs: Additional arguments passed to ToolCallAgent

        Loop Mode Behavior:
        - When enable_loop=True and code_check fails, automatically enters improvement cycle
        - Continues looping until design passes code check OR user inputs "skip"
        - No maximum loop count limit - fully iterative based on engineering logic
        - Warns after 5 consecutive failures to prompt user review
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
        object.__setattr__(self, 'enable_visual_validation', enable_visual_validation)

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
- **CRITICAL: The input request IS the DesignProposal in JSON format**
- **CRITICAL: You must pass the ENTIRE DesignProposal to the fe_analysis tool**
- **CRITICAL: The DesignProposal MUST include the "units" field** ("m" for meters or "mm" for millimeters)
- Return the AnalysisResults exactly as provided by the fe_analysis tool

ERROR RECOVERY:
- If fe_analysis returns "structure type is 'None'" or similar type errors: the DesignProposal is missing the "type" field. Extract the structure type from context (e.g. "beam", "frame", "truss") and add it to the JSON, then retry fe_analysis immediately. Do NOT use AskHuman.
- If fe_analysis returns "no node with tag X exists in the model": recalculate nodal load node IDs to match n_panels, then retry immediately. Do NOT use AskHuman.
- NEVER use AskHuman for tool errors or technical issues. Always attempt to fix and retry silently.

ANALYSIS WORKFLOW:
1. Read the input request - IT IS the DesignProposal in JSON format
2. Call the fe_analysis tool with the DesignProposal from the request
3. Return the AnalysisResults to the user

EXAMPLE:
If the input is:
{"type": "beam", "units": "m", "geometry": {...}, "material": {...}, "loads": {...}, "constraints": {...}}

Then call:
fe_analysis(design_proposal='{"type": "beam", "units": "m", ...}')
"""

    async def run(self, request: str, skip_visual_validation: bool = False, **kwargs) -> str:
        """
        Main execution method for the agent.

        Supports two modes:
        1. Normal mode: Analyze once and return results
        2. Loop mode: When code_check fails, automatically ask user for improvements
           and re-analyze until compliant or user skips

        Args:
            request: User's request (typically contains a DesignProposal)
            skip_visual_validation: If True, skip model preview generation (used in optimization loops)
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

        # 新增：如果 request 中没有包含完整的 DesignProposal，从上下文（memory）中提取
        # 这处理了 PlanningFlow 调用时，request 是 JSON 字符串但可能被包装的情况
        if not design_proposal:
            # 先尝试直接 json.loads（PlanningFlow 传入纯 JSON 字符串时命中）
            import json
            try:
                parsed = json.loads(request)
                if isinstance(parsed, dict) and parsed.get('type'):
                    design_proposal = parsed
            except (json.JSONDecodeError, Exception):
                pass

        if not design_proposal:
            # 尝试从整个对话历史中提取 DesignProposal
            import re
            import json
            # Look for DesignProposal in the request - handle both direct JSON and wrapped formats
            # Pattern: match JSON with type field that has "beam", "frame", etc.
            type_pattern = r'(\{[\s\S]*?"type"\s*:\s*"(beam|frame|truss|arch)"[\s\S]*?\n\})'
            type_match = re.search(type_pattern, request)
            if type_match:
                try:
                    design_proposal = json.loads(type_match.group(1))
                except json.JSONDecodeError:
                    pass

        # Prepare the analysis prompt with explicit instructions
        # 新增：明确告诉 LLM DesignProposal 的位置，并提供提取后的数据
        if design_proposal:
            # 2.2 可视化确认（在分析前让用户确认模型）
            # 新增：支持通过参数跳过预览图生成（用于优化循环）
            if self.enable_visual_validation and not skip_visual_validation:
                confirmed = await self._visual_validation(design_proposal)
                if not confirmed:
                    return "__CANCELLED__"

            # 将提取的 DesignProposal 明确写入 prompt
            request_with_proposal = f"""DesignProposal found in input:
```json
{json.dumps(design_proposal, ensure_ascii=False, indent=2)}
```

Use the fe_analysis tool to perform the finite element analysis.
Pass the DesignProposal above to the fe_analysis tool.
Return the complete AnalysisResults."""
        else:
            # 没有提取到 DesignProposal，使用原请求
            request_with_proposal = request

        analysis_prompt = f"""{request_with_proposal}

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

                # DEBUG: Print the loop count for debugging
                print(f"DEBUG: Entering improvement loop with start_loop_count={start_loop_count}")

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
        Continue looping until design is compliant or user skips.

        Args:
            original_request: Original analysis request
            initial_result: Initial analysis result string (for appending loop summaries)
            analysis_results: Results from initial analysis
            start_loop_count: Starting loop count (for recursive calls)

        Returns:
            Final analysis results (either compliant or user skipped)
        """
        loop_count = start_loop_count
        current_request = original_request
        last_results = analysis_results
        result = initial_result  # Initialize result from initial analysis
        consecutive_failures = 0  # Track consecutive failures to prevent infinite loops

        while True:  # Loop until compliant or user skips
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

            # Build structured question and context for ask_human
            ask_question = f"有限元分析结果 - 规范校核未通过（第 {loop_count} 轮）\n\n请根据以下信息提供改进方案，或选择跳过："
            ask_context = {
                "violations": violation_text,
                "max_displacement": f"{results.get('max_displacement_mm', 'N/A')} mm",
                "max_stress": f"{results.get('max_stress_MPa', 'N/A')} MPa",
                "max_moment": f"{results.get('max_moment_kNm', 'N/A')} kN·m",
                "current_span": f"{geometry.get('length', 'N/A')} m",
                "current_section": f"{geometry.get('width', 'N/A')} x {geometry.get('height', 'N/A')} m",
                "current_material": material.get('material_name', 'N/A'),
                "suggestions": [
                    "增加截面高度（如：将高度从当前值增加20%）",
                    "提高混凝土强度等级（如：C30 → C40）",
                    "增加配筋率",
                    "减小跨度或增加支撑",
                ],
            }
            ask_options = [
                "manual - 手动输入改进方案",
                "skip - 跳过改进，使用当前结果",
            ]

            try:
                # Use AskHuman tool to get user input
                ask_human_tool = next(
                    t for t in self.available_tools.tool_map.values()
                    if hasattr(t, 'name') and t.name == 'ask_human'
                )

                user_input_result = await ask_human_tool.execute(
                    question=ask_question,
                    options=ask_options,
                    context=ask_context,
                )
                user_input = user_input_result.output if hasattr(user_input_result, 'output') else str(user_input_result)

                # Check if user wants to skip (handles both "skip" and "skip - ..." option format)
                if user_input.strip().lower().startswith('skip'):
                    # Append skip message to result
                    return f"""{result}

---
循环中止：用户选择跳过改进
"""

                # Re-analyze with user's improvements
                loop_request = f"""{user_input}

Please update the design and re-analyze."""

                # Call run recursively with loop_request, passing current loop_count
                result = await self.run(original_request, loop_request=loop_request, _loop_count=loop_count)

                # Check if the new result is compliant
                new_results = self.extract_analysis_results(result)
                if new_results and new_results.get('code_check', {}).get('compliant', False):
                    # Success! Design passes code check
                    return f"""{result}

---
循环完成：设计通过规范校核（共 {loop_count} 轮）
"""

                # Not compliant yet, check for consecutive failures
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    # Continuous 5 failures, warn user
                    return f"""{result}

---
警告：连续 {consecutive_failures} 次改进未通过校核
请检查输入的改进方案是否有效（如：增加截面高度、提高混凝土强度等级）。
或输入 "skip" 跳过改进，直接返回当前结果。
"""

                # Continue loop
                last_results = new_results

            except StopIteration:
                # AskHuman tool not found, return result with warning
                return f"""{result}

---
警告：无法使用交互工具进行改进
"""
            except Exception as e:
                # Error during AskHuman, return result with error
                return f"""{result}

---
错误：循环交互失败 - {str(e)}
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
            # Find balanced JSON objects containing "status" field
            # Use a more robust approach to handle nested JSON
            balanced_json = self._find_balanced_json_with_status(response)
            if balanced_json:
                return json.loads(balanced_json)

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

    async def _visual_validation(self, design: Dict[str, Any]) -> bool:
        """
        生成模型示意图并通过 AskHuman 询问用户确认。
        返回 True 表示用户确认继续，False 表示取消分析。
        """
        import tempfile
        import os
        from pathlib import Path
        from structural_app.tool.visualizers.model_visualizer import ModelVisualizer

        stype = design.get("type", "beam")
        viz_methods = {
            "beam": ModelVisualizer.visualize_beam,
            "cantilever_beam": ModelVisualizer.visualize_cantilever_beam,
            "continuous_beam": ModelVisualizer.visualize_continuous_beam,
            "truss": ModelVisualizer.visualize_truss,
            "frame": ModelVisualizer.visualize_frame,
        }
        viz_func = viz_methods.get(stype)
        if viz_func is None:
            return True  # 不支持的结构类型，跳过确认

        # 确定图片保存路径：优先使用 output_dir，否则降级到临时目录
        if getattr(self, "output_dir", None):
            img_path = str(Path(self.output_dir) / "model_preview.png")
            delete_after = False
        else:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.close()
            img_path = tmp.name
            delete_after = True

        # 生成模型示意图
        try:
            viz_func(design, img_path)
            print(f"[模型确认] 示意图已生成：{img_path}")
        except Exception as e:
            print(f"[警告] 模型示意图生成失败，跳过可视化确认：{e}")
            return True

        # 通过 AskHuman 询问用户（使用结构化参数）
        ask_human_tool = next(
            (t for t in self.available_tools.tools if hasattr(t, "name") and t.name == "ask_human"),
            None,
        )
        if ask_human_tool is None:
            print("[警告] 未找到 AskHuman 工具，跳过可视化确认")
            return True

        # 格式化用户友好的参数显示
        question, context = self._format_user_friendly_prompt(stype, design, img_path)

        try:
            # Use structured parameters
            answer = await ask_human_tool.execute(
                question=question,
                options=["是 - 确认模型正确并继续分析", "否 - 取消分析"],
                context=context
            )
            response = str(answer).strip().lower()
        except Exception as e:
            print(f"[警告] AskHuman 执行失败，默认继续分析：{e}")
            return True
        finally:
            # 清除 image_path，防止后续 ask_human 复用预览图
            if hasattr(ask_human_tool, '_last_image_path'):
                ask_human_tool._last_image_path = None
            if delete_after:
                try:
                    os.remove(img_path)
                except Exception:
                    pass

        return response in ("y", "yes", "是", "确认", "正确", "1")

    def _format_user_friendly_prompt(self, stype: str, design: dict, img_path: str) -> tuple[str, dict]:
        """
        格式化用户友好的确认提示

        Returns:
            tuple: (question, context) for structured parameters
        """
        # 结构类型映射
        type_names = {
            'beam': '简支梁',
            'cantilever_beam': '悬臂梁',
            'continuous_beam': '连续梁',
            'truss': '桁架',
            'frame': '框架'
        }
        type_display = type_names.get(stype, stype)

        # 支座类型映射
        support_names = {
            'simply_supported': '简支',
            'fixed': '固定',
            'continuous': '连续支座',
            'cantilever': '悬臂'
        }
        support_type = design.get('constraints', {}).get('support_type', 'N/A')
        support_display = support_names.get(support_type, support_type)

        # 格式化几何参数
        geometry = design.get('geometry', {})
        geo_lines = []

        if 'length' in geometry:
            geo_lines.append(f"   • 总长度：{geometry['length']} 米")
        if 'width' in geometry:
            geo_lines.append(f"   • 截面宽度：{geometry['width']} 米")
        if 'height' in geometry or 'depth' in geometry:
            h = geometry.get('height') or geometry.get('depth')
            geo_lines.append(f"   • 截面高度：{h} 米")
        if 'n_spans' in geometry:
            geo_lines.append(f"   • 跨数：{geometry['n_spans']} 跨")
        if 'num_bays' in geometry:
            geo_lines.append(f"   • 柱跨数：{geometry['num_bays']} 跨")
        if 'num_stories' in geometry:
            geo_lines.append(f"   • 层数：{geometry['num_stories']} 层")

        geo_text = "\n".join(geo_lines) if geo_lines else "   （详见上图）"

        # 格式化荷载
        loads = design.get('loads', {})
        load_lines = []

        if 'distributed' in loads and loads['distributed']:
            for load in loads['distributed']:
                q_value = abs(load.get('q', 0)) / 1000  # 转换为 kN/m
                direction = "向下" if load.get('q', 0) < 0 else "向上"
                load_lines.append(f"   • 均布荷载：{q_value} kN/m（{direction}）")

        if 'point' in loads and loads['point']:
            for load in loads['point']:
                p_value = abs(load.get('P', 0)) / 1000  # 转换为 kN
                load_lines.append(f"   • 集中荷载：{p_value} kN")

        if 'beam_distributed' in loads and loads['beam_distributed']:
            total_beams = len(loads['beam_distributed'])
            load_lines.append(f"   • 梁均布荷载：{total_beams} 处")

        if 'lateral' in loads and loads['lateral']:
            total_lateral = len(loads['lateral'])
            load_lines.append(f"   • 水平荷载：{total_lateral} 处")

        if 'node_forces' in loads and loads['node_forces']:
            total_nodes = len(loads['node_forces'])
            load_lines.append(f"   • 节点荷载：{total_nodes} 处")

        if 'member_loads' in loads and loads['member_loads']:
            total_members = len(loads['member_loads'])
            load_lines.append(f"   • 杆件荷载：{total_members} 处")

        load_text = "\n".join(load_lines) if load_lines else "   如图所示"

        # 组装问题文本
        question = (
            f"请确认以下结构模型参数：\n\n"
            f"📐 结构类型：{type_display}\n\n"
            f"📏 几何尺寸：\n{geo_text}\n\n"
            f"🔗 支座条件：{support_display}\n\n"
            f"⚖️ 荷载情况：\n{load_text}\n\n"
            f"确认模型正确并继续分析？"
        )

        # 构建 context（包含图片路径）
        context = {
            "image_path": img_path
        }

        return question, context


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
