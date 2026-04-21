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
        max_iterations: int = 12,
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
        # Dynamically get supported structure types from AnalyzerFactory
        from structural_app.tool.analyzers.analyzer_factory import AnalyzerFactory
        supported_types = AnalyzerFactory.get_available_types()
        supported_types_str = ", ".join([f'"{t}"' for t in supported_types])

        # Create friendly type descriptions for user
        type_descriptions = {
            'beam': 'beam（简支梁）',
            'cantilever_beam': 'cantilever_beam（悬臂梁）',
            'continuous_beam': 'continuous_beam（连续梁）',
            'truss': 'truss（桁架）',
            'frame': 'frame（框架）'
        }
        supported_types_list = "\n".join([f"  - {type_descriptions.get(t, t)}" for t in supported_types])

        return f"""You are an expert structural engineer with deep knowledge of:
- Structural mechanics and analysis
- Material properties and selection
- Load calculations and combinations
- Design codes and standards (GB, AISC, Eurocode)
- Various structure types: beams, frames, trusses, plates, shells, etc.

Your task is to generate initial structural design proposals based on user requirements.

【系统支持的结构类型】★★★★★ 重要 ★★★★★
当前系统仅支持以下结构类型：{supported_types_str}

具体包括：
{supported_types_list}

如果用户输入的结构类型不在上述列表中（例如：拱桥、壳体、悬索桥、网架、拱结构等），你必须：
1. 立即调用 ask_human 工具告知用户该类型暂不支持
2. 列出当前支持的类型供用户选择
3. 询问用户是否改为设计支持的类型之一

示例回复（当用户要求设计不支持的类型时）：
"抱歉，系统暂不支持'拱桥'的设计。

当前支持的结构类型包括：
  - beam（简支梁）
  - cantilever_beam（悬臂梁）
  - continuous_beam（连续梁）
  - truss（桁架）
  - frame（框架）

请问您是否需要设计以上类型中的某一种？如需要，请告诉我具体的设计需求。"

注意：不要尝试为不支持的类型收集参数或生成设计方案。

CRITICAL OUTPUT FORMAT:
You MUST output a valid JSON object with the following structure:

{{{{
  "type": "<structure_type>",  // REQUIRED: "beam", "cantilever_beam", "continuous_beam", "frame", "truss", etc.
  "units": "<units>",          // REQUIRED: "m" or "mm" (specifies units for geometry)
  "geometry": {{{{
    "length": <number>,        // in specified units (m or mm)
    "width": <number>,         // in specified units (for cross-section)
    "height": <number>,        // in specified units (for cross-section)
    "n_elements": <integer>,   // number of finite elements (default: 20)
    "n_spans": <integer>       // ONLY for continuous_beam: number of spans (2-5)
  }}}},
  "material": {{{{
    "E": <number>,             // Young's modulus in Pa (e.g., 30e9 for C30 concrete)
    "nu": <number>,            // Poisson's ratio (e.g., 0.2 for concrete)
    "fy": <number>,            // Yield strength in Pa (optional)
    "material_name": "<string>" // e.g., "C30", "Q235", "Grade 60"
  }}}},
  "loads": {{{{
    "distributed": [           // Distributed loads
      {{{{
        "q": <number>,         // Load intensity in N/m (negative for downward)
        "direction": "y"       // "x" or "y"
      }}}}
    ],
    "point": [                 // Point loads (optional)
      {{{{
        "P": <number>,         // Load magnitude in N
        "location": <number>,  // Position along beam in same units as geometry
        "direction": "y"       // "x" or "y"
      }}}}
    ]
  }}}},
  "constraints": {{{{
    "support_type": "<type>"   // "simply_supported", "cantilever", "fixed_fixed", "continuous"
  }}}}
}}}}

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
   - Planar truss with pin-jointed members
   - Use when user says: "桁架", "truss"
   - REQUIRED geometry parameters:
     * span: 桁架跨度 (m) - horizontal span length
     * height: 桁架高度 (m) - truss height
     * n_panels: 节间数 (integer, typically 3-8)
       - Guideline: span/1.5 to span/2.0 meters per panel
       - Example: 6m span → 3-5 panels recommended
   - REQUIRED material parameters:
     * E: 弹性模量 (Pa) - Steel: 200e9, Aluminum: 70e9
     * A: 杆件截面积 (m²) - cross-sectional area of members
       - Typical range: 0.0005 to 0.002 m² (500-2000 mm²)
       - Estimate based on loads or ask user
     * fy: 屈服强度 (Pa) - Q235: 235e6, Q345: 345e6
   - REQUIRED loads:
     * nodal: 节点荷载数组 [{{"node": int, "Fx": float, "Fy": float}}]
     * If user provides distributed load q (kN/m), convert to nodal loads at ALL top chord nodes:
       - Top chord nodes: n_panels+2 to 2*n_panels+2 (total n_panels+1 nodes)
       - Interior nodes (not at supports): Fy = -q * panel_length
       - End nodes (first and last top chord node): Fy = -q * panel_length / 2  (half value)
       - MUST include ALL n_panels+1 top chord nodes, including the last one
     * Example for q=10kN/m, span=6m, n_panels=6, panel_length=1m:
       - Nodes 8,14 (ends): Fy = -5000 N  (half)
       - Nodes 9,10,11,12,13 (interior): Fy = -10000 N  (full)
   - Example JSON:
     {{
       "type": "truss",
       "units": "m",
       "geometry": {{"span": 6.0, "height": 1.2, "n_panels": 5}},
       "material": {{"E": 200e9, "A": 0.001, "fy": 235e6, "material_name": "Q235"}},
       "loads": {{"nodal": [
         {{"node": 7, "Fx": 0, "Fy": -5000}},
         {{"node": 8, "Fx": 0, "Fy": -10000}},
         {{"node": 9, "Fx": 0, "Fy": -10000}},
         {{"node": 10, "Fx": 0, "Fy": -10000}},
         {{"node": 11, "Fx": 0, "Fy": -10000}},
         {{"node": 12, "Fx": 0, "Fy": -5000}}
       ]}},
       "constraints": {{"support_type": "simply_supported"}}
     }}

5. "frame" - Frame structure (框架)
   - Multi-story, multi-bay frame with rigid beam-column connections
   - Use when user says: "框架", "frame", "刚架", "多层框架"
   - REQUIRED geometry parameters:
     * num_bays: 跨数 (integer) - number of bays/spans
     * num_stories: 层数 (integer) - number of stories/floors
     * bay_widths: 跨度数组 (array of floats) - width of each bay in meters
     * story_heights: 层高数组 (array of floats) - height of each story in meters
     * columns: 柱截面 {{"type": "rectangular", "width": float, "depth": float}}
     * beams: 梁截面 {{"type": "rectangular", "width": float, "depth": float}}
   - REQUIRED material parameters:
     * E: 弹性模量 (Pa) - Concrete C30: 30e9, Steel Q235: 200e9
     * nu: 泊松比 - Concrete: 0.2, Steel: 0.3
     * fy: 屈服强度 (Pa) - C30: 14.3e6, Q235: 235e6
   - REQUIRED loads:
     * beam_distributed: 梁分布荷载 [{{"story": int, "bay": int, "q": float, "direction": "y"}}]
     * lateral: 侧向荷载 (wind/seismic) [{{"story": int, "F": float}}] (optional)
     * nodal: 节点荷载 [{{"node": int, "Fx": float, "Fy": float}}] (optional)
   - REQUIRED boundary conditions:
     * column_base: "fixed" or "pinned" (typically "fixed" for frames)
   - Example JSON (3-story 2-bay frame):
     {{
       "type": "frame",
       "units": "m",
       "geometry": {{
         "num_bays": 2,
         "num_stories": 3,
         "bay_widths": [6.0, 6.0],
         "story_heights": [4.0, 3.5, 3.5],
         "columns": {{"type": "rectangular", "width": 0.4, "depth": 0.4}},
         "beams": {{"type": "rectangular", "width": 0.3, "depth": 0.6}}
       }},
       "material": {{
         "E": 30e9,
         "nu": 0.2,
         "fy": 14.3e6,
         "material_name": "C30"
       }},
       "loads": {{
         "beam_distributed": [
           {{"story": 1, "bay": 0, "q": -10000, "direction": "y"}},
           {{"story": 1, "bay": 1, "q": -10000, "direction": "y"}},
           {{"story": 2, "bay": 0, "q": -8000, "direction": "y"}},
           {{"story": 2, "bay": 1, "q": -8000, "direction": "y"}},
           {{"story": 3, "bay": 0, "q": -8000, "direction": "y"}},
           {{"story": 3, "bay": 1, "q": -8000, "direction": "y"}}
         ],
         "lateral": [
           {{"story": 1, "F": 20000}},
           {{"story": 2, "F": 15000}},
           {{"story": 3, "F": 10000}}
         ]
       }},
       "boundary": {{
         "column_base": "fixed"
       }}
     }}
   - Load conversion guidelines for frames:
     * Floor area load (kN/m²) → beam line load (kN/m):
       - For interior beams: q = floor_load × tributary_width
       - Tributary width = (bay_width_left + bay_width_right) / 2
     * Wind pressure (kN/m²) → story lateral force (kN):
       - F = wind_pressure × building_width × story_height
       - Apply at each floor level
     * Typical loads:
       - Dead load: 5 kN/m² (residential), 6-8 kN/m² (office)
       - Live load: 2-3 kN/m² (residential), 3-4 kN/m² (office)
       - Wind pressure: 0.4-0.6 kN/m² (depends on location and height)

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

4. For trusses (type="truss"):
   - Height-to-span ratio: typically 1/6 to 1/10
   - n_panels: typically 3-8, about span/1.5 to span/2.0 meters per panel
   - Member cross-sectional area (A): estimate based on loads
     * Light loads (<5kN/m): A ≈ 0.0005 m² (500 mm²)
     * Medium loads (5-10kN/m): A ≈ 0.001 m² (1000 mm²)
     * Heavy loads (>10kN/m): A ≈ 0.002 m² (2000 mm²)
   - Convert distributed loads to nodal loads at top chord nodes
   - Use Q235 steel (E=200e9 Pa, fy=235e6 Pa) as default

5. For frames (type="frame"):
   - Column sections: typically 400×400mm to 600×600mm for concrete
   - Beam sections: typically 300×600mm to 400×800mm for concrete
   - Story heights: 3.5-4.5m typical, first floor often 4.0m
   - Bay widths: 6-9m typical for concrete frames
   - Load conversion:
     * Floor load (kN/m²) → beam line load: q = load × tributary_width
     * Wind pressure → lateral force: F = pressure × width × height
   - Always use "fixed" for column_base (typical for frames)
   - Material: C30 concrete (E=30e9, nu=0.2, fy=14.3e6) is standard

6. For loads:
   - Residential: 2-3 kN/m² live load
   - Office: 3-4 kN/m² live load
   - Convert area loads to line loads based on tributary width

6. Material selection:
   - Concrete: E=30e9 Pa, nu=0.2, fy=14.3e6 Pa (C30)
   - Steel: E=200e9 Pa, nu=0.3, fy=235e6 Pa (Q235)

7. Always include the "type" field - this is CRITICAL for routing to the correct analyzer.

8. For continuous beams, ALWAYS include "n_spans" in geometry.

9. For trusses, ALWAYS include "span", "height", "n_panels" in geometry, and "A" in material.

10. For frames, ALWAYS include "num_bays", "num_stories", "bay_widths", "story_heights", "columns", "beams" in geometry.

CRITICAL: UNITS FIELD IS MANDATORY:
====================================
You MUST always include the "units" field in your JSON output. This is REQUIRED.
- If geometry values are in meters, set "units": "m"
- If geometry values are in millimeters, set "units": "mm"
- ALL geometry dimensions (length, width, height) must use the same units

Example 1 (using meters):
{{
  "type": "beam",
  "units": "m",
  "geometry": {{"length": 6.0, "width": 0.3, "height": 0.6}},
  ...
}}

Example 2 (using millimeters):
{{
  "type": "beam",
  "units": "mm",
  "geometry": {{"length": 6000, "width": 300, "height": 600}},
  ...
}}

Example 3 (continuous beam with 2 spans):
{{
  "type": "continuous_beam",
  "units": "m",
  "geometry": {{
    "length": 12.0,
    "width": 0.3,
    "height": 0.6,
    "n_elements": 40,
    "n_spans": 2
  }},
  "material": {{
    "E": 30e9,
    "nu": 0.2,
    "fy": 14.3e6,
    "material_name": "C30"
  }},
  "loads": {{
    "distributed": [{{"q": -10000, "direction": "y"}}],
    "point": []
  }},
  "constraints": {{
    "support_type": "continuous"
  }}
}}

Example 4 (cantilever beam):
{{
  "type": "cantilever_beam",
  "units": "m",
  "geometry": {{"length": 3.0, "width": 0.3, "height": 0.5}},
  "constraints": {{"support_type": "cantilever"}},
  ...
}}

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
★★★★★ IMPORTANT: Use structured parameters (recommended) ★★★★★

The ask_human tool now supports TWO modes:

MODE 1: Structured Parameters (RECOMMENDED - More Reliable)
-----------------------------------------------------------
Call ask_human with explicit parameters:

ask_human(
    question="请选择材料类型",
    options=["Q235钢材（弹性模量200GPa，屈服强度235MPa）", "C30混凝土（弹性模量30GPa，抗压强度14.3MPa）"],
    context={{"description": "厂房梁通常使用钢材或混凝土"}}
)

Benefits:
- Frontend displays radio buttons for easy selection
- No text parsing issues
- More reliable and consistent

MODE 2: Legacy Text Format (Fallback)
--------------------------------------
Call ask_human with formatted text:

ask_human(inquire="请选择材料类型：\\n1 - Q235钢材 : 弹性模量200GPa\\n2 - C30混凝土 : 弹性模量30GPa")

Note: This mode requires specific text formatting and may have parsing issues.

WHEN TO USE EACH MODE:
- Use MODE 1 (structured) for: material selection, yes/no confirmations, multiple choice questions
- Use MODE 2 (text) for: free-form text input, complex descriptions

EXAMPLES OF STRUCTURED PARAMETERS:

Example 1: Material selection
ask_human(
    question="请选择材料类型（厂房梁通常使用钢材或混凝土）",
    options=[
        "Q235钢材（弹性模量200GPa，屈服强度235MPa，适合大跨度）",
        "C30混凝土（弹性模量30GPa，抗压强度14.3MPa）"
    ]
)

Example 2: Yes/No confirmation
ask_human(
    question="确认截面尺寸：宽度0.2m，高度0.3m，是否正确？",
    options=["是 - 确认正确", "否 - 需要修改"]
)

Example 3: With context (warnings, scores, etc.)
ask_human(
    question="规范检查未通过，请选择处理方式",
    options=[
        "manual - 查看改进建议，手动修改后重新运行",
        "auto - 自动迭代优化直至满足规范"
    ],
    context={{
        "warnings": ["应力超限：180MPa > 156MPa", "挠度超限：15mm > 10mm"]
    }}
)

Example 4: With image
ask_human(
    question="请确认模型参数是否正确",
    options=["是 - 确认继续", "否 - 需要修改"],
    context={{"image_path": "/path/to/model_preview.png"}}
)

CRITICAL: Always prefer MODE 1 (structured parameters) when asking multiple choice questions.
Only use MODE 2 (text format) when you need free-form text input from the user.

OUTPUT FORMAT:
IMPORTANT: You MUST use the create_chat_completion tool to return your final answer.
The JSON should be returned as the content of the create_chat_completion tool.
- If you have all required information: Use create_chat_completion to return a valid JSON object.
- If you need more information: Use the ask_human tool FIRST.

CRITICAL: Do NOT use the terminate tool. Always use create_chat_completion to return your final answer.

【输入澄清规则】★★★★★ 重要 ★★★★★
当用户输入存在以下情况时，你必须主动调用 ask_human 工具进行澄清，不得自行猜测或直接输出设计 JSON：

1. **模糊表述**：如"大概6米"、"中等跨度"、"普通住宅"等不确定描述。你必须询问用户精确值，并提供合理选项或默认值建议。
   - 示例："跨度'大概6米'存在模糊，请确认精确跨度值（如6.0米）。"
   - 对于"中等跨度"，可根据结构类型提供典型范围供选择。

2. **参数矛盾**：如果用户对同一参数给出多个不同数值（如"跨度6米，但长度4米"），你必须列出矛盾项，让用户选择正确值。
   - 示例："参数长度存在矛盾，您同时提到跨度6米和长度4米，请确认正确的长度值：1-6米 2-4米"

3. **关键参数缺失**：对于设计必需的参数（如跨度、荷载、支撑类型），若用户未提供，必须询问，不得猜测。
   - 若缺失参数 ≥ 2 个，合并为一次 ask_human 调用（见下方【澄清时的最佳实践】）；若缺失参数仅 1 个，可单独询问并提供选项。

4. **与结构设计无关的输入**：如果用户输入与结构设计无关（如："天气"、"你好"、"闲聊"等），你必须调用 ask_human 工具，引导用户提供设计需求。
   - 第1-2次无关输入：友好引导，提供示例
   - 第3次无关输入：明确询问用户是否需要设计服务
   - 第4次及以后：如果仍无有效输入，调用 terminate 工具，status="failure"

   示例回复（第1-2次无关输入）：
   "您输入的内容似乎与结构设计无关。我可以帮助您设计各种结构，例如：
   - 简支梁：'设计一个简支梁，跨度6米，均布荷载10kN/m'
   - 框架：'设计一个3层2跨的混凝土框架'
   - 桁架：'设计一个跨度8米的钢桁架'

   请告诉我您需要设计什么类型的结构？"

   示例回复（第3次无关输入）：
   "您已多次输入与结构设计无关的内容。请问您是否需要结构设计服务？
   - 如需要，请提供具体设计需求（结构类型、跨度、荷载等）
   - 如不需要，请回复'取消'或'退出'"

注意：只有在连续多次（3次以上）无关输入且用户未表达设计意图时，才考虑终止。不要过早放弃。

【用户取消处理】★★★★★ 重要 ★★★★★
当用户明确表示取消时（如："算了"、"取消"、"不要了"、"退出"、"不做了"），你必须：
1. 先调用 ask_human 工具确认："您确定要取消当前设计任务吗？(是/否)"
2. 如果用户确认取消（回复"是"、"确定"、"取消"等），调用 terminate 工具，status="failure"
3. 如果用户表示继续（回复"否"、"继续"、"不取消"等），继续收集参数

注意：
- 不要在用户第一次说"算了"时立即终止，应该先确认
- 用户确认取消后，才能调用 terminate
- 这样可以避免误判用户意图

【用户授权处理】★★★★★ 重要 ★★★★★
当用户输入以下任一类表述时，表示用户授权你使用合理默认值补全所有缺失参数，不再逐一询问：
- "请你补全"
- "按照一般情况设计"
- "用默认值"
- "你看着办"
- "按典型设计"
- "就这样吧"
- 任何明确授权你自行决定的语句

此时，你应当：
1. 根据结构类型，使用工程经验选择典型、安全的默认值（参考下方"典型默认值参考"）。
2. 调用 ask_human 工具，向用户确认所用默认值（例如："将使用典型参数：截面0.3×0.6m，C30混凝土，均布荷载10kN/m，是否继续？(是/否)"）。
3. 用户回复"是"、"继续"、"可以"或任何肯定语句后，再调用 create_chat_completion 输出完整设计 JSON。
4. 如果用户回复"否"或提出修改，按用户意见调整后再输出。

注意：只有在用户明确授权后，才能使用默认值；如果用户未授权，仍需逐一询问缺失参数。

【典型默认值参考】（仅供授权补全时使用）
- 简支梁：跨度≤8m时，截面高取跨度的1/12~1/15，宽0.3~0.4m；荷载按住宅取线荷载约10kN/m；材料C30混凝土（E=30GPa，nu=0.2，fy=14.3MPa）。
- 连续梁：截面可稍薄，高取跨度的1/15~1/20。
- 悬臂梁：高取跨度的1/6~1/8，截面适当加宽。
- 框架：柱截面400×400~600×600mm，梁截面300×600~400×800mm，混凝土C30，柱底固定。
- 桁架：高度取跨度的1/6~1/10，杆件截面面积取0.001m²，材料Q235（E=200GPa，fy=235MPa）。

【澄清时的最佳实践】
- 当缺失参数 ≥ 2 个时，将所有缺失参数合并为一次 ask_human 调用（不传 options），
  在 question 中列出所有缺失项并附上参数模板，让用户一次性填写。
  收到回复后，自行解析提取各参数值，无需再次询问已提供的参数。
  示例（框架设计缺少多个参数时）：
  ask_human(
      question="请提供框架设计参数（直接修改下方数值即可）：\n\n层数: 3\n跨数: 2\n各跨跨度(m): 6, 6\n各层层高(m): 4, 3.5, 3.5\n柱截面: 宽0.4 × 高0.4 m\n梁截面: 宽0.3 × 高0.6 m\n材料: C30混凝土\n楼面荷载(kN/m²): 10\n风荷载(kN/m²): 0.5（可选，不需要可删除）"
  )
  示例（桁架设计缺少多个参数时）：
  ask_human(
      question="请提供桁架设计参数（直接修改下方数值即可）：\n\n跨度(m): 6\n桁架高度(m): 1.2\n节间数: 5\n材料: Q235钢材\n均布荷载(kN/m): 10"
  )
- 当缺失参数 ≤ 2 个时，可逐个询问。
- 对于有明确选项的参数（如材料类型、支撑类型），仍使用 options 列表。
- 可提供合理的默认值供用户确认（如"未指定截面，推荐使用 0.3m×0.6m，是否采用？(是/否)"）。
- 用户回复后，若仍有少量参数不明确，再针对性补问（最多再问 1 轮），不要反复多轮询问同类参数。

【何时输出最终设计】
- 只有当所有必要参数明确、无矛盾后，你才能使用 create_chat_completion 工具输出完整的设计 JSON。
- 输出前应再次确认参数合理性（如跨度与截面比例在合理范围）。
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

        # Extract and standardize the design proposal
        design_proposal = self.extract_design_proposal(result)
        if design_proposal:
            # Apply parameter standardization (方案4)
            standardized_design = self._standardize_parameters(design_proposal)
            # Convert back to JSON string for return
            import json
            result = json.dumps(standardized_design, indent=2, ensure_ascii=False)
            print(f"\n[StructuralDesignAgent] Standardized design proposal:")
            print(result)

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

    def _standardize_parameters(self, design: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize parameters: convert LLM-generated parameters to structure-specific format

        This method handles parameter name mismatches between what LLM generates
        and what each structure type's analyzer expects.

        Args:
            design: Design proposal from LLM

        Returns:
            Standardized design proposal
        """
        structure_type = design.get('type')
        geometry = design.get('geometry', {})
        material = design.get('material', {})
        loads = design.get('loads', {})

        # Contradiction detection: warn if length and span both present with different values
        if 'length' in geometry and 'span' in geometry:
            if geometry['length'] != geometry['span']:
                print(f"[WARNING] 参数矛盾：geometry.length={geometry['length']} 与 geometry.span={geometry['span']} 不一致，请检查 LLM 输出。")

        # Parameter mapping table for each structure type
        PARAM_MAPPING = {
            'beam': {
                'geometry_aliases': {},  # beam uses standard names
                'material_aliases': {},
                'load_aliases': {},
                'required_geometry': ['length', 'width', 'height'],
                'required_material': ['E', 'nu'],
                'required_loads': ['distributed', 'point']
            },
            'cantilever_beam': {
                'geometry_aliases': {},
                'material_aliases': {},
                'load_aliases': {},
                'required_geometry': ['length', 'width', 'height'],
                'required_material': ['E', 'nu'],
                'required_loads': ['distributed', 'point']
            },
            'continuous_beam': {
                'geometry_aliases': {},
                'material_aliases': {},
                'load_aliases': {},
                'required_geometry': ['length', 'width', 'height', 'n_spans'],
                'required_material': ['E', 'nu'],
                'required_loads': ['distributed', 'point']
            },
            'truss': {
                'geometry_aliases': {
                    'length': 'span',           # length → span
                    'n_elements': 'n_panels'    # n_elements → n_panels
                },
                'material_aliases': {},
                'load_aliases': {
                    'distributed': 'nodal',     # distributed → nodal (needs conversion)
                    'point': 'nodal'            # point → nodal (needs conversion)
                },
                'required_geometry': ['span', 'height', 'n_panels'],
                'required_material': ['E', 'A'],
                'required_loads': ['nodal']
            }
        }

        if structure_type not in PARAM_MAPPING:
            # Unknown structure type, return as-is
            return design

        mapping = PARAM_MAPPING[structure_type]

        # 1. Apply geometry parameter aliases
        for old_name, new_name in mapping['geometry_aliases'].items():
            if old_name in geometry and new_name not in geometry:
                geometry[new_name] = geometry.pop(old_name)
                print(f"[ParameterStandardization] Converted geometry.{old_name} → geometry.{new_name}")

        # 2. Apply material parameter aliases
        for old_name, new_name in mapping['material_aliases'].items():
            if old_name in material and new_name not in material:
                material[new_name] = material.pop(old_name)
                print(f"[ParameterStandardization] Converted material.{old_name} → material.{new_name}")

        # 3. Handle structure-specific parameter inference
        if structure_type == 'truss':
            # Infer n_panels if missing
            if 'n_panels' not in geometry and 'span' in geometry:
                span = geometry['span']
                geometry['n_panels'] = max(3, min(8, int(span / 1.5)))
                print(f"[ParameterStandardization] Inferred n_panels={geometry['n_panels']} from span={span}m")

            # Infer A (cross-sectional area) if missing
            if 'A' not in material:
                # Estimate based on loads if available
                if 'distributed' in loads and loads['distributed']:
                    q = abs(loads['distributed'][0].get('q', 0))
                    if q < 5000:  # < 5kN/m
                        material['A'] = 0.0005
                    elif q < 10000:  # 5-10kN/m
                        material['A'] = 0.001
                    else:  # > 10kN/m
                        material['A'] = 0.002
                else:
                    material['A'] = 0.001  # Default: 1000 mm²
                print(f"[ParameterStandardization] Inferred A={material['A']} m² (cross-sectional area)")

            # Convert distributed/point loads to nodal loads
            if ('distributed' in loads or 'point' in loads) and 'nodal' not in loads:
                nodal_loads = self._convert_to_nodal_loads(geometry, loads)
                loads['nodal'] = nodal_loads
                # Remove old load formats
                loads.pop('distributed', None)
                loads.pop('point', None)
                print(f"[ParameterStandardization] Converted distributed/point loads to {len(nodal_loads)} nodal loads")

        # Update design with standardized parameters
        design['geometry'] = geometry
        design['material'] = material
        design['loads'] = loads

        return design

    def _convert_to_nodal_loads(self, geometry: Dict, loads: Dict) -> list:
        """
        Convert distributed/point loads to nodal loads for truss

        Args:
            geometry: Geometry parameters (must include span, n_panels)
            loads: Load parameters (distributed and/or point)

        Returns:
            List of nodal loads [{"node": int, "Fx": float, "Fy": float}]
        """
        nodal_loads = []
        span = geometry.get('span', 10.0)
        n_panels = geometry.get('n_panels', 5)
        panel_length = span / n_panels

        # Convert distributed loads to nodal loads at top chord
        if 'distributed' in loads:
            for dist_load in loads['distributed']:
                q = dist_load.get('q', 0)  # N/m
                direction = dist_load.get('direction', 'y')

                # Apply to top chord nodes (nodes n_panels+2 to 2*n_panels+2)
                # Each interior node gets q * panel_length
                # End nodes get q * panel_length / 2
                for i in range(n_panels + 1):
                    node_id = (n_panels + 1) + i + 1  # Top chord node ID

                    if i == 0 or i == n_panels:
                        # End nodes: half load
                        load_magnitude = q * panel_length / 2
                    else:
                        # Interior nodes: full load
                        load_magnitude = q * panel_length

                    if direction == 'y':
                        nodal_loads.append({"node": node_id, "Fx": 0.0, "Fy": load_magnitude})
                    else:
                        nodal_loads.append({"node": node_id, "Fx": load_magnitude, "Fy": 0.0})

        # Convert point loads to nodal loads
        if 'point' in loads:
            for point_load in loads['point']:
                P = point_load.get('P', 0)
                location = point_load.get('location', span / 2)
                direction = point_load.get('direction', 'y')

                # Find nearest node
                node_index = round(location / panel_length)
                node_id = (n_panels + 1) + node_index + 1  # Top chord node

                if direction == 'y':
                    nodal_loads.append({"node": node_id, "Fx": 0.0, "Fy": P})
                else:
                    nodal_loads.append({"node": node_id, "Fx": P, "Fy": 0.0})

        return nodal_loads

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
