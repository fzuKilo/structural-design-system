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
