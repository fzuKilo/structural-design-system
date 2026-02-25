# 技术决策记录

本文档记录项目中的重要技术决策及其理由。

---

## TD-001: 依赖管理策略

**日期**：2026-02-06  
**决策者**：开发团队  
**状态**：✅ 已实施

### 背景

项目依赖 OpenManus 框架，需要决定如何管理这个依赖关系。原始实现使用 `sys.path.insert()` 硬编码路径，存在以下问题：
- 路径不可移植
- 协作开发困难
- 不符合 Python 包管理最佳实践

### 决策

采用混合依赖管理策略：

1. **普通协作者**：从 GitHub 安装 OpenManus
   ```txt
   # requirements.txt
   git+https://github.com/FoundationAgents/OpenManus.git
   ```

2. **核心开发者**：使用可编辑模式安装本地 OpenManus
   ```bash
   pip install -e /path/to/openmanus
   ```

### 理由

- **可移植性**：使用标准 Python 包管理，无硬编码路径
- **灵活性**：支持两种开发模式
- **简单性**：普通协作者一键安装所有依赖
- **开发效率**：核心开发者可同时修改两个项目

### 影响

- 移除了 `fe_analysis_tool.py` 中的 sys.path hack
- 更新导入语句为 `from openmanus.app.tool.base import ...`
- 更新 README 和 requirements.txt 文档

### 替代方案

1. **Git Submodule**：复杂度高，不适合此场景
2. **复制源码**：维护困难，版本同步问题
3. **仅支持 pip install -e**：对普通协作者不友好

---

## TD-002: 通用架构原则

**日期**：2026-02-05  
**决策者**：开发团队  
**状态**：✅ 已实施

### 背景

需要设计一个支持多种结构类型（梁、框架、桁架等）的系统架构。

### 决策

采用"LLM 层通用，类型区分在 Tool 层"的架构原则：

```
Agent 层（通用）
    ↓ 调用
Tool 层（类型特定）
    ↓ 使用
Analyzer 层（类型特定实现）
```

### 理由

- **可扩展性**：添加新结构类型只需实现新的 Analyzer
- **代码复用**：Agent 层逻辑完全通用
- **关注点分离**：LLM 不需要知道结构类型细节
- **测试友好**：各层可独立测试

### 实施

- 创建抽象基类 `StructureAnalyzer`
- 实现工厂模式 `AnalyzerFactory`
- Tool 层根据 `structure_type` 参数路由到对应 Analyzer

### 约束

- **严格禁止**：Agent 层代码中出现 `if type == "beam"` 等类型判断
- **类型识别**：仅在 Factory 层进行

---

## TD-003: 有限元分析引擎选择

**日期**：2026-02-05  
**决策者**：开发团队  
**状态**：✅ 已实施

### 背景

需要选择有限元分析引擎。原计划使用 PyMAPDL (Ansys)。

### 决策

使用 **OpenSeesPy** 替代 PyMAPDL

### 理由

- **开源免费**：无需 Ansys 许可证
- **轻量级**：安装简单，依赖少
- **专业性**：专为结构工程设计
- **Python 原生**：API 友好
- **教育友好**：适合毕业设计项目

### 权衡

- **功能范围**：OpenSeesPy 专注结构分析，PyMAPDL 更全面
- **工业应用**：PyMAPDL 在工业界更常用
- **学习曲线**：OpenSeesPy 相对简单

### 未来考虑

可以通过工厂模式支持多种分析引擎：
```python
AnalyzerFactory.register("beam_opensees", OpenSeesBeamAnalyzer)
AnalyzerFactory.register("beam_ansys", AnsysBeamAnalyzer)
```

---

## TD-004: 测试策略

**日期**：2026-02-05  
**决策者**：开发团队  
**状态**：✅ 已实施

### 决策

采用分层测试策略：

1. **单元测试**：测试各个 Analyzer 和 Tool
2. **集成测试**：测试 Agent-Tool 交互
3. **端到端测试**：测试完整设计流程

### 实施

- 使用 pytest 框架
- 每个模块对应一个测试文件
- 使用 fixture 提供测试数据
- 验证物理合理性（不仅仅是代码正确性）

### 覆盖率目标

- 核心模块：>90%
- 工具层：>80%
- Agent 层：>70%

---

## TD-007: 包命名与 OpenManus 命名空间冲突解决

**日期**：2026-02-11
**决策者**：开发团队
**状态**：✅ 已实施

### 背景

项目本地有一个 `app/` 包，与 OpenManus 框架的 `app/` 包命名冲突，导致：
- `from app.agent.toolcall import ToolCallAgent` 导入失败
- Python 优先导入本地 `app` 包，而不是 OpenManus 的 `app` 包

### 决策

将本地 `app` 包重命名为 `structural_app`

### 理由

- **彻底解决冲突**：重命名后，`from app.` 开头的导入会正确找到 OpenManus 的包
- **长期有效**：一次解决，避免技术债务
- **简单直接**：比 sys.path hack 更清晰
- **后续受益**：所有未来的 Agent 开发都不再需要处理命名空间问题

### 实施

1. 重命名目录 `app/` → `structural_app/`
2. 更新导入语句：
   - `tests/test_fe_analysis_tool.py`
   - `tests/test_structural_design_agent.py`
3. 移除 `structural_design_agent.py` 中的 sys.path hack（27行代码）
4. 简化 `tests/conftest.py`（不再需要复杂的路径配置）

### 影响

- 所有导入语句需要更新（从 `app.` 改为 `structural_app.`）
- OpenManus 的导入保持 `from app.` 不变（现在会正确找到 OpenManus 的包）

---

## TD-008: DeepSeek LLM 集成

**日期**：2026-02-11
**决策者**：开发团队
**状态**：✅ 已实施

### 背景

需要配置 LLM 供 StructuralDesignAgent 调用。原配置使用 GPT-4o。

### 决策

使用 **DeepSeek** 作为 LLM 提供商
- Provider: deepseek
- Model: deepseek-chat
- API Key: 用户配置

### 理由

- **成本优化**：DeepSeek 相比 GPT-4o 成本更低
- **性能良好**：DeepSeek 在代码和推理任务上表现优秀
- **本地配置**：用户已有 DeepSeek API key

### 实施

- 创建 `config.toml` 文件
- 配置 DeepSeek 相关参数
- 集成测试验证 LLM 调用成功

---

## TD-009: OpenManus 执行日志格式兼容

**日期**：2026-02-11
**决策者**：开发团队
**状态**：✅ 已实施

### 背景

OpenManus 的 ToolCallAgent 在执行时，LLM 的 JSON 响应被包裹在执行日志中，格式为：
```
Step 1: Observed output of cmd `create_chat_completion` executed:
{JSON}
Step 2: Observed output of cmd `terminate` executed:
...
```

原有的 JSON 提取正则表达式无法匹配这种格式。

### 决策

更新 `extract_design_proposal()` 方法，添加新的正则表达式模式：

```python
# Pattern 1: OpenManus execution log format
match = re.search(r'create_chat_completion.*?executed:\s*(\{.*?\})\s*(?:Step|\Z)', response, re.DOTALL)
```

### 理由

- **兼容性**：支持 OpenManus 的执行日志格式
- **向后兼容**：保留原有正则表达式模式作为后备
- **鲁棒性**：多种提取模式确保成功率

### 实施

添加第一个匹配模式来处理 OpenManus 日志格式，保持原有 4 种模式不变。

---

## TD-010: Windows 控制台 Unicode 编码处理

**日期**：2026-02-11
**决策者**：开发团队
**状态**：✅ 已实施

### 背景

Windows 控制台使用 GBK 编码，默认无法显示某些 Unicode 字符（✓ ✗ ⚠等）。

### 决策

将所有 Unicode 字符替换为 ASCII 字符：
- ✓ → [PASS]
- ✗ → [FAIL]
- ⚠ → [WARN]
- ✅ → [OK]/[SUCCESS]
- ⚡ → [OK]

### 理由

- **兼容性**：Windows 控制台完全支持 ASCII
- **清晰性**：方括号标记同样清晰易读
- **避免错误**：防止 UnicodeEncodeError 中断测试

---

## TD-018: JSON 提取功能增强

**日期**：2026-02-21
**决策者**：Lin-0408-Yiran
**状态**：✅ 已实施

### 背景

在真实 LLM 调用测试中发现以下问题：
1. `extract_design_proposal()` 的正则表达式无法匹配多行 JSON 内容
2. `extract_analysis_results()` 无法处理错误格式的 JSON 输出
3. LLM 有时返回不完整的 JSON 或错误消息

### 决策

1. **更新 Pattern 1 正则表达式**
   ```python
   # 将 \s* 改为 [\s\S]* 以匹配多行内容（包括换行符）
   pattern = r'create_chat_completion.*?executed:\s*([\s\S]*?)(?:\n\n|\s*Step|\Z)'
   ```

2. **新增 Pattern 4 处理错误 JSON**
   ```python
   # 从错误消息中提取完整的 JSON 对象
   pattern4 = r'Error.*?(\{.*?"status"\s*:\s*"error".*?\})'
   ```

3. **确保 JSON 完整性检查**
   ```python
   # 增加 endswith 检查确保 JSON 完整
   if json_str.endswith('}') or json_str.endswith('],'):
       # JSON 可能完整
   ```

### 理由

- **鲁棒性**：多种提取模式确保在各种输出格式下都能成功提取
- **错误处理**：status='error' 的结果也能被正确提取和判断
- **多行支持**：[\s\S]* 能匹配跨行的 JSON 内容

### 实施

1. `structural_app/agent/fe_analysis_agent.py`：
   - `extract_analysis_results()` 添加 Pattern 4
   - 增强 JSON 完整性检查

2. `structural_app/agent/structural_design_agent.py`：
   - `extract_design_proposal()` 更新 Pattern 1 正则表达式
   - 添加 endswith 检查

---

## TD-019: 提前类型检查

**日期**：2026-02-21
**决策者**：Lin-0408-Yiran
**状态**：✅ 已实施

### 背景

FEAnalysisAgent 在接收到不支持的结构类型时，仍会进入循环模式进行分析，造成：
- 无意义的分析调用
- 浪费 LLM API 调用次数
- 循环模式被触发但无法成功

### 决策

在 FEAnalysisAgent 的 `run()` 方法中添加提前类型检查：

```python
# 在分析前先检查 type 是否支持
supported_types = ['beam', 'frame', 'truss']  # 等
if design_proposal.get('type') not in supported_types:
    return f"错误：不支持的结构类型 '{design_proposal['type']}'"
```

### 理由

- **效率**：避免对不支持的类型进行无意义的分析
- **成本**：节省 LLM API 调用次数
- **用户体验**：快速返回明确的错误信息

### 实施

- `structural_app/agent/fe_analysis_agent.py`：在 `run()` 方法开头添加类型检查
- 如果类型不支持，直接返回错误消息，不进入后续流程

---

## TD-020: 友好错误提示策略

**日期**：2026-02-21
**决策者**：Lin-0408-Yiran
**状态**：✅ 已实施

### 背景

当 LLM 调用工具失败时，原始错误信息可能不清晰或英文，用户难以理解。

### 决策

实现分层错误提示策略：

1. **AnalyzerFactory/DrawerFactory 返回中文友好错误提示**
   ```python
   return f"错误：不支持的结构类型 '{structure_type}'"
   f"可用类型：{', '.join(cls._registry.keys())}"
   ```

2. **FEAnalysisTool/CADDrawingTool 添加可用类型提示**
   ```python
   return ToolResult(output=json.dumps({
       "status": "error",
       "error": f"不支持的结构类型 '{structure_type}'",
       "available_types": ["beam", "frame", "truss"]
   }))
   ```

3. **FEAnalysisAgent 分析失败时不进入循环模式**
   - 检测到永久性错误（如不支持的类型）时直接退出
   - 只有校核不通过时才进入循环改进模式

### 理由

- **用户体验**：清晰的中文错误提示更容易理解
- **可用类型提示**：帮助用户了解系统支持什么
- **模式分离**：永久性错误 vs. 可改进的校核失败

### 实施

- `structural_app/tool/analyzers/analyzer_factory.py`：添加可用类型提示
- `structural_app/tool/drawers/drawer_factory.py`：添加可用类型提示
- `structural_app/tool/fe_analysis_tool.py`：添加可用类型提示
- `structural_app/tool/cad_drawing_tool.py`：添加可用类型提示
- `structural_app/agent/fe_analysis_agent.py`：分析失败时不进入循环模式

---

## TD-021: 梁截面详图尺寸标注修复

**日期**：2026-02-23
**决策者**：Claude Code
**状态**：✅ 已实施

### 背景

梁截面详图的尺寸标注出现以下问题：
1. 宽度标注固定为 400mm，与实际设计不符
2. 标注起点位置错误（在线段中间）
3. 高度标注与实际设计不符

### 决策

1. **修改截面详图绘制策略**
   - 移除固定宽度 400mm 的示意绘制
   - 改用实际截面尺寸 `width_mm` 和 `height_mm` 绘制

2. **修正标注坐标计算**
   ```python
   # 在 _add_section_dimensions 中
   start_x = -width_mm / 2  # 计算居中偏移量
   start_y = 0

   # 调整标注的 p1/p2 位置以匹配实际矩形
   p1 = (start_x, start_y)  # 左下角
   p2 = (start_x + width_mm, start_y)  # 右下角
   ```

### 理由

- **图形与标注一致**：使用实际尺寸绘制，确保标注反映真实尺寸
- **坐标对齐**：考虑居中绘制的偏移量，确保标注对齐到矩形边缘
- **准确性**：避免固定值导致的标注错误

### 实施

- `structural_app/tool/drawers/beam_drawer.py`：
  - `_draw_beam_detail()`：使用实际 `width_mm` 和 `height_mm`
  - `_add_section_dimensions()`：计算 `start_x = -width_mm / 2`，调整标注位置

---

## TD-023: 标注显示 100 倍问题修复

**日期**：2026-02-25
**决策者**：Lin-0408-Yiran
**状态**：✅ 已实施

### 背景

用户报告标注显示值是实际值的 100 倍：
- 6000mm 显示为 600000
- 但图形线段长度正确

### 问题分析

**初步尝试的方案**：
1. **MTEXT 替代 DIMENSION**：标注数字不显示
2. **数值除以 100**：标注线长度错误（p2 从 length_mm 变成 length_mm/100）
3. **创建 MM_UNITS 样式 + 手动设置 text**：标注数字不显示

**根本原因**：
- 通过手动修改 AutoCAD 标注属性发现，ezdxf 默认 EZDXF 样式的 dimlfac=100
- ezdxf 内部用 mm 单位，AutoCAD 默认用 m，所以 dimlfac=100 是为了自动转换
- 标注显示 = 几何距离 × dimlfac = 6000 × 100 = 600000

### 决策

在三个 draw 方法中修改 EZDXF 样式的 dimlfac 从 100 改为 1.0：

```python
# Fix EZDXF dimstyle: change dimlfac from 100 to 1 for correct mm units
dimstyle = doc.dimstyles.get('EZDXF')
if dimstyle:
    dimstyle.dxf.dimlfac = 1.0
```

### 理由

- **简单直接**：只需修改一个属性，无需重写标注逻辑
- **图形正确**：几何点不变，图形和标注线长度都正确
- **显示正确**：dimlfac=1.0 后，标注显示 = 6000 × 1.0 = 6000
- **代码干净**：回滚到干净版本后重新修复，避免代码混乱

### 实施

- `structural_app/tool/drawers/beam_drawer.py`：
  - `draw_elevation()`：添加 dimlfac 修改（第 87-91 行）
  - `draw_plan()`：添加 dimlfac 修改（第 142-145 行）
  - `draw_details()`：添加 dimlfac 修改（第 195-198 行）

### 影响

- 标注显示值正确（6000 显示 6000）
- 图形绘制不受影响（几何点还是 6000）
- 代码回滚到 commit 3c7e3b7 后重新修复

---

## TD-022: 多单位支持方案

**日期**：2026-02-23
**决策者**：Lin-0408-Yiran
**状态**：🔄 待实施

### 背景

用户报告标注数值错误（300mm 显示 30000，500mm 显示 50000），分析发现：
- LLM 返回的设计方案中，几何参数单位可能是 mm 而非 meters
- 代码假设输入为 meters 并乘以 1000，导致数值放大 100 倍

### 讨论的方案

**方案 A：按数值大小判断单位**
- 规则：length > 100 认为是 mm
- **问题**：不保险，后期结构类型增多容易出错

**方案 B：添加 units 字段显式声明**（推荐）
- 在 JSON 中添加 `units` 字段
- 支持值：`"m"` 或 `"mm"`

### 决策

采用**方案 B：添加 units 字段**

### 实施计划

1. **DesignAgent**
   - 在系统提示词中添加 `units` 字段说明
   - 示例：`"length": 6000, "width": 300, "height": 600, "units": "mm"`

2. **FEAnalysisTool**
   - 检测 `units` 字段
   - 如果是 `"mm"`，将几何参数 `/ 1000` 转成 meters（OpenSeesPy 需要）

3. **BeamDrawer**
   - 检测 `units` 字段
   - 如果是 `"m"`，将几何参数 `* 1000` 转成 mm（CAD 绘图需要）

### 理由

- **明确性**：`units` 字段显式声明，不会产生歧义
- **灵活性**：支持多种单位输入，提升用户体验
- **可扩展性**：未来可轻松添加新单位（如 cm）
- **安全性**：不依赖数值大小判断，避免误判

### 影响

- 需要更新所有涉及几何参数的模块
- 需要更新架构设计文档和扩展指南

---

## 模板

```markdown
## TD-XXX: 决策标题

**日期**：YYYY-MM-DD  
**决策者**：XXX  
**状态**：🔄 进行中 / ✅ 已实施 / ❌ 已废弃

### 背景
（为什么需要做这个决策？）

### 决策
（具体决定是什么？）

### 理由
（为什么这样决定？）

### 影响
（这个决策会影响什么？）

### 替代方案
（考虑过哪些其他方案？为什么没选？）
```

## TD-005: 多代理模式选择

**日期**：2026-02-07  
**决策者**：开发团队  
**状态**：✅ 已实施

### 背景

需要决定如何协调多个 Agent 的工作流程。最初考虑创建 MainCoordinatorAgent 来手动编排任务。

### 决策

使用 **OpenManus 的 PlanningFlow** 替代 MainCoordinatorAgent

### 理由

- **自动规划**：PlanningFlow 可以根据用户输入自动生成任务计划
- **减少代码**：无需手动编写协调逻辑
- **灵活性**：支持动态任务调整
- **框架原生**：充分利用 OpenManus 的能力
- **降低复杂度**：Agent 数量从 6 个减少到 5 个

### 实施

- 使用 PlanningFlow 进行任务编排
- 5 个专用 Agent：StructuralDesignAgent、FEAnalysisAgent、EvaluationAgent、CADDrawingAgent、ReportGenerationAgent
- 通过 [TYPE] 标记进行 Agent 路由

### 影响

- 简化了系统架构
- 提高了开发效率
- 更好地利用了 OpenManus 框架的能力

---


## TD-006: Agent 数量调整

**日期**：2026-02-07  
**决策者**：开发团队  
**状态**：✅ 已实施

### 背景

最初规划了 4 个专用 Agent，但在架构设计过程中发现报告生成和可视化功能较为复杂。

### 决策

将 Agent 数量从 4 个增加到 **5 个**，新增 **ReportGenerationAgent**

### 5 个 Agent 的职责分工

1. **StructuralDesignAgent**：参数收集、初步设计
2. **FEAnalysisAgent**：有限元分析验算
3. **EvaluationAgent**：设计质量评估
4. **CADDrawingAgent**：CAD 图纸生成
5. **ReportGenerationAgent**：报告生成与可视化（新增）

### 理由

- **职责分离**：报告生成和可视化是独立的功能模块
- **复杂度管理**：ReportGenerationAgent 需要整合所有前面的输出
- **可维护性**：独立的 Agent 更易于测试和维护
- **扩展性**：未来可以支持多种报告格式（PDF、HTML、Markdown）

### 影响

- 工作流程更加清晰
- 每个 Agent 的职责更加单一
- 便于并行开发和测试

---

## TD-011: AskHuman 工具集成方式

**日期**：2026-02-15
**决策者**：开发团队
**状态**：✅ 已实施

### 背景

需要让 LLM 在参数缺失时调用 AskHuman 工具询问用户。OpenManus 的 ToolCallAgent 使用 available_tools 属性来确定 LLM 可以调用的工具。

### 决策

在 FEAnalysisAgent 中正确设置 available_tools：

```python
# 在 __init__ 中
all_tools = tools + [CreateChatCompletion(), Terminate()]
self.available_tools = ToolCollection(*all_tools)
```

### 理由

- **LLM 可见性**：只有在 available_tools 中的工具，LLM 才会知道并调用
- **工具注册**：单纯添加到 tools 列表不够，必须设置 available_tools
- **集成测试验证**：通过测试验证 ask_human 在 available_tools.tool_map 中

### 实施

- FEAnalysisAgent.__init__() 中添加 available_tools 设置
- 测试验证：`test_agent_has_ask_human_tool()` 通过

---

## TD-012: 验证循环位置

**日期**：2026-02-15
**决策者**：开发团队
**状态**：✅ 已实施

### 背景

考虑在 FEAnalysisAgent.run() 中实现外部验证循环，在验证失败时插入系统消息让 LLM 重新思考。

### 决策

**不实现外部验证循环**，让 OpenManus 内部的 ReAct 循环处理：

```python
# 简化 run() 方法
async def run(self, request: str, **kwargs) -> str:
    # ... Prepare prompt ...
    result = await super().run(request=design_prompt, **kwargs)
    return result
```

### 理由

- **避免冲突**：外部循环与 OpenManus 内部 ReAct 循环冲突
- **AskHuman 交互**：OpenManus 内部循环已正确处理 AskHuman 多轮交互
- **简化代码**：不需要手动管理消息历史和迭代

### 问题记录

- **现象**：Agent 询问参数后，测试代码又询问一次，陷入循环
- **解决**：移除外部验证循环，让 OpenManus 自己处理

---

## TD-013: 参数验证架构

**日期**：2026-02-15
**决策者**：开发团队
**状态**：✅ 已实施

### 背景

需要定义不同结构类型的必要参数，用于判断是否需要询问用户。

### 决策

采用抽象基类 + 具体验证器模式：

```
ParameterValidator (抽象基类)
  ├── BeamValidator (必要参数：length, loads, support_type)
  ├── FrameValidator (必要参数：...)
  └── TrussValidator (必要参数：...)
```

### 理由

- **可扩展性**：添加新结构类型只需实现新的 Validator
- **代码复用**：通用验证逻辑在基类
- **关注点分离**：LLM 不需要知道参数细节
- **维护性**：每种结构类型定义自己的必要参数

### 实施

- 创建 `structural_app/tool/validators/base_validator.py`
- 创建 `structural_app/tool/validators/beam_validator.py`
- 定义必要参数与可默认参数的区分

---

## TD-014: FEAnalysisTool 参数格式兼容与 JSON 输出

**日期**：2026-02-16
**决策者**：Claude Code
**状态**：✅ 已实施

### 背景

FEAnalysisTool 在集成测试中遇到以下问题：
1. LLM 调用工具时传递 `design_proposal` 参数（JSON 字符串），但工具期望独立参数
2. ToolResult 输出使用 `str(dict)` 返回 Python 字典格式，无法被 json.loads() 解析
3. extract_analysis_results 正则表达式无法匹配长 JSON

### 决策

1. **添加 design_proposal 参数支持**
   ```python
   # 在参数定义中添加
   "design_proposal": {
       "type": "string",
       "description": "Complete design proposal in JSON format. This is an alternative to passing individual parameters."
   }
   ```

2. **统一 JSON 输出格式**
   ```python
   # 使用 json.dumps 确保标准 JSON 格式
   return ToolResult(output=json.dumps(output_data, ensure_ascii=False))
   ```

3. **修复 JSON 提取正则表达式**
   ```python
   pattern = r'fe_analysis.*?executed:\s*(\{.*?\})\s*(?:Step|\Z)'
   matches = re.findall(pattern, response, re.DOTALL)
   if matches:
       json_str = matches[-1]  # 获取最后一个匹配（最新结果）
       return json.loads(json_str)
   ```

### 理由

- **兼容性**：同时支持独立参数和 design_proposal 两种格式
- **标准性**：统一使用 json.dumps() 确保返回标准 JSON 格式
- **鲁棒性**：正则表达式使用非贪婪匹配 + Step/EOF 分隔符

### 实施

1. fe_analysis_tool.py：添加 design_proposal 参数
2. fe_analysis_tool.py：所有输出使用 json.dumps()
3. fe_analysis_agent.py：修复 extract_analysis_results() 方法

---

## TD-015: AskHuman 工具 EOFError 处理

**日期**：2026-02-16
**决策者**：Claude Code
**状态**：✅ 已实施

### 背景

在无交互环境下运行集成测试时，AskHuman 工具的 input() 调用会抛出 EOFError：
```
EOFError: EOF when reading a line
```

### 决策

在 OpenManus 的 `app/tool/ask_human.py` 中添加异常处理：
```python
async def execute(self, inquire: str) -> str:
    try:
        return input(f"""Bot: {inquire}\n\nYou: """).strip()
    except EOFError:
        return "EOF_ERROR"
```

### 理由

- **测试友好**：无交互环境下测试不会中断
- **明确错误**：返回 "EOF_ERROR" 字符串，便于调试
- **向后兼容**：交互环境下正常工作

---

## TD-016: Windows 控制台编码规范

**日期**：2026-02-16
**决策者**：Claude Code
**状态**：✅ 已实施

### 背景

测试脚本运行时出现 UnicodeEncodeError：
```
UnicodeEncodeError: 'gbk' codec can't encode character '\u26a0'
```

Windows 控制台使用 GBK 编码，无法显示 Unicode 字符（⚠️ ✓ ✗ 等）。

### 决策

在测试脚本中添加 UnicodeEncodeError 捕获：
```python
except UnicodeEncodeError as e:
    print(f"\n[FAIL] 编码错误: {e}")
    print("注意: 这是由于 Windows 控制台使用 GBK 编码，无法显示 Unicode 字符")
    print("请确保所有输出只使用 ASCII 字符 (参考 TD-010)")
    return False
```

### 理由

- **兼容性**：Windows 控制台完全支持 ASCII
- **清晰性**：方括号标记同样清晰易读
- **预防性**：提示用户参考 TD-010 避免类似问题

---

## TD-017: FEAnalysisAgent 循环模式实现

**日期**：2026-02-18
**决策者**：Claude Code
**状态**：✅ 已实施

### 背景

FEAnalysisAgent 需要在规范校核不通过时，自动询问用户进行设计改进。OpenManus 的 ReAct 循环模式需要正确配置才能支持这种多轮交互。

### 决策

采用递归调用 self.run() 实现改进循环：

```python
async def _enter_improvement_loop(self, ..., start_loop_count: int = 0) -> str:
    loop_count = start_loop_count

    while loop_count < self.max_loop_count:
        loop_count += 1

        # AskHuman 询问改进
        user_input_result = await ask_human_tool.execute(inquire=ask_human_prompt)
        user_input = user_input_result.output

        # 递归调用 run 进行重新分析
        result = await self.run(original_request, loop_request=loop_request, _loop_count=loop_count)

        # 检查是否通过校核
        new_results = self.extract_analysis_results(result)
        if new_results and new_results.get('code_check', {}).get('compliant', False):
            return result  # 通过，退出循环

        last_results = new_results  # 继续循环

    return result  # 达到最大轮数，退出循环
```

### 理由

- **避免冲突**：外部 while 循环与 OpenManus 内部 ReAct 循环冲突
- **AskHuman 集成**：OpenManus 内部循环已正确处理 AskHuman 多轮交互
- **轮次传递**：通过 _loop_count 和 start_loop_count 参数在递归调用间传递轮次信息
- **简化代码**：不需要手动管理消息历史和迭代

### 参数传递机制

```python
# 1. 在 run() 方法中过滤 _loop_count
parent_kwargs = {k: v for k, v in kwargs.items() if k not in ('loop_request', '_loop_count')}

# 2. 在递归调用时传递当前轮次
result = await self.run(original_request, loop_request=loop_request, _loop_count=loop_count)

# 3. 在 _enter_improvement_loop 中使用 start_loop_count
async def _enter_improvement_loop(self, ..., start_loop_count: int = 0):
    loop_count = start_loop_count
```

### 问题记录

- **问题 1**：循环模式完全不工作
  - **原因**：之前的代码尝试直接调用 fe_analysis_tool.execute()
  - **解决**：回滚到 commit aeb6dc7，使用正确的递归调用方式

- **问题 2**：轮次数字显示错误
  - **原因**：递归调用重新进入 _enter_improvement_loop，loop_count 被重置为 0
  - **解决**：添加 start_loop_count 参数，在递归调用时传递当前轮次

- **问题 3**：analysis_prompt 双重嵌套
  - **原因**：analysis_prompt 包含外层的 "Analyze" 指令和内层的 "请分析" 指令
  - **解决**：简化 analysis_prompt，去掉外层指令

- **问题 4**：validate_analysis_results 显示原始方案
  - **原因**：验证时传入的是原始 design_proposal，而不是最终改进方案
  - **解决**：从 analysis_results.detailed_results 中提取最终设计方案

---

