# Claude 辅助开发使用指南

本文档教你如何高效使用Claude进行辅助开发，解决"每天重新打开Claude就失去记忆"的问题。

---

## 🎯 核心理念

Claude每次对话都是独立的，没有记忆。但通过**文档化上下文**，可以让Claude快速了解项目状态。

---

## 📚 上下文管理系统

我们创建了4个核心文档来管理项目上下文：

### 1. docs/CURRENT_TASK.md ⭐⭐⭐⭐⭐
**最重要的文档！**
- 记录当前正在做什么
- 下一步要做什么
- 待决策的问题

### 2. docs/DEV_LOG.md ⭐⭐⭐⭐
- 每天的开发日志
- 完成了什么
- 遇到了什么问题

### 3. docs/TECH_DECISIONS.md ⭐⭐⭐
- 重要的技术决策
- 为什么这样设计
- 考虑了哪些方案

### 4. docs/DAILY_WORKFLOW.md ⭐⭐
- 每日工作流程
- 如何使用这套系统

---

## 🚀 快速开始

### 方法1：使用Claude Projects（最推荐）

**一次性设置：**

1. 访问 https://claude.ai
2. 点击左侧 `Projects`
3. 点击 `Create Project`
4. 项目名称：`structural-design-system`
5. 添加项目知识：
   - 上传 `docs/CURRENT_TASK.md`
   - 上传 `docs/DEV_LOG.md`
   - 上传 `docs/TECH_DECISIONS.md`
   - 上传 `README.md`
   - 上传 `docs/INTERFACE_CONTRACT.md`

**每天使用：**

在这个Project中开始对话：
```
早上好！请继续帮我开发。
查看 CURRENT_TASK.md 了解当前任务。
```

**优势：**
- ✅ Claude自动读取项目知识
- ✅ 不用每次重复解释
- ✅ 对话历史保存在Project中

---

### 方法2：每次对话提供上下文

**每天开始时：**

```
你好！我在开发一个基于OpenManus的结构设计系统。

项目信息：
- 路径：D:\structural-design-system
- GitHub：https://github.com/Lin-0408-Yiran/structural-design-system
- 当前分支：dev

请先阅读这些文档了解项目状态：
1. docs/CURRENT_TASK.md - 当前任务
2. docs/DEV_LOG.md - 开发日志（看最近3天）

然后告诉我今天应该继续做什么。
```

---

## 💬 与Claude对话的技巧

### 技巧1：明确告诉Claude读取文档

❌ 不好的方式：
```
帮我继续开发
```

✅ 好的方式：
```
请先阅读 docs/CURRENT_TASK.md，
了解当前任务后继续帮我开发
```

### 技巧2：提供具体的文件路径

❌ 不好的方式：
```
帮我看看Agent的代码
```

✅ 好的方式：
```
请查看 app/agent/design_agent.py，
帮我优化参数收集的逻辑
```

### 技巧3：让Claude查看Git历史

```
请运行 git log --oneline -10
查看最近的提交，了解项目进度
```

### 技巧4：分阶段开发

```
我们分3步实现这个功能：
1. 先实现数据结构
2. 再实现核心逻辑
3. 最后添加测试

现在开始第1步
```

### 技巧5：保存重要对话

```
请总结这次对话的要点，
包括我们做的决策和实现的功能，
保存到 C:\Users\Lin\Desktop\对话摘要.txt
```

---

## 📅 每日工作流程

### 早上开始工作

1. **拉取最新代码**
   ```bash
   cd D:\structural-design-system
   git pull origin dev
   ```

2. **打开VS Code**
   ```bash
   code .
   ```

3. **开始与Claude对话**
   ```
   早上好！请阅读 docs/CURRENT_TASK.md，
   继续昨天的开发任务
   ```

### 开发过程中

- 完成小功能就提交
- 遇到问题随时问Claude
- 让Claude审查代码

### 晚上结束工作

1. **让Claude更新文档**
   ```
   今天工作结束了。请帮我：
   1. 更新 docs/DEV_LOG.md
   2. 更新 docs/CURRENT_TASK.md
   3. 生成今日摘要保存到桌面
   ```

2. **提交并推送代码**
   ```bash
   git add .
   git commit -m "docs: 更新开发日志"
   git push origin dev
   ```

---

## 🎨 常见使用场景

### 场景1：开始新功能

```
我要开始实现梁结构分析功能。

请帮我：
1. 设计代码结构
2. 创建必要的文件
3. 实现基础框架
4. 更新 CURRENT_TASK.md
```

### 场景2：遇到Bug

```
我遇到了一个Bug：
- 文件：app/tool/analyzers/beam_analyzer.py:45
- 问题：计算结果不正确
- 错误信息：[粘贴错误]

请帮我分析原因并修复
```

### 场景3：代码审查

```
我完成了设计Agent的实现。
请审查 app/agent/design_agent.py，
给出改进建议
```

### 场景4：重构代码

```
app/tool/ 目录下的代码结构不太好。
请帮我重构，使其更清晰
```

### 场景5：编写测试

```
请为 app/agent/design_agent.py
编写单元测试，保存到 tests/test_design_agent.py
```

---

## ⚡ 高级技巧

### 技巧1：使用Git作为上下文

```
请查看最近的Git提交和diff：
git log --oneline -5
git diff HEAD~3..HEAD

了解最近的修改后，继续开发
```

### 技巧2：让Claude生成TODO

```
请分析当前项目状态，
生成接下来2周的开发计划，
更新到 CURRENT_TASK.md
```

### 技巧3：多轮对话规划

```
第1轮：我们先讨论设计方案
第2轮：确定方案后开始实现
第3轮：实现完成后编写测试
```

### 技巧4：保存决策过程

```
我们刚才讨论了LLM选型。
请把这个决策记录到 docs/TECH_DECISIONS.md
```

---

## 📖 文档更新策略

### 每天必须更新
- ✅ docs/CURRENT_TASK.md

### 每天建议更新
- ✅ docs/DEV_LOG.md

### 有重要决策时更新
- ✅ docs/TECH_DECISIONS.md

### 不需要频繁更新
- docs/DAILY_WORKFLOW.md
- docs/COLLABORATION.md
- docs/SETUP_GUIDE.md

---

## ⚠️ 注意事项

### 1. 文档要简洁
- ❌ 不要写太长的文档
- ✅ 只记录关键信息
- ✅ 使用列表和标题

### 2. 及时更新
- ❌ 不要积累几天才更新
- ✅ 每天结束时更新
- ✅ 重要决策立即记录

### 3. 保持一致
- ✅ 使用统一的格式
- ✅ 使用清晰的标题
- ✅ 日期格式统一

### 4. 版本控制
- ✅ 文档也要提交到Git
- ✅ 方便回溯历史
- ✅ 团队成员同步

---

## 🔧 故障排除

### 问题1：Claude不理解项目背景

**解决：**
```
请先阅读以下文档：
1. README.md - 项目概述
2. docs/CURRENT_TASK.md - 当前任务
3. docs/TECH_DECISIONS.md - 技术决策

然后告诉我你的理解
```

### 问题2：Claude给出的建议不符合项目架构

**解决：**
```
请注意：
- 我们使用OpenManus框架
- Agent在 app/agent/ 目录
- Tool在 app/tool/ 目录
- 请遵循 docs/INTERFACE_CONTRACT.md 的接口约定
```

### 问题3：忘记更新文档

**解决：**
设置每天下班前的提醒，或者让Claude提醒你

---

## 📊 效果评估

使用这套系统后，你应该能：

- ✅ Claude每天都能快速了解项目状态
- ✅ 不需要重复解释背景
- ✅ 开发效率提高
- ✅ 代码质量提升
- ✅ 团队协作更顺畅

---

## 🎓 学习资源

### Claude相关
- Claude官网：https://claude.ai
- Claude Projects文档：https://docs.anthropic.com/

### Git相关
- Git文档：https://git-scm.com/doc
- GitHub文档：https://docs.github.com/

### OpenManus相关
- OpenManus仓库：https://github.com/FoundationAgents/OpenManus

---

## 💡 最佳实践总结

1. **使用Claude Projects** - 一次设置，长期受益
2. **保持文档更新** - 每天更新CURRENT_TASK.md
3. **明确指示** - 告诉Claude读取哪些文档
4. **小步迭代** - 分阶段开发，频繁提交
5. **记录决策** - 重要决策写入TECH_DECISIONS.md

---

**祝你和Claude合作愉快！🎉**
