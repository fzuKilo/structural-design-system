# 结构设计系统 - Agent 架构设计文档

## 文档信息

- **版本**: v2.0
- **创建日期**: 2026-02-07
- **最后更新**: 2026-05-01
- **状态**: 已实现

---

## 1. 项目概述

### 1.1 系统简介

基于 OpenManus 框架构建的 AI 驱动结构设计系统，实现：
- 自然语言输入 → 交互式参数收集
- LLM 智能设计 → 生成结构方案
- 有限元分析 → OpenSeesPy 验算与校核（自动迭代，最多10轮）
- CAD 绘图 → ezdxf 自动生成图纸
- 量化评估 → 4维度设计质量评分
- 完整报告 → Markdown 格式设计报告
- BIM 导出 → IFC 文件 + Speckle 平台推送

### 1.2 核心架构理念

本系统采用**通用架构**设计，关键理念：

#### 1.2.1 LLM 层面：通用设计能力
- LLM 本身具备所有结构类型的设计知识
- 不需要为不同结构类型编写不同的 Agent
- Agent 保持通用，只负责协调和调用工具

#### 1.2.2 类型区分：仅用于工具层
- 区分结构类型是为了有限元建模、CAD 绘图和专业评估
- 通过抽象基类 + 工厂模式实现扩展
- 使用 `type` 字段进行动态路由

#### 1.2.3 职责分离
```
PlanningFlow（任务编排，自定义实现）
    ↓
Agent 层（继承 OpenManus ToolCallAgent，通用协调）
    ↓ 传递设计方案（含 type 字段）
Tool 层（继承 OpenManus BaseTool，通用路由）
    ↓ 根据 type 路由
实现层（类型特定）
    - BeamAnalyzer / CantileverBeamAnalyzer / ContinuousBeamAnalyzer / TrussAnalyzer / FrameAnalyzer
    - BeamDrawer / CantileverBeamDrawer / ContinuousBeamDrawer / TrussDrawer / FrameDrawer
    - BeamEvaluator / CantileverBeamEvaluator / ContinuousBeamEvaluator / TrussEvaluator / FrameEvaluator
    - BeamReporter / TrussReporter / FrameReporter
```

#### 1.2.4 扩展性
- 添加新结构类型时，Agent 代码零修改
- 只需实现新的 Analyzer + Drawer + Evaluator + Reporter 子类
- 在工厂类中注册即可

### 1.3 架构验收标准

- Agent 代码中不得出现 `if type == "beam"` 这样的硬编码
- 能够在不修改 Agent 的前提下添加新结构类型
- 所有类型特定的逻辑封装在 Tool 实现层

---

## 2. 技术栈

### 2.1 核心框架
- **OpenManus**: 多智能体协作框架（提供 ToolCallAgent、BaseTool、AskHuman 等基础组件）
- **Python 3.12+**: 开发语言

### 2.2 OpenManus 组件使用
- **ToolCallAgent**: 所有 Agent 的基类，提供工具调用、状态管理、记忆管理能力
- **BaseTool**: 所有 Tool 的基类，提供参数定义、验证和标准化调用接口
- **AskHuman**: 交互式参数收集工具（CLI 模式下使用）

> **注意**：`PlanningFlow` 是本系统自定义实现的编排器，并非继承 OpenManus 的 PlanningFlow。它负责协调各 Agent 的执行顺序、数据传递和 WebSocket 进度推送。

### 2.3 工程计算
- **OpenSeesPy**: 开源有限元分析库（梁、桁架、框架建模与计算）
- **NumPy/SciPy**: 辅助计算

### 2.4 可视化
- **matplotlib**: 静态图表生成（PNG，用于报告）
- **Plotly**: 交互式可视化生成（HTML，用于 Web 界面展示）

### 2.5 绘图
- **ezdxf**: 纯 Python DXF 生成

### 2.6 知识库
- **ChromaDB**: 向量数据库，用于 RAG 检索
- **RAGEngine**: 基于语义搜索的设计规范检索引擎

### 2.7 BIM 导出
- **ifcopenshell**: IFC 文件生成（IFC2X3 / IFC4）
- **specklepy**: Speckle 平台推送

### 2.8 LLM 服务
- **GPT-4o / Claude / DeepSeek**: 可配置（通过 config.toml）

---

## 3. Agent 层设计

### 3.1 整体架构

系统使用自定义 PlanningFlow 进行任务编排，包含5个专用 Agent，均继承自 OpenManus 的 `ToolCallAgent`：

| Agent | 类名 | 工具集 | 主要职责 |
|-------|------|--------|---------|
| 结构设计 | StructuralDesignAgent | AskHuman, CreateChatCompletion, Terminate | 参数收集、方案生成、参数标准化 |
| 有限元分析 | FEAnalysisAgent | FEAnalysisTool, AskHuman | 模型预览确认、有限元分析、可选改进循环 |
| 设计评估 | EvaluationAgent | EvaluationTool, AskHuman | 4维度量化评估（**主流程中被 PlanningFlow 绕过，直接调用 EvaluationTool**） |
| CAD 绘图 | CADDrawingAgent | CADDrawingTool, AskHuman | CAD 图纸生成（**主流程中 PlanningFlow 优先直接调用 Tool，失败时降级**） |
| 报告生成 | ReportGenerationAgent | ReportTool, VisualizationTool | 结构可视化、Markdown 报告生成（**无 AskHuman**） |

### 3.2 Agent 基类继承关系

```
BaseAgent (OpenManus)
    ↓
ToolCallAgent (OpenManus)  ← 提供 ReAct 循环、状态管理、记忆管理、工具调用
    ↓
StructuralDesignAgent / FEAnalysisAgent / EvaluationAgent / CADDrawingAgent / ReportGenerationAgent
```

各 Agent 覆盖 `system_prompt`、`available_tools`，并重写 `run()` 在 `super().run()` 前后注入自定义逻辑。

---

### 3.3 StructuralDesignAgent（结构设计 Agent）

**初始化**：`max_iterations=12`

**工具集**：`AskHuman`（CLI）/ `WebAskHuman`（Web，由 PlanningFlow 注入）、`CreateChatCompletion`、`Terminate`

#### System Prompt 关键内容

System Prompt 在构造时动态生成：

- **支持类型列表**：运行时从 `AnalyzerFactory.get_available_types()` 读取，写入 Prompt，LLM 不会生成未支持类型
- **每种类型的完整参数格式**：beam / cantilever_beam / continuous_beam / truss / frame 各有专属参数说明
- **桁架荷载换算公式**：端节点 `Fy = q × panel_length / 2`，内节点 `Fy = q × panel_length`（需列出全部 n_panels+1 个顶弦节点）
- **框架荷载换算**：楼面荷载（kN/m²）→ 梁线荷载 `q = load × tributary_width`；风压 → 层剪力 `F = pressure × width × height`
- `units` 字段为**必填项**（`"m"` 或 `"mm"`），所有 geometry 尺寸须使用同一单位

#### AskHuman 两种调用模式

**模式 1：结构化参数（推荐）**——前端渲染为单选按钮，无解析歧义：
```python
ask_human(
    question="请选择材料类型",
    options=["Q235钢材（E=200GPa, fy=235MPa）", "C30混凝土（E=30GPa, fy=14.3MPa）"],
    context={"description": "...", "image_path": "/path/preview.png"}
)
```

**模式 2：遗留文本格式（兜底）**——需特定分隔符格式，有解析风险：
```python
ask_human(inquire="请选择：\n1 - Q235钢材\n2 - C30混凝土")
```

`context` 字段还支持 `"warnings": [...]` 传递预警信息，`"image_path"` 传递图片路径（前端展示）。

#### 内置交互规则（System Prompt 硬编码）

| 场景 | 行为 |
|------|------|
| 模糊表述（"大概6米"、"中等跨度"） | 必须调用 ask_human 澄清，不得猜测 |
| 参数矛盾（同一参数给出两个值） | 列出矛盾项让用户二选一 |
| 缺失参数 ≥ 2 个 | 合并为一次 ask_human，含参数模板，用户一次填完 |
| 缺失参数 = 1 个 | 可单独询问并提供选项 |
| 用户取消（"算了"、"取消"） | 先 ask_human 确认，确认后才 terminate（防误判） |
| 授权补全（"请你补全"/"你看着办"） | ask_human 展示默认值列表 → 用户确认后才输出 JSON |
| 无关输入 | 前 2 次引导，第 3 次确认，第 4+ 次 terminate |

> **参数模板必须写在 `question` 字段，禁止放入 `context`**（context 仅用于警告/图片）

#### run() 执行流程

```
1. 构建 design_prompt → super().run()（ToolCallAgent ReAct 循环）
   └── LLM 自主调用 ask_human / create_chat_completion / terminate
2. 从返回文本提取 JSON（4 级 fallback）：
   Pattern 1: ```json ... ``` 代码块（优先，要求以 \n} 结尾）
   Pattern 2: create_chat_completion executed: { ... } 日志块（排除含 "..." 的省略输出）
   Pattern 3: ``` ... ``` 普通代码块（要求以 \n} 结尾）
   Pattern 4: 匹配含 "type" 字段的平衡 JSON 对象
3. 提取成功 → 调用 _standardize_parameters()
4. 返回标准化后的 JSON 字符串
```

#### _standardize_parameters() 后处理

| 结构类型 | 处理内容 |
|---------|---------|
| 所有类型 | 检测 `geometry.length` 与 `geometry.span` 矛盾并打印警告 |
| `truss` | `length → span`、`n_elements → n_panels` 别名转换 |
| `truss` | n_panels 缺失时按 `max(3, min(8, int(span/1.5)))` 推断 |
| `truss` | A 缺失时按荷载大小推断（<5kN/m: 0.0005m²；5~10kN/m: 0.001m²；>10kN/m: 0.002m²） |
| `truss` | distributed/point 荷载 → 节点荷载（端节点半载，内节点全载）并删除原格式 |
| 其他类型 | 暂无转换，参数原样保留 |

**验证器**：`_validator_map` 当前仅注册 `BeamValidator`（`'beam'`），frame / truss 待补充。

#### 输出格式（DesignProposal JSON）

```json
{
  "type": "beam",
  "units": "m",
  "geometry": { "length": 6.0, "width": 0.3, "height": 0.6, "n_elements": 20 },
  "material": { "E": 30000000000, "nu": 0.2, "fy": 235000000, "material_name": "Q235" },
  "loads": {
    "distributed": [{"q": -10000, "direction": "y"}],
    "point": []
  },
  "constraints": { "support_type": "simply_supported" }
}
```

---

### 3.4 FEAnalysisAgent（有限元分析 Agent）

**初始化参数**：
- `enable_loop: bool = False`（默认关闭内置改进循环；PlanningFlow 主流程用自己的迭代逻辑）
- `enable_visual_validation: bool = True`（默认开启模型预览确认）

**工具集**：`FEAnalysisTool`，`AskHuman`，`CreateChatCompletion`，`Terminate`

#### run() 执行流程

```
1. 从 request 提取 DesignProposal（json.loads / 正则 4 级 fallback）
2. AnalyzerFactory.is_registered(type) 检查
   └── 未注册 → 立即返回错误 JSON（含可用类型列表），不进入分析
3. enable_visual_validation && !skip_visual_validation
   └── 调用 _visual_validation()
   └── 用户取消 → 返回 "__CANCELLED__"（PlanningFlow 据此判断终止）
4. 构建 analysis_prompt → super().run()（ToolCallAgent ReAct 循环）
5. 从返回文本提取 AnalysisResults（4 级 fallback，优先匹配 fe_analysis executed: {...} 日志块）
6. enable_loop && !compliant → _enter_improvement_loop()
```

#### _visual_validation() 模型预览流程

```
1. 按 type 选择 ModelVisualizer 方法：
   beam / cantilever_beam / continuous_beam / truss / frame 各有专属可视化
2. 图片保存路径：
   - 有 output_dir → output_dir/model_preview.png（持久保存）
   - 无 output_dir → 系统临时文件（用后删除）
3. 调用 AskHuman（结构化模式）：
   question : 参数摘要（类型/几何尺寸/支座条件/荷载概况）
   options  : ["是 - 确认模型正确并继续分析", "否 - 取消分析"]
   context  : {"image_path": "<path_to_model_preview.png>"}
4. 返回值：
   - "y / yes / 是 / 确认 / 正确 / 1" → True（继续分析）
   - 其他 → False（返回 "__CANCELLED__"）
5. 执行后清除 ask_human_tool._last_image_path，防止后续弹窗复用预览图
```

**`skip_visual_validation` 参数**：PlanningFlow 在优化循环中重新分析时传 `True`，跳过预览图生成，避免重复弹窗。

#### _enter_improvement_loop()（仅 enable_loop=True 时触发）

```
while True:
  1. 向 AskHuman 展示：当前违规列表、现有参数（跨度/截面/材料）、改进建议列表
     options: ["manual - 手动输入改进方案", "skip - 跳过"]
  2. 用户回复 "skip"
     → 返回结果（附 "循环中止：用户选择跳过改进" 说明）
  3. 用户提供改进文本
     → 递归调用 run()（传入 loop_request，带 _loop_count）
     → 重新分析
       - compliant=True → 返回（附完成轮次）
       - consecutive_failures >= 5 → 警告并返回（建议检查改进方案有效性）
       - 否则继续下一轮
```

> ⚠️ 此循环**无硬性轮次上限**（连续5次失败后仅警告并返回，不强制终止）。
> PlanningFlow 主流程以 `enable_loop=False` 调用本 Agent，由 PlanningFlow 自己管理10轮上限；
> `enable_loop=True` 仅在将本 Agent 单独使用时有效。

#### System Prompt 错误恢复规则

LLM 工具调用出错时**必须自行修复后重试，严禁调用 AskHuman**：

| 错误信息 | 自动修复方式 |
|---------|------------|
| `structure type is 'None'` | 从上下文提取结构类型，补充 `type` 字段后重试 |
| `no node with tag X exists` | 重新计算节点 ID（按 n_panels 对齐）后重试 |

#### 输出格式（AnalysisResults JSON）

```json
{
  "status": "success",
  "results": {
    "max_displacement_mm": 1.04,
    "max_stress_MPa": 2.49,
    "max_moment_kNm": 44.78,
    "max_shear_kN": 30.0,
    "detailed_results": { "geometry": {...}, "displacements": [...], "moments": [...] }
  },
  "code_check": {
    "compliant": true,
    "violations": [],
    "safety_factors": { "stress": 63.05, "deflection": 5.77 }
  }
}
```

---

### 3.5 EvaluationAgent（设计评估 Agent）

> ⚠️ **主流程中被绕过**：PlanningFlow 直接调用 `EvaluationTool.execute()` 完成评估，不经过本 Agent。
> 本 Agent 仅供独立调用或调试使用。

**工具集**：`EvaluationTool`，`AskHuman`

**run() 执行流程**：拼接 evaluation_prompt → `super().run()` → 返回 EvaluationTool 输出文本（无额外处理）

#### 评分等级（来自 System Prompt）

| 等级 | 分数范围 |
|------|---------|
| A+   | ≥ 95    |
| A    | 90–94   |
| B+   | 85–89   |
| B    | 80–84   |
| C+   | 75–79   |
| C    | 70–74   |
| D    | < 70    |

#### 输出格式（EvaluationReport JSON）

```json
{
  "status": "success",
  "comprehensive_score": 82.5,
  "grade": "B",
  "dimensions": {
    "economy":               {"score": 78.0, "indicators": {...}},
    "structural_efficiency": {"score": 85.0, "indicators": {...}},
    "safety":                {"score": 88.0, "indicators": {...}},
    "sustainability":        {"score": 75.0, "indicators": {...}}
  },
  "recommendations": ["建议增大截面以提高安全裕度"]
}
```

---

### 3.6 CADDrawingAgent（CAD 绘图 Agent）

> ⚠️ **主流程中被降级使用**：PlanningFlow 优先直接调用 `CADDrawingTool.execute()`；失败时才调用本 Agent。

**工具集**：`CADDrawingTool`，`AskHuman`

**run() 执行流程**：拼接 drawing_prompt → `super().run()` → 返回结果

#### System Prompt 关键约束（桁架参数保护规则）

LLM 在调用 cad_drawing 工具时**禁止转换或补全参数**，必须原样透传 DesignProposal 中的字段：

| 正确（原样传递） | 错误（禁止转换） |
|----------------|----------------|
| `geometry.span` | ~~`geometry.length`~~ |
| `geometry.n_panels` | ~~`geometry.n_elements`~~ |
| `loads.nodal` | ~~`loads.distributed` / `loads.point`~~ |
| 不补默认值 | ~~`"width": 0.0`~~ |

#### 输出格式（DrawingResults JSON）

```json
{
  "status": "success",
  "files": {
    "plan_view":      "output/.../beam_plan_20260501_143022.dxf",
    "elevation_view": "output/.../beam_elevation_20260501_143022.dxf",
    "section_view":   "output/.../beam_section_20260501_143022.dxf"
  },
  "metadata": {
    "structure_type":    "beam",
    "drawing_standard":  "GB/T 50001-2017",
    "scale":             "1:50",
    "units":             "mm",
    "generated_at":      "2026-05-01T14:30:22",
    "plan_preview":      "output/.../plan_preview.png",
    "elevation_preview": null,
    "detail_preview":    null
  },
  "notes": ["图纸已按 GB/T 50001-2017 标准生成"]
}
```

---

### 3.7 ReportGenerationAgent（报告生成 Agent）

**工具集**：`ReportTool`，`VisualizationTool`

> ⚠️ **无 AskHuman**（已明确移除）：本 Agent 直接从传入数据生成报告，System Prompt 明确禁止调用 ask_human。

#### run() 执行流程（含预先执行优化）

```
1. 解析 request JSON，提取：
   - design_proposal
   - analysis_results_full（优先）或 analysis_results（降级）→ 用于可视化（保留完整数组）
   - skip_visualization 标志
2. 根据 skip_visualization 决定执行路径：

   ┌─ skip_visualization=True（report_only 模式）
   │   → 构建 REPORT_ONLY MODE prompt，告知 LLM 跳过可视化
   │
   ├─ skip_visualization=False
   │   → 直接调用 viz_tool.execute(design_proposal, analysis_results) 预先生成可视化
   │   │
   │   ├─ 成功 → 构建 prompt，告知 LLM 可视化已完成，勿重复调用
   │   └─ 失败 → 构建 prompt，告知 LLM 错误原因，要求 LLM 自行重试
   └

3. super().run()（ToolCallAgent ReAct 循环，根据 prompt 调用 ReportTool）
4. 从输出分别提取 visualization_results 和 report_results，合并返回
```

> **为何预先执行可视化？** ToolCallAgent ReAct 循环中 LLM 有时会跳过可视化步骤直接调用 ReportTool。通过在 `run()` 中先手动调用 `viz_tool.execute()`，确保可视化结果在 prompt 中显式存在，LLM 不会遗漏该步骤。

#### analysis_results_full 机制

PlanningFlow 的 `_build_report_request()` 在传给 ReportGenerationAgent 的 JSON 中同时包含两份分析结果：
- `analysis_results`：裁剪了 `detailed_results` 内大数组（displacements / stresses / moments 等），避免超出 LLM 工具参数长度限制
- `analysis_results_full`：保留完整数组，供 VisualizationTool 绘制精确图表

ReportGenerationAgent 的 `run()` 优先使用 `analysis_results_full` 调用可视化工具，降级时才用裁剪版。

#### 输出格式（ReportResults JSON）

```json
{
  "status": "success",
  "report_file": "output/beam_20260501_143022/reports/beam_design_report_20260501_143022.md",
  "visualizations": {
    "static": {
      "moment_diagram":   "output/.../moment_diagram.png",
      "shear_diagram":    "output/.../shear_diagram.png",
      "deflection_curve": "output/.../deflection_curve.png"
    },
    "interactive": {
      "moment_html":     "output/.../moment_diagram.html",
      "shear_html":      "output/.../shear_diagram.html",
      "deflection_html": "output/.../deflection_curve.html"
    }
  },
  "summary": {
    "structure_type":      "beam",
    "design_grade":        "B+",
    "comprehensive_score": 76.5,
    "code_compliant":      true
  }
}
```

---

## 4. Tool 层设计

### 4.1 整体架构

Tool 层负责具体的功能实现，通过工厂模式实现类型路由：

| Tool | 类名 | `name` 字段 | 调用方 | 路由工厂 |
|------|------|------------|--------|---------|
| 有限元分析 | FEAnalysisTool | `fe_analysis` | FEAnalysisAgent | AnalyzerFactory |
| 设计评估 | EvaluationTool | `evaluation` | PlanningFlow 直接调用 | EvaluatorFactory |
| CAD 绘图 | CADDrawingTool | `cad_drawing` | PlanningFlow 优先直接调用 | DrawerFactory |
| 报告生成 | ReportTool | `report` | ReportGenerationAgent | ReporterFactory |
| 可视化 | VisualizationTool | `visualization` | ReportGenerationAgent | VisualizerFactory |
| 人机交互 | WebAskHuman | `ask_human` | 全部 Agent（Web 模式注入） | — |

所有 Tool 均继承自 `BaseTool`（OpenManus），通过 `execute(**kwargs) -> ToolResult` 暴露接口。

### 4.2 工具基类继承关系

```
BaseTool (OpenManus)
    ├── FEAnalysisTool
    ├── EvaluationTool
    ├── CADDrawingTool
    ├── ReportTool
    └── VisualizationTool

AskHuman (OpenManus)  ← CLI 模式，阻塞 input()
    └── WebAskHuman   ← Web 模式，通过 WebSocket + Redis 异步交互
```

---

### 4.3 FEAnalysisTool

**调用方式（两种格式互斥）**：

| 格式 | 参数 | 说明 |
|------|------|------|
| 格式1（推荐） | `design_proposal: str/dict` | 整个 DesignProposal JSON，含 type/units/geometry/material/loads/constraints |
| 格式2（兼容） | `structure_type, geometry, material, loads, constraints, units` | 逐字段传入，`units` 默认 `"m"` |

**智能单位检测**：若 `units="m"` 但 geometry 中存在 `length ≥ 1000` 或 `length > 100 且 % 100 == 0` 的值，自动判定为 mm 并打印 `"Smart unit detection: detected mm units"`，在传入 Analyzer 前将所有尺寸除以 1000 转换为 m。

**execute() 执行流程**：

```
1. 解析输入（格式1/2），提取 structure_type、units、geometry 等
2. 智能单位检测（仅 units="m" 时触发）
3. AnalyzerFactory.is_registered(structure_type) → 不通过则返回 error
4. analyzer = AnalyzerFactory.create(structure_type)
5. mm → m 几何换算（仅 units="mm" 时，转换 length/width/height/n_elements，保留 n_spans 等额外字段）
6. analyzer.run_full_analysis(design) → {status, results, code_check}
7. 返回格式化 JSON（status/results/code_check）
```

**输出 JSON**：

```json
{
  "status": "success",
  "results": {
    "max_displacement":    0.012,
    "max_displacement_mm": 12.0,
    "max_stress":          1.5e8,
    "max_stress_MPa":      150.0,
    "max_moment":          45000,
    "max_moment_kNm":      45.0,
    "max_shear":           30000,
    "max_shear_kN":        30.0,
    "structure_type":      "beam",
    "detailed_results":    { ... }
  },
  "code_check": {
    "compliant":  true,
    "violations": [],
    "safety_factors": { ... }
  }
}
```

`detailed_results` 为 `AnalysisResults.to_dict()` 的完整输出（含大数组），由 PlanningFlow 在传给 ReportAgent 时裁剪。

---

### 4.4 EvaluationTool

**调用方式（两种格式互斥）**：

| 格式 | 参数 |
|------|------|
| 格式1（推荐） | `evaluation_data: str/dict`，内含 `design_proposal` + `analysis_results` |
| 格式2 | `design_proposal: dict, analysis_results: dict` |

**execute() 执行流程**：

```
1. 解析输入，提取 design_proposal + analysis_results
2. 检查必填项（两者均不可为空）
3. EvaluatorFactory.is_registered(structure_type) → 不通过则返回 error
4. evaluator = EvaluatorFactory.create(structure_type)
5. evaluator.evaluate_comprehensive(design_proposal, analysis_results)
6. 返回格式化 JSON
```

**输出 JSON**：

```json
{
  "status": "success",
  "comprehensive_score": 82.5,
  "grade": "B",
  "dimensions": {
    "economy":               { "score": 78.0, "indicators": { ... } },
    "structural_efficiency": { "score": 85.0, "indicators": { ... } },
    "safety":                { "score": 88.0, "indicators": { ... } },
    "sustainability":        { "score": 75.0, "indicators": { ... } }
  },
  "recommendations": [ "材料用量偏高，建议优化截面。" ]
}
```

---

### 4.5 CADDrawingTool

**调用方式**：逐字段传入（`structure_type, geometry, material, loads, constraints, units`）。

**`set_output_directory(directory, subdirectory=None)`**：PlanningFlow 在 Step 4 前调用，将输出路径指向 `output/<type>_<ts>/drawings/`。

**execute() 执行流程**：

```
1. 提取参数（structure_type 为必填，required: ["structure_type"]）
2. DrawerFactory.is_registered(structure_type) → 不通过则返回错误
3. drawer = DrawerFactory.create(structure_type)
4. 若 _custom_output_dir 存在，调用 drawer.set_output_directory()
5. drawer.generate_drawings(design) → DrawingResults
6. 构造输出 JSON（files + metadata + notes）
```

**输出 JSON**：

```json
{
  "status": "success",
  "files": {
    "plan_view":      "output/.../drawings/beam_plan.dxf",
    "elevation_view": "output/.../drawings/beam_elevation.dxf",
    "section_view":   null,
    "detail_view":    "output/.../drawings/beam_detail.dxf"
  },
  "metadata": {
    "structure_type":    "beam",
    "drawing_standard":  "GB/T 50001-2017",
    "scale":             "1:50",
    "units":             "mm",
    "generated_at":      "2026-05-01T14:30:22",
    "plan_preview":      "output/.../drawings/beam_plan_preview.png",
    "elevation_preview": "output/.../drawings/beam_elevation_preview.png"
  },
  "notes": [
    "Generated by OpenManus Structure Designer",
    "Design standard: GB/T 50001-2017",
    "Scale: 1:50",
    "Units: mm",
    "Length: 6.0 m"
  ]
}
```

> **plan_preview / elevation_preview**：`generate_drawings()` 在生成每个 DXF 后自动调用 `_convert_dxf_to_png()`（基于 ezdxf + matplotlib），将预览 PNG 路径写入 `DrawingResults.metadata`，再由 CADDrawingTool 在 metadata 中提取以 `.png` 结尾的值一并输出。

---

### 4.6 ReportTool

**调用方式（两种格式互斥）**：

| 格式 | 参数 |
|------|------|
| 格式1（推荐） | `report_data: str`，内含所有字段的完整 JSON |
| 格式2 | `design_proposal, analysis_results, evaluation_report, drawing_results, bim_results, ifc_results`（后4个可选） |

**execute() 执行流程**：

```
1. 解析输入，提取所有字段
2. 检查必填项（design_proposal + analysis_results）
3. ReporterFactory.is_registered(structure_type) → 不通过则返回 error
4. reporter = ReporterFactory.create(structure_type)
5. 若 _custom_output_dir 存在，调用 reporter.set_output_directory()
6. reporter.generate_report(design, analysis, evaluation, drawings, bim, ifc) → report_path: str
7. 返回 {status: "success", report_file: "<path>"}
```

> ReportTool 本身只返回报告文件路径。可视化文件路径由 VisualizationTool 分别输出，两者在 ReportGenerationAgent 的 `extract_report_results()` 中合并。

---

### 4.7 VisualizationTool

**调用方式（两种格式互斥）**：

| 格式 | 参数 |
|------|------|
| 格式1（推荐） | `visualization_data: str/dict`，内含 `design_proposal` + `analysis_results` |
| 格式2 | `design_proposal: dict, analysis_results: dict` |

**execute() 执行流程**：

```
1. 解析输入
2. VisualizerFactory.is_registered(structure_type) → 不通过则返回 error
3. visualizer = VisualizerFactory.create(structure_type)
4. 若 _custom_output_dir 存在，调用 visualizer.set_output_directory()
5. visualizer.generate_all_visualizations(design_proposal, analysis_results)
   → generate_static_visualizations()  （matplotlib → PNG）
   → generate_interactive_visualizations()  （Plotly → HTML）
6. 返回 {status: "success", visualizations: {static: {...}, interactive: {...}}}
```

**输出示例**：

```json
{
  "status": "success",
  "visualizations": {
    "static": {
      "moment_diagram":   "output/.../visualizations/moment_diagram.png",
      "shear_diagram":    "output/.../visualizations/shear_diagram.png",
      "deflection_curve": "output/.../visualizations/deflection_curve.png"
    },
    "interactive": {
      "moment_html":     "output/.../visualizations/moment_diagram.html",
      "shear_html":      "output/.../visualizations/shear_diagram.html",
      "deflection_html": "output/.../visualizations/deflection_curve.html"
    }
  }
}
```

---

### 4.8 WebAskHuman（Web 模式人机交互）

**继承**：`WebAskHuman(AskHuman)`，`name="ask_human"`，保持与 CLI 版完全相同的接口。

**注入机制**：PlanningFlow 在 `task_id` + `websocket_callback` 均存在时，调用 `_inject_web_ask_human()` 将全部 Agent 工具集中的 `ask_human` 替换为同一个 `WebAskHuman` 实例。

**execute() 两种调用模式**：

| 模式 | 参数 | 前端渲染 |
|------|------|---------|
| 结构化（推荐） | `question, options, context` | 单选按钮 + 图片展示 |
| 遗留文本（兜底） | `inquire` | 解析后提取 question/options/context |

**交互流程**：

```
1. 解析参数（结构化 / 遗留文本）
2. 构造 WebSocket 消息：{type: "ask_human", question, options, default, image_path?, context?}
3. 持久化到 Redis: ask_human_pending:{task_id}（TTL 7200s，供断线重连恢复）
4. 广播给前端
5. 轮询 Redis key "ask_human:{task_id}"（每秒一次，超时 1800s）
6. 收到答案后：
   a. 删除 ask_human:{task_id} + ask_human_pending:{task_id}
   b. 读取 current_stage:{task_id}（由 _broadcast_stage 写入）
   c. 写入 interaction_history:{task_id} Redis list（TTL 86400s）
   d. 立即广播 {type: "interaction_history", ...} 触发前端持久化
7. 返回答案字符串
```

**遗留文本解析逻辑**（`_parse_inquire`）：仅识别 `"数字 - 关键词"` 格式为 options（如 `"1 - continue"`, `"2 - optimize : 描述"`），**不**识别 `"1. 问题文本"` 格式，避免将问卷式多问题拆成 options。

---

### 4.9 实现层架构

#### 4.9.1 已支持的结构类型

| 类型标识 | 中文名 | Analyzer | Drawer | Evaluator | Reporter | Visualizer |
|---------|--------|----------|--------|-----------|---------|-----------|
| `beam` | 简支梁 | BeamAnalyzer | BeamDrawer | BeamEvaluator | BeamReporter | BeamVisualizer |
| `cantilever_beam` | 悬臂梁 | CantileverBeamAnalyzer | CantileverBeamDrawer | CantileverBeamEvaluator | BeamReporter | BeamVisualizer |
| `continuous_beam` | 连续梁 | ContinuousBeamAnalyzer | ContinuousBeamDrawer | ContinuousBeamEvaluator | BeamReporter | BeamVisualizer |
| `truss` | 桁架 | TrussAnalyzer | TrussDrawer | TrussEvaluator | TrussReporter | TrussVisualizer |
| `frame` | 框架 | FrameAnalyzer | FrameDrawer | FrameEvaluator | FrameReporter | FrameVisualizer |

> BeamReporter 同时服务于 beam / cantilever_beam / continuous_beam（Reporter 映射为 3:5）。
> BeamVisualizer 同样复用于三种梁类型。

#### 4.9.2 StructureAnalyzer（抽象基类）

```python
StructureAnalyzer (ABC)
    ├── _get_structure_type() -> str          # 抽象：返回类型标识
    ├── build_model(design: Dict) -> bool      # 抽象：OpenSeesPy 建模
    ├── analyze() -> AnalysisResults           # 抽象：执行有限元计算
    ├── check_code(results) -> Dict            # 抽象：规范校核
    ├── _validate_structure_specific(design)   # 抽象：类型特定模型验证
    ├── export_opensees_script(design, path) -> str  # 抽象：导出 Tcl 脚本
    ├── validate_design(design) -> (bool, str) # 非抽象：检查必填字段
    ├── _validate_model(design)                # 非抽象：调用 OpenSeesPy 验证节点/单元/边界
    └── run_full_analysis(design) -> Dict      # 非抽象：完整流程（validate→build→_validate→analyze→check_code）
```

**`run_full_analysis` 返回格式**：

```python
{
    "status":     "success" | "failed",
    "results":    AnalysisResults,   # dataclass 对象（非 dict）
    "code_check": { "compliant": bool, "violations": [...], "safety_factors": {...} },
    "error":      str | None
}
```

**AnalysisResults dataclass 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `max_displacement` | float | 最大位移（m） |
| `max_stress` | float | 最大应力（Pa） |
| `max_moment` | float | 最大弯矩（N·m） |
| `max_shear` | float | 最大剪力（N） |
| `displacements` | List[float] | 节点位移数组 |
| `stresses` | List[float] | 单元应力数组 |
| `moments` | List[float] | 单元弯矩数组 |
| `shears` | List[float] | 单元剪力数组 |
| `nodes` | List[List[float]] | 节点坐标列表 |
| `n_elements` | int | 单元数量 |
| `structure_type` | str | 结构类型 |
| `analysis_status` | str | `"success"` 或 `"failed"` |
| `error_message` | Optional[str] | 失败原因 |
| `geometry` | Dict | 几何参数（供可视化使用） |
| `material` | Dict | 材料参数（供可视化使用） |
| `extra` | Dict | 类型特定扩展数据（如 `ux_displacements`、`axial_forces`） |

#### 4.9.3 DesignEvaluator（抽象基类）

```python
DesignEvaluator (ABC)
    ├── evaluate_economy(design, results) -> Dict       # 抽象
    ├── evaluate_efficiency(design, results) -> Dict    # 抽象（注：方法名为 efficiency，非 structural_efficiency）
    ├── evaluate_safety(design, results) -> Dict        # 抽象
    ├── evaluate_sustainability(design, results) -> Dict # 抽象
    ├── _get_stress_utilization(design, results) -> float  # 抽象：应力利用率
    ├── _check_structure_specific_construction(...) -> List  # 抽象：构造要求检查
    ├── evaluate_comprehensive(design, results) -> Dict  # 非抽象：综合评分
    ├── evaluate_construction(design, results) -> Dict   # 非抽象：构造评分（扣分制）
    ├── _calculate_grade(score) -> str                   # 非抽象：评级
    ├── _get_deflection_utilization(design, results) -> float
    └── _get_comprehensive_utilization(design, results) -> float
```

**综合评分特殊规则**：
- 若 `code_check.compliant == False`，综合分上限强制为 60（`min(score, 60.0)`）
- 综合分 < 75 时自动生成改进建议（`recommendations`）

**各结构类型权重**（来自 `WEIGHTS_CONFIG`）：

| 类型 | safety | economy | efficiency | sustainability |
|------|--------|---------|------------|---------------|
| `beam` | 40% | 25% | 20% | 15% |
| `cantilever_beam` | 45% | 20% | 20% | 15% |
| `continuous_beam` | 40% | 25% | 20% | 15% |
| `truss` | 35% | 30% | 20% | 15% |
| `frame` | 45% | 20% | 20% | 15% |

**评分等级**：A+（≥95）/ A（90-94）/ B+（85-89）/ B（80-84）/ C+（75-79）/ C（70-74）/ D（<70）

**挠度限值**（来自 `DEFLECTION_LIMITS`）：

| 类型 | 限值 |
|------|------|
| `beam` | L/250 |
| `cantilever_beam` | L/200（最严） |
| `continuous_beam` | L/300（较严） |
| `truss` | L/250 |
| `frame` | L/300（较严） |

**构造检查扣分制**（`evaluate_construction`，初始5分）：
- minor 问题：-0.5 分
- moderate 问题：-1.0 分
- severe 问题：-2.0 分

**预警阈值**（来自 `ALERT_THRESHOLDS`，PlanningFlow `_handle_evaluation_alert` 读取）：

| 类型 | safety_severe | safety_warning | economy_severe | economy_warning |
|------|--------------|----------------|----------------|----------------|
| default（beam/continuous_beam） | 60 | 70 | 60 | 70 |
| cantilever_beam | 65 | 75 | 55 | 65 |
| frame | 65 | 75 | 55 | 65 |
| truss | 55 | 65 | 65 | 75 |

#### 4.9.4 StructureDrawer（抽象基类）

```python
StructureDrawer (ABC)
    ├── draw_plan(design) -> Optional[str]      # 抽象：平面图 DXF
    ├── draw_elevation(design) -> Optional[str] # 抽象：立面图 DXF
    ├── draw_details(design) -> Optional[str]   # 抽象：详图 DXF
    ├── generate_drawings(design) -> DrawingResults  # 非抽象：调用以上3个，自动生成 PNG 预览
    ├── set_output_directory(directory, subdirectory=None)
    └── _convert_dxf_to_png(dxf_path) -> Optional[str]  # 使用 ezdxf + matplotlib
```

**DrawingResults dataclass 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `plan_view` | Optional[str] | 平面图 DXF 路径 |
| `elevation_view` | Optional[str] | 立面图 DXF 路径 |
| `section_view` | Optional[str] | 剖面图 DXF 路径 |
| `detail_view` | Optional[str] | 详图 DXF 路径 |
| `structure_type` | str | 结构类型 |
| `drawing_standard` | str | `"GB/T 50001-2017"` |
| `scale` | str | `"1:50"` |
| `units` | str | `"mm"` |
| `generated_at` | str | ISO 格式时间戳 |
| `metadata` | Dict | 含 `plan_preview`/`elevation_preview` PNG 路径 |
| `notes` | List[str] | 包含标准、比例、尺寸等说明 |

#### 4.9.5 BaseReporter（抽象基类）

```python
BaseReporter (ABC)
    ├── generate_report(design, results, evaluation, drawings, bim, ifc) -> str  # 抽象：返回 Markdown 报告路径
    ├── set_output_directory(directory, subdirectory=None)
    └── get_structure_display_name(structure_type) -> str  # 静态方法：返回中英文名称
```

**`get_structure_display_name` 映射**：

| 类型标识 | 显示名称 |
|---------|---------|
| `beam` | 简支梁 (Simply Supported Beam) |
| `cantilever_beam` | 悬臂梁 (Cantilever Beam) |
| `continuous_beam` | 连续梁 (Continuous Beam) |
| `truss` | 桁架 (Truss) |
| `frame` | 框架 (Frame) |

#### 4.9.6 BaseVisualizer（抽象基类）

```python
BaseVisualizer (ABC)
    ├── generate_static_visualizations(design, results) -> Dict[str, str]       # 抽象：matplotlib PNG
    ├── generate_interactive_visualizations(design, results) -> Dict[str, str]  # 抽象：Plotly HTML
    └── generate_all_visualizations(design, results) -> Dict                    # 非抽象：{static, interactive}
```

---

### 4.10 工厂模式实现

所有5个工厂类（AnalyzerFactory / EvaluatorFactory / DrawerFactory / ReporterFactory / VisualizerFactory）遵循相同模式：

```python
class AnalyzerFactory:
    _registry: Dict[str, Type[StructureAnalyzer]] = {}

    @classmethod
    def register(cls, structure_type: str, analyzer_class: Type) -> None:
        """注册时校验必须继承自 StructureAnalyzer，否则 TypeError"""
        ...

    @classmethod
    def create(cls, structure_type: str) -> StructureAnalyzer:
        """未注册则 raise ValueError（含中文提示 + 可用类型列表）"""
        ...

    @classmethod
    def get_available_types(cls) -> list[str]: ...

    @classmethod
    def is_registered(cls, structure_type: str) -> bool: ...
```

> `create()` 未找到类型时**抛出 ValueError**（非返回 None）。调用方（FEAnalysisTool/EvaluationTool/CADDrawingTool）在此之前已用 `is_registered()` 过滤，工厂本身的 ValueError 作为最后一道防线。

**模块加载时自动注册**（5个工厂各自在文件末尾执行）：

```python
# analyzer_factory.py
AnalyzerFactory.register("beam", BeamAnalyzer)
AnalyzerFactory.register("cantilever_beam", CantileverBeamAnalyzer)
AnalyzerFactory.register("continuous_beam", ContinuousBeamAnalyzer)
AnalyzerFactory.register("truss", TrussAnalyzer)
AnalyzerFactory.register("frame", FrameAnalyzer)
# EvaluatorFactory / DrawerFactory / ReporterFactory / VisualizerFactory 同理
```

---

### 4.11 ModelVisualizer（结构模型预览）

`ModelVisualizer` 位于 `structural_app/tool/visualizers/model_visualizer.py`，**与 VisualizerFactory 无关**，专门用于 FEAnalysisAgent 的可视化确认步骤（Step 2 AH1）。

```python
class ModelVisualizer:
    """全部为 @staticmethod，不使用工厂模式"""
    visualize_beam(design, output_path) -> str
    visualize_cantilever_beam(design, output_path) -> str
    visualize_continuous_beam(design, output_path) -> str
    visualize_truss(design, output_path) -> str
    visualize_frame(design, output_path) -> str
```

- 使用 `matplotlib` + `Agg` 后端（非交互，适合服务器/CI 环境）
- 每个方法绘制结构示意图（梁体/节点/支座/荷载箭头/标注），保存为 PNG
- 图中包含：跨度标注、截面尺寸、支座类型、荷载大小，供工程师目视确认模型是否与需求一致

---

### 4.12 BIM 导出

| 导出器 | 类名 | 格式 | 依赖 |
|--------|------|------|------|
| IFC 导出 | IfcExporter | IFC2X3 / IFC4 | ifcopenshell |
| Speckle 推送 | SpeckleExporter | Speckle 平台 URL | specklepy |

两者均由 **PlanningFlow 在 Step 5.1 直接调用**（无 Agent 参与）。触发条件：
- **IFC**：`config.toml` 中 `[ifc] enabled = true`
- **Speckle**：`config.toml` 中 `[speckle]` 有 `token` 且有 `project_id`

`report_only` 模式下两者均跳过。用户可通过 `_ask_web_or_cli()` 选择不导出（默认"否"）。

---

### 4.13 RAG 知识库

```
RAGEngine
    ├── 向量存储：ChromaDB（本地持久化）
    ├── 嵌入模型：text-embedding-ada-002
    └── 用途：设计规范语义检索，增强 Evaluator 的规范引用能力
```

`RAGEnhancedMixin` 可混入任意 Evaluator 子类，提供 `enhance_construction_issue_with_citation(issue, structure_type)` 方法——在 `evaluate_construction()` 发现构造问题时，自动查询相关规范条文并附在 `issue` 的 `citation` 字段中。

---

## 5. 工作流程与数据流

### 5.1 整体工作流程

```
用户输入（自然语言）
    ↓
PlanningFlow（自定义编排器，全程广播 WebSocket 进度）
    ↓
[Step 1] StructuralDesignAgent
    ├── WebAskHuman 收集缺失参数（Web）/ AskHuman（CLI）
    ├── LLM 生成设计方案
    └── 输出 DesignProposal（含 type 字段）
    ↓
[Step 1.5] PlanningFlow 预检
    └── AnalyzerFactory.is_registered(type) 不通过 → 返回 failed，终止
    ↓
[Step 2] FEAnalysisAgent
    └── FEAnalysisTool → AnalyzerFactory → 具体 Analyzer（OpenSeesPy）→ 规范校核
    ↓
规范校核决策点（compliant == false 时触发，由 PlanningFlow 询问用户）
    ├── 手动改进 → LLM 提出改进建议 → 修改设计参数 → 重新分析（循环，上限10轮）
    ├── 自动优化 → PlanningFlow 自动迭代调整参数 → 重新分析（循环，上限10轮）
    └── 终止    → 返回 terminated
    ↓
[Step 3] EvaluationAgent
    └── EvaluationTool → EvaluatorFactory → 具体 Evaluator → 4维度评分 + 综合评分
    ↓
评估预警决策点（安全性/经济性得分过低 或 综合分 < 70 时触发，由 PlanningFlow 询问用户）
    ├── continue     → 不做任何修改，直接继续
    ├── optimize     → _parallel_optimization：生成多个备选方案 → 用户选择最优方案
    ├── report_only  → skip_drawing = True，跳过 Step 4，直接生成报告
    └── terminate    → 返回 terminated
    ↓
[Step 4] CADDrawingAgent（skip_drawing == True 时跳过）
    └── CADDrawingTool → DrawerFactory → 具体 Drawer（ezdxf）→ DXF 图纸文件
    ↓
[Step 5.1] BIM/IFC 导出（由 PlanningFlow 直接调用，skip_drawing == True 时跳过）
    ├── config.toml 中未配置 → 跳过
    └── 已配置 → WebAskHuman 询问用户是否导出
            ├── Speckle 导出 → SpeckleExporter → 推送到 Speckle 平台
            └── IFC 导出    → IfcExporter → IFC 文件
    ↓
[Step 5.2] ReportGenerationAgent
    └── ReportTool → ReporterFactory → 具体 Reporter → Markdown 报告
    ↓
完整设计方案（报告 + 图纸 + 可选 BIM）
```

### 5.2 数据流转示例

以简支梁设计为例，展示从用户输入到最终报告的完整数据流转过程。

---

**用户输入**
```
"我需要设计一根6米跨度的简支梁，承受10kN/m的均布荷载"
```

---

**Step 1 — StructuralDesignAgent**

PlanningFlow 广播：
```json
{ "type": "stage", "stage": "design_proposal", "status": "started", "message": "开始生成设计方案" }
```

Agent 发现参数不全，通过 WebAskHuman 向用户提问（Web 模式下推送到前端）：
```
请问梁的截面尺寸（宽×高）是多少？材料是混凝土还是钢材？
```

用户回答后，LLM 生成设计方案并写入 `self.results["design_proposal"]`：
```json
{
  "type": "beam",
  "geometry": { "length": 6.0, "width": 0.3, "height": 0.6, "n_elements": 20 },
  "material": { "E": 30000000000, "nu": 0.2, "fy": 235000000, "material_name": "Q235" },
  "loads": { "distributed": [{ "q": -10000, "direction": "y" }], "point": [] },
  "constraints": { "support_type": "simply_supported" }
}
```

PlanningFlow 广播（触发前端更新右侧设计方案状态栏）：
```json
{
  "type": "stage", "stage": "design_proposal", "status": "completed",
  "data": { "type": "beam", "geometry": { "length": 6.0, "width": 0.3, "height": 0.6 }, "material": { "material_name": "Q235" } }
}
```

同时创建本次运行的输出目录：`output/beam_20260501_143022/`

---

**Step 2 — FEAnalysisAgent**

PlanningFlow 广播：
```json
{ "type": "progress", "stage": "fe_analysis", "sub_stage": "building_model", "message": "正在构建有限元模型..." }
```

FEAnalysisTool → `AnalyzerFactory.create("beam")` → `BeamAnalyzer`，调用 OpenSeesPy 建模并求解，写入 `self.results["analysis_results"]`：
```json
{
  "status": "success",
  "results": {
    "max_displacement_mm": 12.4,
    "max_stress_MPa": 187.3,
    "max_moment_kNm": 45.0,
    "max_shear_kN": 30.0
  },
  "code_check": {
    "compliant": false,
    "violations": ["挠度超限: 12.4mm > 允许值 12.0mm"],
    "safety_factors": { "stress": 1.25, "deflection": 0.97 }
  }
}
```

`compliant: false` → PlanningFlow 询问用户处理方式（三选一）：
```
有限元分析未通过规范校核，请选择处理方式：
  1. 手动改进 - 由 LLM 提出改进建议并重新分析
  2. 自动优化 - 系统自动迭代优化（最多10轮）
  3. 终止工作流
```

用户选择"手动改进"，LLM 建议将梁高从 0.6m 增至 0.65m，重新分析后：
```json
{
  "status": "success",
  "results": { "max_displacement_mm": 9.8, "max_stress_MPa": 160.2, ... },
  "code_check": { "compliant": true, "violations": [], "safety_factors": { "stress": 1.47, "deflection": 1.22 } }
}
```

---

**Step 3 — EvaluationAgent**

EvaluationTool → `EvaluatorFactory.create("beam")` → `BeamEvaluator`，写入 `self.results["evaluation_report"]`：
```json
{
  "status": "success",
  "comprehensive_score": 76.5,
  "grade": "B+",
  "dimensions": {
    "safety":                { "score": 84.0, "indicators": { "min_safety_factor": 1.22, "stress_utilization": 0.68 } },
    "economy":               { "score": 72.0, "indicators": { "stress_utilization": 0.68, "material_usage_index": 1.18 } },
    "structural_efficiency": { "score": 74.0, "indicators": { "average_utilization": 0.65, "utilization_uniformity": 0.91 } },
    "sustainability":        { "score": 71.0, "indicators": { "carbon_emission_kg": 520.0, "recyclability_ratio": 0.95 } }
  },
  "recommendations": ["梁高偏大，可考虑适当减小以提高经济性"]
}
```

PlanningFlow 广播（触发前端雷达图渲染）：
```json
{
  "type": "stage", "stage": "evaluation", "status": "completed",
  "data": { "comprehensive_score": 76.5, "grade": "B+", "safety_score": 84.0, "economy_score": 72.0, ... }
}
```

综合评分 76.5 > 70（合格线），且安全性/经济性得分均高于各维度预警阈值，无预警触发，继续执行。

---

**Step 4 — CADDrawingAgent**

CADDrawingTool → `DrawerFactory.create("beam")` → `BeamDrawer`，调用 ezdxf 生成 DXF 文件，写入 `self.results["drawing_results"]`：
```json
{
  "status": "success",
  "files": {
    "elevation": "output/beam_20260501_143022/drawings/beam_elevation_20260501_143022.dxf",
    "details":   "output/beam_20260501_143022/drawings/beam_details_20260501_143022.dxf"
  }
}
```

---

**Step 5.1 — BIM/IFC 导出（PlanningFlow 直接调用）**

config.toml 中未配置 Speckle/IFC，跳过此步骤。

---

**Step 5.2 — ReportGenerationAgent**

ReportTool → `ReporterFactory.create("beam")` → `BeamReporter`，整合 DesignProposal + AnalysisResults + EvaluationReport + DrawingResults，生成 Markdown 报告，同时调用 VisualizationTool 生成静态/交互式图表，写入 `self.results["report_results"]`：
```json
{
  "status": "success",
  "report_file": "output/beam_20260501_143022/reports/beam_design_report_20260501_143022.md",
  "visualizations": {
    "static": { "displacement": "...png", "stress": "...png" },
    "interactive": { "displacement": "...html" }
  }
}
```

---

**PlanningFlow 最终返回**（写入数据库，供前端下载）：
```json
{
  "status": "success",
  "design_proposal":  { "type": "beam", ... },
  "analysis_results": { "status": "success", "code_check": { "compliant": true }, ... },
  "evaluation_report":{ "comprehensive_score": 76.5, "grade": "B+", ... },
  "drawing_results":  { "files": { "elevation": "...", "details": "..." } },
  "report_results":   { "report_file": "output/beam_20260501_143022/reports/..." }
}
```

---

### 5.3 Agent 间通信机制

#### 1. PlanningFlow 显式数据传递（主要机制）

Agent 之间**不直接传递数据**。PlanningFlow 是数据流的中枢：每个 Agent 执行完毕后，PlanningFlow 从其返回的文本中解析 JSON，写入 `self.results` 字典，再将所需字段序列化为 JSON 字符串作为下一个 Agent 的输入请求。

```python
# 每个阶段的数据提取与传递模式
design_result = await self.design_agent.run(user_request)
self.results["design_proposal"] = self._extract_design_proposal(design_result)  # 正则解析JSON

analysis_request = json.dumps(self.results["design_proposal"])                  # 显式序列化
analysis_result  = await self.analysis_agent.run(analysis_request)
self.results["analysis_results"] = self._extract_analysis_results(analysis_result)

# EvaluationTool 直接调用（绕过 LLM）
eval_result = await _evaluation_tool_instance.execute(
    design_proposal=self.results["design_proposal"],
    analysis_results=self.results["analysis_results"]
)
self.results["evaluation_report"] = json.loads(eval_result.output)
```

注意：EvaluationTool 由 PlanningFlow **直接调用**，不经过 EvaluationAgent 的 LLM，避免 LLM 解析开销。CADDrawingTool 也有类似的直接调用路径（优先走直接调用，失败时降级到 Agent）。

#### 2. Agent 响应文本的 JSON 解析（三层 fallback）

由于 Agent 的 LLM 响应是自由文本，PlanningFlow 用正则逐层兜底提取 JSON：

```
Pattern 1: 匹配工具调用输出块  "fe_analysis ... executed: { ... }"
    ↓ 失败
Pattern 2: 匹配文本中的平衡 JSON 对象（含 "status" 字段）
    ↓ 失败
Pattern 3: 返回 None（由 PlanningFlow 处理异常分支）
```

对于 DesignProposal，额外匹配含 `"type"` 字段的 JSON（而非 `"status"`）。报告生成的结果则分别提取 `visualization` 和 `report_file` 两部分再合并。

#### 3. 传给下一阶段的请求格式

| 阶段 | 请求内容 |
|------|---------|
| FEAnalysisAgent | `json.dumps(design_proposal)` |
| CADDrawingAgent | `json.dumps({design_proposal, analysis_results})` |
| ReportGenerationAgent | `json.dumps({design_proposal, analysis_results（裁剪大数组）, analysis_results_full, evaluation_report, drawing_results, bim_results, ifc_results, skip_visualization})` |

> 报告请求中 `analysis_results` 的 `detailed_results` 内大数组（displacements、stresses、moments 等）会被裁剪，但同时保留一份完整的 `analysis_results_full` 供可视化工具使用，避免超出 LLM 工具参数长度限制。

#### 4. WebSocket 进度推送

PlanningFlow 在每个阶段的关键节点调用 `_broadcast_stage()` / `_broadcast_progress()`，通过 WebSocket 向前端推送两类消息：

```json
// 阶段事件（触发前端状态栏更新）
{ "type": "stage", "stage": "fe_analysis", "status": "completed",
  "data": { "max_stress_MPa": 187.3, "compliant": true, ... } }

// 进度事件（触发前端进度条更新）
{ "type": "progress", "stage": "fe_analysis", "current": 3, "total": 4,
  "sub_stage": "solving", "progress": 0.75, "message": "正在求解位移和内力..." }
```

同时，`_broadcast_stage()` 会将当前阶段名同步写入 Redis（`current_stage:{task_id}`），供 WebAskHuman 读取，用于标记交互记录属于哪个阶段。

#### 5. WebAskHuman 人机交互（Web 模式）

当 Agent 需要询问用户时，WebAskHuman 取代 AskHuman，流程如下：

```
Agent 调用 WebAskHuman.execute(question, options, context)
    ↓
① 通过 WebSocket 推送 ask_human 消息到前端（含问题、选项、图片路径等）
② 同时将消息写入 Redis（ask_human_pending:{task_id}，TTL 2小时，供断线重连恢复）
    ↓
③ 轮询 Redis 键 ask_human:{task_id}，每秒一次，超时 30 分钟
    ↓
④ 前端用户作答后，POST /api/design/{task_id}/respond 将答案写入 Redis
    ↓
⑤ WebAskHuman 读到答案，删除键，将交互记录追加到 Redis list（interaction_history:{task_id}）
⑥ 立即广播完整历史（type: "interaction_history"）触发数据库持久化
    ↓
返回答案字符串给 Agent
```

---

## 6. 扩展性设计

### 6.1 添加新结构类型的步骤

**示例：添加拱结构（arch）**

1. 实现 `ArchAnalyzer`（继承 `StructureAnalyzer`，使用 OpenSeesPy 建模）
2. 实现 `ArchDrawer`（继承 `StructureDrawer`，使用 ezdxf 绘图）
3. 实现 `ArchEvaluator`（继承 `DesignEvaluator`，实现4维度评估）
4. 在工厂类中注册：
   ```python
   AnalyzerFactory.register("arch", ArchAnalyzer)
   DrawerFactory.register("arch", ArchDrawer)
   EvaluatorFactory.register("arch", ArchEvaluator)
   ReporterFactory.register("arch", ArchReporter)  # 或复用已有 Reporter
   ```
5. Agent 代码无需任何修改

### 6.2 架构验收标准

- ✅ Agent 代码中不出现 `if type == "beam"` 这样的硬编码
- ✅ 能够在不修改 Agent 的前提下添加新结构类型
- ✅ 所有类型特定的逻辑封装在 Tool 实现层
- ✅ 工厂模式和路由机制正常工作

---

## 7. 总结

### 7.1 核心设计原则

1. **LLM 层面通用**：Agent 不针对特定结构类型，LLM 具备全部设计知识
2. **类型区分在 Tool 层**：通过 `type` 字段 + 工厂模式动态路由
3. **职责分离**：PlanningFlow 编排 → Agent 协调 → Tool 路由 → 实现层执行
4. **Web/CLI 双模式**：AskHuman（CLI）与 WebAskHuman（Web）无缝切换

### 7.2 架构优势

- **高扩展性**：添加新结构类型无需修改 Agent 代码
- **低耦合**：Agent、Tool、实现层职责清晰
- **易维护**：抽象基类定义标准接口，工厂统一管理
- **实时交互**：WebSocket 进度推送 + Redis 答案轮询，支持 Web 端人机协同

---

**文档版本**：v2.1
**创建日期**：2026-02-07
**最后更新**：2026-05-01

**更新日志**：
- v2.1 (2026-05-01): 根据代码审查修正若干不准确描述：补充 Plotly 交互式可视化；修正 3.1/3.7 中 EvaluationAgent 被绕过、ReportGenerationAgent 不负责 BIM 导出的事实；修正 4.1 EvaluationTool/CADDrawingTool 由 PlanningFlow 直接调用；修正 4.4.2 Analyzer 方法签名（build_model 返回 bool，analyze 返回 AnalysisResults dataclass）；修正 4.6 BIM 导出调用位置为 PlanningFlow Step 5.1；修正 5.2 评估预警阈值为综合分 < 70；修正 5.2 数据流示例中 BIM 导出与报告生成的顺序。
- v2.0 (2026-05-01): 根据实际代码全面更新。补充已实现的全部结构类型；补充 Reporter 层；更新 BIM 导出为已实现状态；补充 RAG 知识库；补充 WebAskHuman 机制；明确 PlanningFlow 为自定义实现；更新文档状态为"已实现"。
- v1.1 (2026-02-10): 添加4.5节"导出接口设计"
- v1.0 (2026-02-07): 初始版本
