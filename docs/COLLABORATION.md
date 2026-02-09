# 协同开发指南

## Git工作流程

### 分支策略

```
main          # 稳定版本，只接受merge
├── dev       # 开发主分支
    ├── feature/design-agent      # 功能分支
    ├── feature/analysis-agent    # 功能分支
    └── ...
```

### 日常工作流程

#### 每天开始工作前

```bash
# 1. 切换到dev分支，拉取最新代码
git checkout dev
git pull origin dev

# 2. 创建/切换到自己的功能分支
git checkout -b feature/your-feature-name
# 或者如果分支已存在
git checkout feature/your-feature-name

# 3. 合并dev的最新更新
git merge dev
```

#### 开发过程中

```bash
# 频繁提交（每完成一个小功能就提交）
git add .
git commit -m "feat: 实现BeamAnalyzer的build_model方法"

# 提交信息规范：
# feat: 新功能
# fix: 修复bug
# docs: 文档更新
# refactor: 重构
# test: 测试相关
# chore: 构建/工具相关
```

#### 每天结束工作时

```bash
# 推送到远程
git push origin feature/your-feature-name
```

#### 功能完成后

```bash
# 1. 确保代码最新
git checkout dev
git pull origin dev
git checkout feature/your-feature-name
git merge dev

# 2. 合并到dev分支
git checkout dev
git merge feature/your-feature-name

# 3. 推送到远程
git push origin dev

# 4. 删除已完成的功能分支（可选）
git branch -d feature/your-feature-name
```

### 冲突处理

```bash
# 如果合并时出现冲突
git merge dev
# CONFLICT (content): Merge conflict in app/agent/design_agent.py

# 1. 打开冲突文件，手动解决
# 2. 标记为已解决
git add app/agent/design_agent.py
git commit -m "fix: 解决design_agent合并冲突"
```

## 任务分工（按阶段）

### 阶段0：环境准备 - 已完成
**状态**: ✅ 已完成
**分工**: 一起完成
- 安装 OpenManus 框架及依赖
- 安装 OpenSeesPy（有限元分析库）
- 安装 matplotlib 和 Plotly（可视化库）
- 配置 LLM API
- 确定代码规范

### 阶段1：有限元分析集成测试 - 已完成
**状态**: ✅ 已完成
**分工**: 人员A
- 编写 OpenSeesPy 测试脚本
- 实现简支梁分析示例（6m跨度，10kN/m均布荷载）
- 实现静态可视化（matplotlib）：位移云图、弯矩云图、应力云图、弯矩图
- 实现交互式可视化（Plotly）：位移、弯矩、应力云图
- 验证分析结果

**产出**:
- `tests/test_opensees_visualization.py`
- `tests/test_plotly_visualization.py`

### 阶段2：CAD绘图测试
**状态**: 🔄 进行中
**分工**: 人员B
- 编写 ezdxf 测试脚本
- 生成简单梁结构图纸（DXF格式）
- 测试节点、线条、标注等基本绘图功能

**产出**:
- `tests/test_cad_drawing.py`

### 阶段3：有限元分析工具架构 - 已完成
**状态**: ✅ 已完成
**分工**: 人员A (`feature/fe-analysis-tool`)
- 创建 `StructureAnalyzer` 抽象基类
- 创建 `AnalysisResults` 数据类
- 实现 `BeamAnalyzer`（使用 OpenSeesPy）
- 创建 `AnalyzerFactory` 工厂类
- 创建 `FEAnalysisTool`（OpenManus工具）
- 编写单元测试（16个测试全部通过）

**产出**:
- `app/tool/analyzers/base_analyzer.py`
- `app/tool/analyzers/beam_analyzer.py`
- `app/tool/analyzers/analyzer_factory.py`
- `app/tool/fe_analysis_tool.py`
- `tests/test_fe_analysis_tool.py`

**架构要点**:
- 抽象基类定义标准接口
- 工厂模式支持动态扩展
- BeamAnalyzer 封装 OpenSeesPy 调用
- 保持通用架构，避免硬编码结构类型

### 阶段4：CAD工具架构
**状态**: ⏳ 待开始
**分工**: 人员B (`feature/cad-tool`)
- 创建 `StructureDrawer` 抽象基类
- 实现 `BeamDrawer`（使用 ezdxf）
- 创建 `DrawerFactory` 工厂类
- 创建 `CADDrawingTool`（OpenManus工具）
- 编写单元测试

**产出**:
- `app/tool/drawers/base_drawer.py`
- `app/tool/drawers/beam_drawer.py`
- `app/tool/drawers/drawer_factory.py`
- `app/tool/cad_tool.py`

**注意**: 第1天与人员A讨论抽象基类接口设计

### 阶段5：架构设计
**状态**: ✅ 已完成
**分工**: 一起完成（1-2天）
- 使用 OpenManus 的 PlanningFlow 进行任务编排
- 设计5个专用Agent的职责分工：
  - **StructuralDesignAgent**（注册名：design）：参数收集、初步设计
  - **FEAnalysisAgent**（注册名：analysis）：有限元分析验算
  - **EvaluationAgent**（注册名：evaluation）：量化评估设计质量
  - **CADDrawingAgent**（注册名：drawing）：CAD图纸生成
  - **ReportGenerationAgent**（注册名：report）：报告生成与可视化
- 定义Agent间通信机制（共享上下文、数据提取）
- 定义通用数据传递格式（JSON Schema）
- 编写架构文档和扩展指南

**产出**:
- `docs/agent_architecture.md`（架构设计文档）
- `docs/how_to_add_new_structure_type.md`（扩展指南）

### 阶段6-10：Agent实现 + PlanningFlow编排（并行，7-10天）
**人员A**: StructuralDesignAgent + FEAnalysisAgent + EvaluationAgent (`feature/design-analysis-evaluation-agents`)
- 实现 `StructuralDesignAgent`（继承ToolCallAgent）
  - 参数收集（使用AskHuman工具）
  - 初步设计（调用LLM）
  - 输出DesignProposal（JSON字符串，含type字段）
- 实现 `FEAnalysisAgent`（继承ToolCallAgent）
  - 从上下文提取DesignProposal
  - 调用FEAnalysisTool进行有限元分析
  - 输出AnalysisResults（JSON字符串）
- 实现 `EvaluationAgent`（继承ToolCallAgent）
  - 从上下文提取DesignProposal和AnalysisResults
  - 调用EvaluationTool进行量化评估
  - 输出EvaluationReport（JSON字符串）
- 编写单元测试

**人员B**: CADDrawingAgent + ReportGenerationAgent + PlanningFlow (`feature/drawing-report-planning`)
- 实现 `CADDrawingAgent`（继承ToolCallAgent）
  - 从上下文提取DesignProposal
  - 调用CADDrawingTool生成图纸
  - 输出DrawingResults（JSON字符串）
- 实现 `ReportGenerationAgent`（继承ToolCallAgent）
  - 从上下文提取所有前面的输出
  - 调用VisualizationTool和ReportTool
  - 输出ReportResults（JSON字符串）
- 配置 PlanningFlow 编排完整工作流
- 实现智能决策机制（评分<75时询问用户）
- 编写单元测试

**注意**:
- 所有Agent继承自OpenManus的ToolCallAgent
- 每2天进行代码审查
- 确保Agent代码保持通用，不硬编码结构类型

### 阶段10：端到端测试
**状态**: ⏳ 待开始
**分工**: 一起完成（1-2天）
- 完整流程测试：用户输入 → 设计 → 验算 → 绘图
- 测试用例：简支梁设计（6米跨度，10kN均布荷载）
- 验证Agent协作流程
- 修复bug

### 阶段10.5：架构验证（并行，2-3天）
**人员A**: CantileverBeamAnalyzer + CantileverBeamEvaluator (`feature/cantilever-beam-analyzer-evaluator`)
- 实现 `CantileverBeamAnalyzer`（继承StructureAnalyzer）
  - 实现悬臂梁的OpenSeesPy建模逻辑（固定端边界条件）
  - 实现规范校核（挠度限值：L/250）
- 在 `AnalyzerFactory` 中注册：`AnalyzerFactory.register("cantilever_beam", CantileverBeamAnalyzer)`
- 实现 `CantileverBeamEvaluator`（继承DesignEvaluator）
- 在 `EvaluatorFactory` 中注册
- 编写单元测试

**人员B**: CantileverBeamDrawer (`feature/cantilever-beam-drawer`)
- 实现 `CantileverBeamDrawer`（继承StructureDrawer）
  - 实现悬臂梁的ezdxf绘图逻辑（固定端支座符号）
- 在 `DrawerFactory` 中注册：`DrawerFactory.register("cantilever_beam", CantileverBeamDrawer)`
- 编写单元测试

**验收标准**:
- ✅ Agent代码零修改
- ✅ 端到端测试通过（悬臂梁设计）
- ✅ 验证真正的通用性

### 阶段11：规范验证（集成到Analyzer，1-2天）
**分工**: 一起完成
- 在 `BeamAnalyzer.check_code()` 方法中完善规范校核逻辑
  - 挠度限值校核（简支梁：L/400）
  - 应力限值校核（与材料强度对比）
  - 安全系数计算
  - 违规项记录
- 返回标准化的CodeCheckResults
- 编写单元测试

**注意**:
- 规范校核直接集成到Analyzer，不需要单独的Validator架构
- 保持简单，避免过度设计
- 如果未来需要更复杂的规范验证，可以创建独立的Validator类

### 阶段11.5：设计评估（并行，2-3天）
**人员A**: EvaluationTool (`feature/evaluation-tool`)
- 创建 `DesignEvaluator` 抽象基类（`app/tool/evaluators/base_evaluator.py`）
  - 定义4个评估方法：`evaluate_economy()`, `evaluate_efficiency()`, `evaluate_safety()`, `evaluate_sustainability()`
  - 定义通用方法：`evaluate_comprehensive()`（加权综合评分）
- 创建 `EvaluatorFactory` 工厂类
- 创建 `EvaluationTool`（继承BaseTool）
- 编写单元测试

**人员B**: BeamEvaluator实现 (`feature/beam-evaluator`)
- 实现 `BeamEvaluator`（继承DesignEvaluator）
  - **经济性评估**：材料用量指数、造价效率比
  - **结构效率评估**：平均利用率、利用率均匀性
  - **安全性评估**：最小安全系数、挠度裕度
  - **可持续性评估**：碳排放量、可回收率
  - **综合评分**：加权计算（经济30% + 效率25% + 安全30% + 可持续15%）
- 在 `EvaluatorFactory` 中注册
- 编写单元测试

**注意**:
- EvaluationAgent已在阶段6-10实现，此阶段完善评估逻辑
- 综合评分（0-100分）+ 等级（A+/A/B+/B/C+/C/D）
- 评分<75时PlanningFlow智能提示用户优化

### 阶段12：结果可视化与报告（并行，3-4天）
**人员A**: VisualizationTool + ReportTool (`feature/visualization-report-tools`)
- 创建 `VisualizationTool`（继承BaseTool）
  - 基于阶段1的测试代码进行封装
  - 静态可视化：matplotlib（位移云图、弯矩云图、应力云图、弯矩图）→ PNG格式
  - 交互式可视化：Plotly（位移、弯矩、应力）→ HTML格式
  - 支持悬停查看数值、缩放、平移
- 创建 `ReportTool`（继承BaseTool）
  - 生成结构化的Markdown报告
  - 整合设计参数、验算结果、评估得分、图纸路径
  - 实现报告模板系统
- 编写单元测试

**人员B**: 导出架构 (`feature/export-architecture`)
- 创建 `DesignExporter` 抽象基类（`app/tool/exporters/base_exporter.py`）
- 实现 `JSONExporter`（当前使用）
- 预留 `IFCExporter`、`SpeckleExporter` 接口（为BIM扩展预留）
- 编写单元测试

**注意**:
- ReportGenerationAgent已在阶段6-10实现，此阶段完善可视化和报告工具
- 可视化功能独立于FEAnalysisTool，保持职责分离

### 阶段13：集成RAG知识库（并行，3-4天）
**人员A**: RAG系统搭建 (`feature/rag-system`)
- 导入工程规范文档（PDF转文本）
- 使用 LangChain 构建 RAG 系统
- 集成 ChromaDB 向量数据库

**人员B**: Agent集成 (`feature/rag-integration`)
- 在 DesignAgent 中支持规范查询
- 实现自然语言查询规范条文
- 编写测试用例

## 代码规范

### Python代码风格
- 使用Black格式化
- 遵循PEP 8
- 类型注解（Type Hints）

### 命名规范
- 类名：PascalCase (例如: `BeamAnalyzer`)
- 函数名：snake_case (例如: `build_model`)
- 常量：UPPER_CASE (例如: `MAX_ITERATIONS`)

### 文档字符串
```python
def analyze(self, design: Dict) -> Dict:
    """
    分析设计方案

    Args:
        design: 设计方案数据

    Returns:
        分析结果

    Raises:
        ValueError: 如果设计参数无效
    """
    pass
```

## 沟通协调

### 每日同步（15分钟）
- 时间：每天晚上9点
- 内容：
  - 今天完成了什么
  - 遇到什么问题
  - 明天计划做什么

### 代码审查
- 每2-3天进行一次
- 互相审查对方的代码
- 提出改进建议

### 问题讨论
- 遇到架构问题立即讨论
- 不要等到代码写完才发现不兼容

## 测试要求

- 每个模块都要写单元测试
- 测试覆盖率 > 80%
- 提交前运行测试：`pytest tests/`

## 注意事项

1. **不要直接在main分支开发**
2. **每天至少提交一次代码**
3. **提交前先pull最新代码**
4. **遇到冲突及时沟通**
5. **重要修改前先讨论**
