# 开发环境配置指南

本文档帮助新成员快速配置开发环境并开始协作开发。

## 前置要求

在开始之前，请确保已安装：

- ✅ Python 3.8+
- ✅ Git
- ✅ GitHub账号
- ✅ 文本编辑器（推荐 VS Code）

---

## 第一步：接受仓库邀请

1. 检查你的邮箱，找到来自GitHub的协作邀请邮件
2. 点击邮件中的 `Accept invitation` 按钮
3. 或者直接访问：https://github.com/Lin-0408-Yiran/structural-design-system
4. 如果看到 `Accept invitation` 按钮，点击接受

---

## 第二步：配置Git用户信息

打开命令行工具（PowerShell / CMD / Git Bash），执行：

```bash
# 配置你的名字（用于Git提交记录）
git config --global user.name "你的名字"

# 配置你的邮箱（建议使用GitHub邮箱）
git config --global user.email "你的邮箱@example.com"

# 验证配置
git config --global user.name
git config --global user.email
```

**示例：**
```bash
git config --global user.name "Zhang San"
git config --global user.email "zhangsan@fzu.edu.cn"
```

---

## 第三步：克隆项目到本地

### 3.1 选择工作目录

```bash
# 例如在D盘创建工作目录
cd /d D:\
```

### 3.2 克隆仓库

```bash
git clone https://github.com/Lin-0408-Yiran/structural-design-system.git
```

### 3.3 进入项目目录

```bash
cd structural-design-system
```

### 3.4 查看项目结构

```bash
# Windows CMD/PowerShell
dir

# Git Bash
ls -la
```

你应该看到：
```
structural-design-system/
├── app/              # 应用代码
├── docs/             # 文档
├── tests/            # 测试
├── config.toml.example
├── requirements.txt
└── README.md
```

---

## 第四步：切换到开发分支

```bash
# 切换到dev分支（日常开发分支）
git checkout dev

# 验证当前分支
git branch
```

应该显示：
```
* dev
  main
```

---

## 第五步：安装依赖

### 5.1 安装OpenManus框架

**方式1：从本地安装（如果有OpenManus源码）**
```bash
pip install -e D:\openmanus
```

**方式2：从GitHub安装**
```bash
pip install git+https://github.com/FoundationAgents/OpenManus.git
```

### 5.2 安装项目依赖

```bash
pip install -r requirements.txt
```

### 5.3 验证安装

```bash
python -c "import openmanus; print('OpenManus安装成功')"
```

---

## 第六步：配置API密钥

### 6.1 复制配置文件模板

```bash
# Windows CMD
copy config.toml.example config.toml

# PowerShell
Copy-Item config.toml.example config.toml

# Git Bash
cp config.toml.example config.toml
```

### 6.2 编辑配置文件

用文本编辑器打开 `config.toml`，填入实际的API密钥：

```toml
[llm]
provider = "openai"  # 或 "anthropic", "deepseek"
api_key = "你的实际API密钥"
model = "gpt-4o"
temperature = 0.7
max_tokens = 4000

[ansys]
# Ansys MAPDL配置
mapdl_path = "C:/Program Files/ANSYS Inc/v242/ansys/bin/winx64/ANSYS242.exe"
working_dir = "./ansys_workdir"
```

**注意：**
- ⚠️ `config.toml` 已在 `.gitignore` 中，不会被提交到Git
- ⚠️ 不要将API密钥提交到仓库！

---

## 第七步：验证环境

运行测试脚本验证环境配置：

```bash
python main.py
```

如果看到欢迎信息，说明环境配置成功！

---

## 日常开发流程

### 开始工作前（每次！）

```bash
# 1. 确保在dev分支
git checkout dev

# 2. 拉取最新代码（避免冲突）
git pull origin dev

# 3. 创建功能分支（推荐）
git checkout -b feature/你的功能名称
```

**功能分支命名规范：**
- `feature/design-agent` - 新功能
- `fix/beam-calculation` - Bug修复
- `refactor/tool-structure` - 重构
- `docs/api-documentation` - 文档

### 开发过程中

```bash
# 随时查看修改状态
git status

# 查看具体修改内容
git diff
```

### 完成工作后

```bash
# 1. 查看修改
git status

# 2. 添加修改的文件
git add .
# 或者添加特定文件
git add app/agent/design_agent.py

# 3. 提交修改
git commit -m "feat: 添加设计Agent基础功能"

# 4. 推送到远程
git push origin feature/你的功能名称
```

**提交信息规范：**
- `feat: 新功能描述`
- `fix: 修复问题描述`
- `refactor: 重构描述`
- `docs: 文档更新`
- `test: 测试相关`
- `chore: 构建/工具相关`

### 合并到dev分支

**方式1：通过GitHub Pull Request（推荐）**

1. 推送功能分支后，访问GitHub仓库
2. 点击 `Compare & pull request`
3. 填写PR描述，说明你做了什么
4. 请求队友Review
5. 通过后合并到dev

**方式2：直接合并（小改动）**

```bash
# 切换到dev分支
git checkout dev

# 合并功能分支
git merge feature/你的功能名称

# 推送到远程
git push origin dev
```

---

## 常见问题

### Q1: 拉取代码时出现冲突怎么办？

```bash
# 1. 查看冲突文件
git status

# 2. 打开冲突文件，手动解决冲突
# 文件中会有 <<<<<<< HEAD 和 >>>>>>> 标记

# 3. 解决后添加文件
git add 冲突文件名

# 4. 完成合并
git commit -m "merge: 解决冲突"
```

### Q2: 不小心在main分支修改了代码？

```bash
# 1. 暂存当前修改
git stash

# 2. 切换到dev分支
git checkout dev

# 3. 恢复修改
git stash pop
```

### Q3: 想撤销最近的提交？

```bash
# 撤销提交但保留修改
git reset --soft HEAD~1

# 撤销提交和修改（危险！）
git reset --hard HEAD~1
```

### Q4: 如何更新本地的分支列表？

```bash
# 获取远程分支信息
git fetch origin

# 查看所有分支
git branch -a
```

---

## 团队协作最佳实践

### ✅ 推荐做法

1. **每天开始工作前先拉取最新代码**
   ```bash
   git pull origin dev
   ```

2. **小步提交，频繁推送**
   - 完成一个小功能就提交
   - 不要积累太多修改

3. **写清晰的提交信息**
   - 说明做了什么，为什么这样做
   - 方便队友理解

4. **使用功能分支**
   - 大功能用独立分支开发
   - 避免直接在dev上修改

5. **代码Review**
   - 通过Pull Request让队友检查代码
   - 互相学习，提高代码质量

### ❌ 避免做法

1. ❌ 不要直接在main分支修改
2. ❌ 不要提交 `config.toml`（包含密钥）
3. ❌ 不要提交 `__pycache__/` 等临时文件
4. ❌ 不要使用 `git push --force`（除非确定）
5. ❌ 不要长时间不同步代码（容易冲突）

---

## 项目结构说明

```
structural-design-system/
├── app/
│   ├── agent/              # Agent实现
│   │   └── design_agent.py
│   ├── tool/               # 工具实现
│   │   ├── analyzers/      # 分析工具（Ansys）
│   │   ├── drawers/        # 绘图工具
│   │   ├── validators/     # 验证工具
│   │   └── evaluators/     # 评估工具
│   └── utils/              # 工具函数
├── tests/                  # 测试文件
├── docs/                   # 文档
│   ├── COLLABORATION.md    # 协同开发指南
│   ├── INTERFACE_CONTRACT.md  # 接口约定
│   └── SETUP_GUIDE.md      # 本文档
├── examples/               # 示例代码
├── config.toml.example     # 配置模板
├── config.toml            # 实际配置（不提交）
├── requirements.txt        # Python依赖
├── main.py                # 主入口
└── README.md              # 项目说明
```

---

## 获取帮助

### 文档资源

- 协同开发指南：`docs/COLLABORATION.md`
- 接口约定：`docs/INTERFACE_CONTRACT.md`
- OpenManus文档：https://github.com/FoundationAgents/OpenManus

### 遇到问题？

1. 查看项目文档
2. 询问队友
3. 查看Git/GitHub文档
4. 在项目中创建Issue讨论

---

## 快速命令参考

```bash
# 查看状态
git status

# 拉取最新代码
git pull origin dev

# 创建并切换分支
git checkout -b feature/xxx

# 添加修改
git add .

# 提交
git commit -m "feat: 描述"

# 推送
git push origin dev

# 查看分支
git branch -a

# 切换分支
git checkout dev

# 查看提交历史
git log --oneline

# 查看远程仓库
git remote -v
```

---

**配置完成后，就可以开始愉快地协作开发了！🎉**

有问题随时在团队中讨论。
