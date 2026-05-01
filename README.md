# OpenManus 结构设计系统

基于 OpenManus 框架的 AI 驱动土木工程结构设计平台，支持自然语言输入、多 Agent 协作、有限元分析、CAD 出图与设计报告生成。

---

## 功能特性

- **自然语言交互**：用自然语言描述设计需求，系统自动收集参数并生成结构方案
- **支持结构类型**：简支梁、悬臂梁、连续梁、桁架、框架
- **有限元分析**：调用 Ansys MAPDL 进行结构验算，输出应力、位移等关键指标
- **多方案优化**：生成多个备选方案并实时对比，用户选择最优方案
- **设计评估**：基于经济性、效率、安全性、可持续性四维度量化评分
- **CAD 自动出图**：生成 DXF 格式工程图纸
- **BIM 导出**：支持 IFC 格式导出
- **设计报告**：自动生成完整的 Markdown 格式设计报告
- **实时进度推送**：WebSocket 实时推送任务进度，支持断线重连
- **用户权限管理**：支持管理员 / 普通用户角色，含配额管理

---

## 系统架构

```
用户浏览器（Vue 3 + Ant Design Vue）
    │  HTTP REST API（登录、任务管理、文件下载）
    │  WebSocket（实时进度推送）
    ▼
FastAPI 后端（backend/）
    │  Celery 异步任务队列（Redis 作为 Broker）
    ▼
PlanningFlow 多 Agent 编排（structural_app/）
    ├── StructuralDesignAgent   → 参数收集 & 方案生成（调用 LLM）
    ├── FEAnalysisAgent         → 有限元分析（调用 Ansys MAPDL）
    ├── EvaluationAgent         → 设计质量评估
    ├── CADDrawingAgent         → CAD 图纸生成（ezdxf）
    └── ReportGenerationAgent   → 设计报告生成
    ▼
Ansys MAPDL（本地安装，结构仿真）
```

---

## 技术栈

### 后端
| 组件 | 版本 |
|------|------|
| Python | 3.12 |
| FastAPI | 0.109.0 |
| SQLAlchemy | 2.0.25 |
| Celery | 5.3.6 |
| Redis | 5.0.1（任务队列） |
| PostgreSQL | — （生产数据库） |
| ezdxf | 1.1.3（CAD 出图） |
| PyMAPDL | — （Ansys 接口） |

### 前端
| 组件 | 版本 |
|------|------|
| Vue | ^3.x |
| Vben Admin | 5.7.0（`@vben/web-antd`） |
| Ant Design Vue | ^4.x |
| Vite | — |
| pinia | ^2.x |
| vue-router | ^4.x |
| marked | ^17.0.5（Markdown 渲染） |
| echarts | ^6.0.0（评估图表） |

---

## 项目目录结构

```
structural-design-system/
├── backend/                        # FastAPI 后端
│   ├── api/
│   │   ├── main.py                 # 应用入口，路由注册
│   │   ├── config.py               # 配置（读取 .env）
│   │   ├── routes/                 # 路由（auth、design、file、admin、websocket）
│   │   ├── services/               # 业务服务（认证、加密、WebSocket 管理）
│   │   └── middleware/             # 中间件（JWT 认证、权限、配额）
│   ├── database/
│   │   ├── models.py               # 数据库模型（User、DesignTask 等）
│   │   └── session.py              # 数据库连接
│   ├── tasks/
│   │   ├── celery_app.py           # Celery 配置
│   │   └── design_task.py          # 设计任务异步执行逻辑
│   ├── requirements-api.txt        # 后端依赖
│   └── .env.example                # 环境变量模板
│
├── structural_app/                 # 核心 AI 设计引擎
│   ├── planning_flow.py            # 多 Agent 编排主入口
│   ├── agent/                      # 各阶段 Agent
│   │   ├── structural_design_agent.py
│   │   ├── fe_analysis_agent.py
│   │   ├── evaluation_agent.py
│   │   ├── cad_drawing_agent.py
│   │   └── report_generation_agent.py
│   ├── tool/
│   │   ├── analyzers/              # 有限元分析器（beam、truss、frame 等）
│   │   ├── evaluators/             # 设计评估器
│   │   ├── drawers/                # CAD 绘图器
│   │   ├── reports/                # 报告生成器
│   │   ├── visualizations/         # 结构可视化
│   │   └── exporters/              # BIM 导出（IFC、Speckle）
│   └── knowledge_base/             # RAG 知识库（设计规范）
│
├── frontend/                       # Vben Admin monorepo
│   └── apps/web-antd/src/
│       ├── api/                    # HTTP 接口（auth、design、admin）
│       ├── views/structural/       # 结构设计页面（列表、新建、详情）
│       ├── views/admin/            # 系统管理页面
│       ├── components/design/      # 设计组件（进度、结果展示、人机交互）
│       ├── components/visualization/ # 可视化组件（Markdown、DXF、图表）
│       └── router/routes/modules/  # 路由配置
│
├── config.toml                     # LLM & Ansys 配置（本地，不提交）
├── config.toml.example             # 配置模板
└── output/                         # 生成的图纸、报告输出目录
```

---

## 环境配置

### 前置要求

- Python 3.12（推荐 Anaconda/Miniconda）
- Node.js v20+
- pnpm
- PostgreSQL
- Redis
- Ansys（含 PyMAPDL，需本地授权）

---

### 后端配置

**1. 创建 Python 环境**

```bash
conda create -n structural-design python=3.12
conda activate structural-design
```

**2. 安装依赖**

```bash
cd structural-design-system
pip install -r backend/requirements-api.txt
```

> 关键版本注意：`bcrypt==3.2.2`，版本不对会导致认证报错。

**3. 配置环境变量**

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`：

```env
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=          # Fernet 密钥，用于加密用户 API Key
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/structural_design
REDIS_URL=redis://localhost:6379/0
OUTPUT_DIR=./output
```

**4. 配置 LLM 与 Ansys**

```bash
cp config.toml.example config.toml
```

编辑 `config.toml`，填入 LLM API Key 和 Ansys 安装路径：

```toml
[llm]
provider = "openai"   # 或 "anthropic"、"deepseek"
api_key = "your-api-key"
model = "gpt-4o"

[ansys]
use_local = true
ansys_path = "C:/Program Files/ANSYS Inc/v242/ansys/bin/winx64/ANSYS242.exe"
```

**5. 初始化数据库**

确保 PostgreSQL 已启动并创建数据库 `structural_design`，首次启动后端时会自动建表。

---

### 前端配置

**1. 安装 Node.js 和 pnpm**

```bash
npm install -g pnpm
```

**2. 安装前端依赖**

```bash
cd frontend
pnpm approve-builds   # 首次安装：按 a 全选，回车确认
pnpm install
```

---

## 启动系统

每次启动需要开 **4 个终端窗口**，按顺序执行：

**窗口 1 — Redis**
```bash
D:\Redis\Redis-x64-3.0.504\redis-server.exe
```
> macOS/Linux：`redis-server`

**窗口 2 — 后端 API**
```bash
cd structural-design-system
conda activate structural-design
python -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

验证：访问 http://localhost:8000/docs 查看 API 文档

**窗口 3 — Celery Worker**
```bash
cd structural-design-system
conda activate structural-design
celery -A backend.tasks.celery_app worker --loglevel=info --pool=solo
```

> Windows 必须加 `--pool=solo`

**窗口 4 — 前端**
```bash
cd structural-design-system/frontend
pnpm dev
```

出现选择菜单时选择 **`@vben/web-antd`**，然后访问：

**http://localhost:5666**

---

## API Key 配置

系统使用 LLM 生成结构方案，每个用户需要在个人中心配置自己的 LLM API Key：

1. 登录后点击右上角头像 → **个人中心**
2. 进入 **API Key 设置** 标签页
3. 输入 API Key 并保存

Key 会使用 Fernet 加密后存储到数据库，不保存明文。未配置 API Key 时无法提交设计任务。

---

## 默认账号

| 账号 | 密码 | 角色 |
|------|------|------|
| 管理员 | 123456 | admin（可访问系统管理） |

---

## 常见问题

**Q：启动前端提示 `pnpm approve-builds`**
```bash
pnpm approve-builds   # 按 a 全选，回车确认
```

**Q：新建设计任务失败**
- 确认 Redis 已启动
- 确认 Celery Worker 已启动
- 确认已在个人中心配置 API Key

**Q：`bcrypt` 报错 `AttributeError`**
```bash
pip install bcrypt==3.2.2
```

**Q：Redis 连接失败**
```bash
redis-cli ping   # 应返回 PONG
```

**Q：登录后看不到"系统管理"菜单**
- 确认使用管理员账号登录
- 在浏览器控制台执行 `localStorage.clear()` 后刷新重新登录

---

## 分支说明

- `main`：稳定版本
- `dev`：日常开发分支

---

## 许可证

MIT License
