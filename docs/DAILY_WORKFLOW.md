# 每日工作流程指南

本文档说明如何使用开发上下文管理系统，让Claude每天都能快速了解项目状态。

---

## 📅 每天开始工作

### 步骤1：拉取最新代码

```bash
cd D:\structural-design-system
git checkout dev
git pull origin dev
```

### 步骤2：打开VS Code

```bash
code .
```

### 步骤3：开始与Claude对话

**方式A：使用Claude Projects（推荐）**

在Claude网页版的Project中开始对话：
```
早上好！请帮我继续开发。
请先阅读以下文档了解项目状态：
1. docs/CURRENT_TASK.md - 当前任务
2. docs/DEV_LOG.md - 最近的开发日志
3. docs/TECH_DECISIONS.md - 技术决策

然后告诉我今天应该做什么。
```

**方式B：普通对话**

```
你好！我在开发一个基于OpenManus的结构设计系统。
项目路径：D:\structural-design-system

请先阅读这些文档了解项目状态：
1. docs/CURRENT_TASK.md
2. docs/DEV_LOG.md

然后继续帮我开发。
```

---

## 💻 开发过程中

### 随时提交代码

完成小功能就提交：
```bash
git add .
git commit -m "feat: 实现xxx功能"
```

### 遇到问题时

告诉Claude：
```
我遇到了一个问题：[描述问题]
相关代码在：[文件路径]
```

### 需要Claude查看代码

```
请查看 app/agent/design_agent.py 文件，
帮我优化xxx功能
```

---

## 🌙 每天结束工作

### 步骤1：让Claude更新文档

```
今天的工作结束了。请帮我：
1. 更新 docs/DEV_LOG.md，记录今天的进度
2. 更新 docs/CURRENT_TASK.md，更新任务状态
3. 如果有重要决策，更新 docs/TECH_DECISIONS.md
```

### 步骤2：提交所有修改

```bash
git add .
git commit -m "docs: 更新开发日志和任务状态"
git push origin dev
```

### 步骤3：生成今日摘要（可选）

让Claude生成摘要保存到桌面：
```
请生成今天的开发摘要，包括：
1. 完成了什么
2. 遇到了什么问题
3. 明天要做什么
保存到 C:\Users\Lin\Desktop\今日开发摘要.txt
```

---

## 🔄 每周回顾

### 每周五下午

```
请帮我做本周开发回顾：
1. 查看 docs/DEV_LOG.md 本周的记录
2. 总结本周完成的功能
3. 列出下周的计划
4. 更新 docs/CURRENT_TASK.md
```

---

## 📝 文档说明

### docs/CURRENT_TASK.md
- **用途：** 记录当前正在做什么
- **更新频率：** 每天
- **重要性：** ⭐⭐⭐⭐⭐ 最重要！

### docs/DEV_LOG.md
- **用途：** 记录每天的开发日志
- **更新频率：** 每天
- **重要性：** ⭐⭐⭐⭐

### docs/TECH_DECISIONS.md
- **用途：** 记录重要的技术决策
- **更新频率：** 有重要决策时
- **重要性：** ⭐⭐⭐

---

## 💡 使用技巧

### 技巧1：使用Git历史

让Claude查看最近的提交：
```
请查看最近10条Git提交记录，了解项目进度：
git log --oneline -10
```

### 技巧2：保存对话摘要

重要对话结束时：
```
请总结这次对话的要点，保存到桌面
```

### 技巧3：使用Claude Projects

在Claude网页版创建Project，上传关键文档作为知识库

### 技巧4：代码审查

完成功能后：
```
请审查我刚写的代码，给出改进建议：
[粘贴代码或文件路径]
```

---

## ⚠️ 注意事项

1. **每天必须更新 CURRENT_TASK.md**
   - 这是最重要的上下文文档
   - Claude依赖它了解当前状态

2. **及时推送代码**
   - 每天下班前推送
   - 避免代码丢失

3. **记录重要决策**
   - 为什么这样设计？
   - 为什么选择这个方案？
   - 方便后续回顾

4. **保持文档简洁**
   - 只记录关键信息
   - 太长的文档反而难以阅读

---

## 🎯 目标

通过这套流程，实现：
- ✅ Claude每天都能快速了解项目状态
- ✅ 不需要重复解释背景
- ✅ 开发进度清晰可追踪
- ✅ 团队成员都能了解项目状态

---

## 快速命令参考

```bash
# 开始工作
cd D:\structural-design-system
git pull origin dev
code .

# 提交代码
git add .
git commit -m "feat: xxx"
git push origin dev

# 查看状态
git status
git log --oneline -10
```
