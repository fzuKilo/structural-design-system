# OpenManus结构设计系统

基于OpenManus框架的AI驱动土木工程结构设计平台

## 项目概述

本系统实现：
- **自然语言输入** → 交互式参数收集
- **LLM智能设计** → 生成结构方案
- **Ansys验算** → 有限元分析与校核
- **量化评估** → 多维度设计质量评估
- **AutoCAD绘图** → 自动生成图纸
- **完整报告** → 向用户提供设计方案

## 快速开始

### 环境要求

- Python 3.12+
- Ansys (PyMAPDL)
- OpenManus框架

### 安装

#### 普通协作者（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/Lin-0408-Yiran/structural-design-system.git
cd structural-design-system

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 安装依赖（会自动从GitHub安装OpenManus）
pip install -r requirements.txt

# 4. 配置
cp config.toml.example config.toml
# 编辑config.toml，填入API密钥
```

#### 核心开发者（需要同时开发OpenManus）

```bash
# 1-2. 同上

# 3. 先安装OpenManus为可编辑模式
pip install -e /path/to/your/openmanus

# 4. 安装其他依赖（注释掉requirements.txt中的OpenManus行）
pip install -r requirements.txt

# 5. 配置（同上）
```

### 运行

```bash
python main.py
```

## 项目结构

```
structural-design-system/
├── app/
│   ├── agent/          # Agent层（通用）
│   ├── tool/           # Tool层（类型特定）
│   └── utils/          # 工具函数
├── tests/              # 测试
├── docs/               # 文档
├── config/             # 配置文件
└── examples/           # 示例
```

## 开发指南

详见 [DEVELOPMENT.md](docs/DEVELOPMENT.md)

## 协同开发

- 主分支：`main`（稳定版本）
- 开发分支：`dev`（日常开发）
- 功能分支：`feature/xxx`（新功能）

详见 [COLLABORATION.md](docs/COLLABORATION.md)

## 架构设计

详见 [docs/agent_architecture.md](docs/agent_architecture.md)

## 许可证

MIT License

## 贡献者

- 人员A
- 人员B
