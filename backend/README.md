# OpenManus 后端 API

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements-api.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

### 3. 启动 Redis（用于 Celery）

```bash
redis-server
```

### 4. 启动 Celery Worker

```bash
celery -A backend.tasks.celery_app worker --loglevel=info
```

### 5. 启动开发服务器

```bash
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

### 认证
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/profile` - 获取用户信息
- `PUT /api/auth/profile` - 更新用户信息

### 设计任务
- `POST /api/design/create` - 创建设计任务
- `GET /api/design/list` - 列出任务
- `GET /api/design/{task_id}/status` - 获取任务状态
- `DELETE /api/design/{task_id}` - 删除任务

### 文件
- `GET /api/file/download?path=xxx` - 下载文件

### WebSocket
- `WS /ws/design/{task_id}?token=xxx` - 实时任务更新

## 数据库

需要 PostgreSQL 数据库。创建数据库：

```bash
createdb structural_design
```

应用会自动创建表结构。
