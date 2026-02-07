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
**状态**: ⏳ 待开始
**分工**: 一起完成（1-2天）
- 设计多Agent协作架构
- 定义Agent职责分工（MainCoordinatorAgent、StructuralDesignAgent、FEAnalysisAgent、CADDrawingAgent、EvaluationAgent）
- 定义通用数据传递格式（JSON Schema）
- 绘制UML类图
- 编写扩展指南

**产出**:
- `docs/agent_architecture.md`
- `docs/how_to_add_new_structure_type.md`

### 阶段6-8：Agent实现（并行，5-7天）
**人员A**: DesignAgent + AnalysisAgent (`feature/design-analysis-agents`)
- 实现 `StructuralDesignAgent`（参数收集、初步设计）
- 实现 `FEAnalysisAgent`（调用有限元分析工具）
- 集成 `FEAnalysisTool`
- 编写单元测试

**人员B**: DrawingAgent + EvaluationAgent骨架 (`feature/drawing-evaluation-agents`)
- 实现 `CADDrawingAgent`（调用CAD工具生成图纸）
- 实现 `EvaluationAgent` 骨架
- 编写单元测试

**注意**: 每2天进行代码审查

### 阶段9：MainAgent协调器（2-3天）
**人员A**: MainCoordinatorAgent (`feature/main-coordinator`)
- 实现 `MainCoordinatorAgent`
- 使用 PlanningFlow 编排任务流程
- 实现Agent间数据传递
- 处理异常和错误恢复

**人员B**: 优化之前的代码或准备下一阶段

### 阶段10：端到端测试
**状态**: ⏳ 待开始
**分工**: 一起完成（1-2天）
- 完整流程测试：用户输入 → 设计 → 验算 → 绘图
- 测试用例：简支梁设计（6米跨度，10kN均布荷载）
- 验证Agent协作流程
- 修复bug

### 阶段10.5：架构验证（并行，2-3天）
**人员A**: CantileverBeamAnalyzer (`feature/cantilever-beam-analyzer`)
- 实现 `CantileverBeamAnalyzer`
- 在 `AnalyzerFactory` 中注册
- 编写单元测试

**人员B**: CantileverBeamDrawer (`feature/cantilever-beam-drawer`)
- 实现 `CantileverBeamDrawer`
- 在 `DrawerFactory` 中注册
- 编写单元测试

**重要性**: 验证"通用架构"是否成功的关键阶段，确保Agent代码零修改

### 阶段11：规范验证（并行，3-4天）
**人员A**: Validator架构 (`feature/validator-architecture`)
- 创建 `CodeValidator` 抽象基类
- 创建 `ValidatorFactory` 工厂类
- 集成到 Analyzer 的 `check_code()` 方法

**人员B**: BeamValidator实现 (`feature/beam-validator`)
- 实现 `BeamValidator`（混凝土规范GB 50010）
- 硬编码关键规范条文
- 实现规范校验逻辑（应力限值、挠度限值、配筋率等）
- 编写单元测试

### 阶段11.5：设计评估（并行，2-3天）
**人员A**: EvaluationAgent (`feature/evaluation-agent`)
- 实现 `EvaluationAgent`
- 实现单方案评估功能
- 实现多方案评估 + 帕累托分析
- 集成到 MainCoordinatorAgent 工作流

**人员B**: Evaluator实现 + ParetoAnalyzer (`feature/evaluator`)
- 创建 `DesignEvaluator` 抽象基类
- 实现 `BeamEvaluator`（4维度评估：经济性、结构效率、安全性、可持续性）
- 创建 `EvaluatorFactory` 工厂类
- 实现 `ParetoAnalyzer`（可选）
- 编写单元测试

**评估体系**:
- 综合评分（0-100分）+ 等级（A+/A/B+/B/C+/C/D）
- 评分<75时智能提示用户优化

### 阶段12：结果可视化与报告（并行，3-4天）
**人员A**: 报告生成 (`feature/report-generation`)
- 创建 `VisualizationTool`（基于阶段1的测试代码）
- 集成静态可视化（matplotlib）：PNG格式，用于PDF报告
- 集成交互式可视化（Plotly）：HTML格式，用于Web查看
- 实现报告模板系统（Markdown格式）
- 整合设计参数、验算结果、评估得分、图纸路径

**人员B**: 导出架构 (`feature/export-architecture`)
- 创建 `DesignExporter` 抽象基类
- 实现 `JSONExporter`（当前使用）
- 预留 `IFCExporter`、`SpeckleExporter` 接口
- 编写单元测试

**可视化功能**:
- 位移云图、弯矩云图、应力云图、弯矩图
- 支持悬停查看数值、缩放、平移（Plotly）

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
