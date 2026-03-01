---
name: structural-design-system-patterns
description: Coding patterns extracted from structural-design-system repository
version: 1.0.0
source: local-git-analysis
analyzed_commits: 200
---

# Structural Design System Patterns

## Commit Conventions

This project uses **Conventional Commits** with the following prefixes:

| Prefix | Purpose | Examples |
|--------|---------|----------|
| `feat:` | New features | `feat: 实现FEAnalysisAgent`, `feat: 添加单位支持优化` |
| `fix:` | Bug fixes | `fix: 修复标注显示值为实际值100倍的问题`, `fix: 修复循环模式中的变量作用域问题` |
| `docs:` | Documentation updates | `docs: 更新开发日志和技术决策`, `docs: 添加结构类型扩展计划` |
| `refactor:` | Code refactoring | `refactor: 重命名 app → structural_app` |
| `test:` | Test-related changes | `test: 添加ezdxf CAD绘图测试脚本` |
| `chore:` | Maintenance tasks | `chore: 初始化项目结构` |

**Commit message format**: `<type>: <description>`

## Code Architecture

```
structural-design-system/
├── structural_app/              # Main application package
│   ├── agent/                   # LLM agents (one file per agent)
│   │   ├── __init__.py
│   │   ├── structural_design_agent.py    # Phase 6: LLM-based design proposal
│   │   ├── fe_analysis_agent.py          # Phase 7: Finite element analysis
│   │   ├── cad_drawing_agent.py          # Phase 8: CAD drawing generation
│   │   ├── evaluation_agent.py           # Phase 9: Design quality evaluation
│   │   └── report_generation_agent.py    # Phase 10: Report generation
│   ├── tool/                    # Tools and utilities
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── fe_analysis_tool.py           # FEA integration with Ansys MAPDL
│   │   ├── cad_drawing_tool.py           # CAD drawing with ezdxf
│   │   ├── evaluation_tool.py            # Design evaluation (Phase 9)
│   │   ├── report_tool.py                # Report generation (Phase 10)
│   │   ├── visualization_tool.py         # PNG/HTML visualization (Phase 10)
│   │   ├── analyzers/                    # Structure analysis logic
│   │   │   ├── __init__.py
│   │   │   ├── base_analyzer.py
│   │   │   ├── beam_analyzer.py
│   │   │   └── analyzer_factory.py
│   │   ├── drawers/                      # CAD drawing drawers
│   │   │   ├── __init__.py
│   │   │   ├── base_drawer.py
│   │   │   ├── beam_drawer.py
│   │   │   └── drawer_factory.py
│   │   ├── validators/                   # Code compliance validation
│   │   │   ├── __init__.py
│   │   │   ├── base_validator.py
│   │   │   └── beam_validator.py
│   │   ├── evaluators/                   # Design quality evaluation
│   │   │   ├── __init__.py
│   │   │   ├── base_evaluator.py
│   │   │   ├── beam_evaluator.py
│   │   │   └── evaluator_factory.py
│   │   ├── reporters/                    # Report generation
│   │   │   ├── __init__.py
│   │   │   ├── base_reporter.py
│   │   │   ├── beam_reporter.py
│   │   │   └── reporter_factory.py
│   │   └── visualizations/               # Visualization generation
│   │       ├── __init__.py
│   │       ├── base_visualizer.py
│   │       ├── beam_visualizer.py
│   │       └── visualizer_factory.py
│   ├── utils/                              # Utility functions
│   │   └── __init__.py
│   └── planning_flow.py                  # Phase 10: Agent workflow orchestration
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_*.py                          # Unit tests
│   └── integration/                       # Integration tests
│       ├── __init__.py
│       ├── test_design_agent_integration.py
│       ├── test_stage7_integration.py
│       ├── test_stage8_integration.py
│       └── test_stage8_noninteractive.py
├── docs/                        # Documentation
│   ├── agent_architecture.md              # Agent architecture design
│   ├── COLLABORATION.md                   # Team collaboration guide
│   ├── CURRENT_TASK.md                    # Current task tracking
│   ├── DEV_LOG.md                         # Development log
│   ├── TECH_DECISIONS.md                  # Technical decisions record
│   ├── INTEGRATION_TEST_PLAN.md           # Integration test plan
│   ├── SETUP_GUIDE.md                     # Setup instructions
│   ├── CLAUDE_GUIDE.md                    # Claude AI guide
│   ├── DAILY_WORKFLOW.md                  # Daily workflow
│   ├── how_to_add_new_structure_type.md   # Extension guide
│   └── 阶段4完成报告.md                    # Phase 4 report (Chinese)
├── main.py                      # Entry point
├── config.toml.example          # Configuration template
├── requirements.txt
└── README.md
```

### Package Naming Convention

- **Main package**: `structural_app` (NOT `app` - resolved namespace conflict)
- **Agents**: `structural_app.agent.*` (one class per file)
- **Tools**: `structural_app.tool.*` (feature-based organization)
- **Test files**: `tests/test_*.py` and `tests/integration/test_*.py`

## Workflows

### Adding a New Structure Type

See `docs/how_to_add_new_structure_type.md` for detailed steps:

1. Create analyzer in `structural_app/tool/analyzers/`
2. Add to `analyzer_factory.py`
3. Create drawer in `structural_app/tool/drawers/`
4. Add to `drawer_factory.py`
5. Update validators in `structural_app/tool/validators/`
6. Update documentation

### Adding a New Agent

1. Create agent file: `structural_app/agent/<agent_name>_agent.py`
2. Register in `structural_app/agent/__init__.py`
3. Add integration tests: `tests/integration/test_stage*_integration.py`
4. Update `docs/COLLABORATION.md` with agent interface
5. Update `docs/agent_architecture.md` with new agent

### Agent-to-Agent Integration (Phase 7+)

1. Define interface contract in `docs/INTERFACE_CONTRACT.md`
2. Implement output validation in the calling agent
3. Add integration tests with real LLM calls
4. Test error handling and fallback scenarios

### Unit Testing Pattern

```python
# tests/test_<module>.py
import pytest
from structural_app.<module> import <ClassName>

def test_<scenario>():
    # Arrange
    # Act
    # Assert
    pass
```

### Integration Testing Pattern

```python
# tests/integration/test_stage*_integration.py
import pytest

def test_<agent>_integration():
    """Test agent integration with real LLM and downstream agents"""
    # Test full workflow with actual API calls
    pass
```

### Development Workflow

1. **Daily start**: Update `docs/CURRENT_TASK.md` with today's tasks
2. **During development**: Log changes in `docs/DEV_LOG.md`
3. **Technical decisions**: Record in `docs/TECH_DECISIONS.md`
4. **Daily end**: Update task status and plan for tomorrow

## Testing Patterns

### Test Organization

| Test Type | Location | Coverage |
|-----------|----------|----------|
| Unit tests | `tests/test_*.py` | Individual classes/functions |
| Integration tests | `tests/integration/` | Agent workflows |
| Feature tests | `tests/test_*_tool.py` | Tool functionality |
| Visualization | `tests/test_*_visualization.py` | Plot/graphics output |

### Test Requirements

- **pytest** as test runner
- **pytest-cov** for coverage (target: 80%+)
- **pytest-asyncio** for async tests

### Test Naming Conventions

- Unit test files: `test_<module>.py`
- Integration test files: `test_stage*_integration.py`
- Test functions: `test_<what_is_tested>[_<scenario>]`

## Dependencies

### Core Libraries

| Category | Package | Purpose |
|----------|---------|---------|
| Framework | OpenManus | Agent framework |
| FEA | ansys-mapdl-core | Ansys finite element analysis |
| Math | numpy, scipy | Numerical computations |
| CAD | ezdxf | AutoCAD DXF drawing |
| LLM | openai | Language model integration |
| Data | pandas, pydantic | Data validation and processing |
| Visualization | matplotlib, plotly | Plotting and visualization |
| Testing | pytest, pytest-cov | Testing framework |

### Code Quality Tools

- **black**: Code formatting
- **flake8**: Style checking
- **mypy**: Type checking

## Configuration

### Environment Setup

```bash
# 1. Clone repository
git clone https://github.com/Lin-0408-Yiran/structural-design-system.git
cd structural-design-system

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp config.toml.example config.toml
# Edit config.toml with API keys
```

### Configuration File

- Template: `config.toml.example`
- Local config: `config.toml` (gitignored)

## Technical Decisions

### Agent Architecture (Phase 5)

- **Separate agents** for each major responsibility:
  - `StructuralDesignAgent`: LLM-based design proposal
  - `FEAnalysisAgent`: Finite element analysis and verification
  - `CADDrawingAgent`: CAD drawing generation

### Error Handling Strategy

- **Phase 7+**: Use `AskHuman` tool for complex failures
- **FE Analysis**: Cycle mode with automatic retry and human intervention
- **LLM parsing**: Multiple regex patterns for robust JSON extraction

### Unit Support

- Add `units` field to all design parameters
- Support metric (mm, kN, MPa) and imperial units
- Automatic unit conversion in validators

## Extension Guidelines

### Adding New Validators

1. Create `structural_app/tool/validators/<name>_validator.py`
2. Implement `BaseValidator` subclass
3. Register in `structural_app/tool/validators/__init__.py`

### Adding New Analyzers

1. Create `structural_app/tool/analyzers/<name>_analyzer.py`
2. Implement `BaseAnalyzer` subclass
3. Register in `analyzer_factory.py`
4. Update `how_to_add_new_structure_type.md`

### Adding New Evaluators

1. Create `structural_app/tool/evaluators/<name>_evaluator.py`
2. Implement `DesignEvaluator` abstract base class
3. Implement 4 evaluation methods: `evaluate_economy()`, `evaluate_efficiency()`, `evaluate_safety()`, `evaluate_sustainability()`
4. Register in `evaluator_factory.py`
5. Update `how_to_add_new_structure_type.md`

### Adding New Reporters

1. Create `structural_app/tool/reports/<name>_reporter.py`
2. Implement `BaseReporter` subclass with report template
3. Implement report sections: engineering info, design proposal, FEA results, evaluation, recommendations
4. Register in `reporter_factory.py`
5. Update `how_to_add_new_structure_type.md`

### Adding New Visualizers

1. Create `structural_app/tool/visualizations/<name>_visualizer.py`
2. Implement `BaseVisualizer` subclass
3. Implement visualization methods: moment diagram, shear diagram, deflection diagram
4. Support both static (PNG) and interactive (HTML) output
5. Register in `visualizer_factory.py`
6. Update `how_to_add_new_structure_type.md`

### 4-Dimensional Evaluation System

**EvaluationDimensions**:
- **Economy** (25%): Material usage, cost efficiency, construction complexity
- **Structural Efficiency** (25%): Stress utilization, uniformity, redundancy
- **Safety** (30%): Safety factors, deflection margin, code compliance
- **Sustainability** (20%): Carbon emissions, recyclability

**Scoring Scale**: A+ (≥95), A (90-94), B+ (85-89), B (80-84), C+ (75-79), C (70-74), D (<70)

**Recommendations**: Auto-generated when comprehensive score < 75

---

## Development Stages (开发阶段)

This project follows a 18-stage development plan from the OpenManus framework:

### Core Functionality (阶段0-13)

| Stage | Name | Status |
|-------|------|--------|
| 0 | 环境准备 | ✅ |
| 1 | 有限元分析测试 (OpenSeesPy) | ✅ |
| 2 | CAD绘图测试 (ezdxf) | 🔄 |
| 3-4 | 工具架构 (抽象基类 + 工厂模式) | ✅ |
| 5 | 架构设计 (5个Agent + PlanningFlow) | ✅ |
| 6-10 | Agent实现 (Design/Analysis/Evaluation/Drawing/Report) | ✅ |
| 10 | 端到端测试 (简支梁) | ✅ |
| 10.5 | 架构验证 (添加悬臂梁) | ⏳ |
| 11 | 规范验证 | ✅ |
| 11.5 | 设计评估系统 (4维度量化评分) | ✅ |
| 12 | 报告生成系统 | ✅ |
| 12.5 | 可视化系统 (PNG/HTML) | ✅ |
| 13 | 增强功能 (RAG知识库) | ⏳ |
| 14 | PlanningFlow JSON提取优化 | ✅ |

### Web Interface (阶段14-18)

| Stage | Name |
|-------|------|
| 14 | Web界面设计 | ⏳ |
| 15 | 后端API (FastAPI) | ⏳ |
| 16 | 前端开发 | ⏳ |
| 17 | 实时通信 (WebSocket) | ⏳ |
| 18 | Web端到端测试 | ⏳ |

---

## Core Architecture Principles (核心架构理念)

### Generic Architecture Design (通用架构设计)

**Key Principle**: LLM层不需要区分结构类型，类型区分仅在Tool层处理。

```
PlanningFlow（任务编排）
    ↓
Agent层（通用，协调）← 不硬编码结构类型
    ↓ 传递设计方案（含type字段）
Tool层（通用，路由功能）← 根据type动态路由
    ↓
实现层（类型特定）
    - BeamAnalyzer / FrameAnalyzer / TrussAnalyzer
    - BeamDrawer / FrameDrawer / TrussDrawer
    - BeamEvaluator / FrameEvaluator / TrussEvaluator
```

### Must-Avoid (禁止事项)

- ❌ Agent中不得出现 `if type == "beam"` 这样的硬编码
- ❌ 添加新结构类型时不应修改Agent代码
- ❌ 类型特定的逻辑必须封装在Tool实现层

### Key Components (关键组件)

| Component | File | Purpose |
|-----------|------|---------|
| Abstract Base Class | `*_analyzer.py` (base) | 定义通用接口 |
| Concrete Implementation | `*_analyzer.py` (beam) | 具体结构类型实现 |
| Factory | `*_factory.py` | 根据type动态创建对象 |
| Tool | `*_tool.py` | 封装Agent可调用的接口 |

---

## Technology Stack (技术栈)

### Core Framework
- **OpenManus**: 多智能体协作框架
- **Python 3.12+**: 开发语言

### Engineering Computation
- **OpenSeesPy**: 开源有限元分析库 (已采用)
- **PyMAPDL**: Ansys Python接口 (备选)
- **NumPy/SciPy**: 辅助计算

### Visualization
- **matplotlib**: 静态云图 (PNG/JPG)
- **Plotly**: 交互式云图 (HTML)

### CAD
- **ezdxf**: 纯Python DXF生成 (推荐)
- **PyAutoCAD**: AutoCAD COM接口 (备选)

### Knowledge Base
- **LangChain**: RAG实现
- **ChromaDB**: 向量数据库

### Web Development
- **快速方案**: Gradio
- **完整方案**: FastAPI + React + WebSocket

---

*Generated from 200 commits of structural-design-system repository*
*Development plan source: OpenManus开发规划2.4.md*
