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

### 阶段0：环境准备（一起完成，1天）
- 两人一起搭建环境
- 确定代码规范

### 阶段1-2：技术验证（并行，2-3天）
- **人员A**: PyMAPDL集成测试
- **人员B**: CAD绘图测试

### 阶段3-4：工具架构（并行，3-4天）
- **人员A**: Ansys工具架构 (`feature/ansys-tool`)
- **人员B**: CAD工具架构 (`feature/cad-tool`)
- ⚠️ 第1天：一起讨论抽象基类接口

### 阶段5：架构设计（一起完成，1-2天）
- 两人一起设计架构
- 绘制UML类图

### 阶段6-8：Agent实现（并行，5-7天）
- **人员A**: DesignAgent + AnalysisAgent (`feature/design-analysis-agents`)
- **人员B**: DrawingAgent + EvaluationAgent骨架 (`feature/drawing-evaluation-agents`)
- ⚠️ 每2天：代码审查

### 阶段9：MainAgent协调器（人员A，2-3天）
- **人员A**: MainCoordinatorAgent (`feature/main-coordinator`)
- **人员B**: 优化之前的代码或准备下一阶段

### 阶段10：端到端测试（一起完成，1-2天）
- 两人一起测试和修复bug

### 阶段10.5：架构验证（并行，2-3天）
- **人员A**: CantileverBeamAnalyzer
- **人员B**: CantileverBeamDrawer

### 阶段11：规范验证（并行，3-4天）
- **人员A**: Validator架构
- **人员B**: BeamValidator实现

### 阶段11.5：设计评估（并行，2-3天）
- **人员A**: EvaluationAgent
- **人员B**: Evaluator实现 + ParetoAnalyzer

### 阶段12-13：增强功能（并行，3-4天）
- **人员A**: 报告生成
- **人员B**: RAG系统

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
