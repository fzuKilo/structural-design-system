# Celery Worker 启动验证指南

## 问题已修复 ✅

**错误**: `ImportError: cannot import name 'SessionLocal' from 'backend.database'`

**原因**: `SessionLocal` 未在 `backend/database/__init__.py` 中导出

**修复**: 已在 commit `9969d03` 中修复，导出了 `SessionLocal` 和 `QuotaUsageHistory`

---

## 启动步骤

### 1. 启动 Redis（必需）
```bash
# Windows
启动Redis.bat

# 或手动启动
redis-server
```

### 2. 启动 Celery Worker
```bash
# 激活conda环境
conda activate structural-design

# 启动worker（Windows使用solo pool）
celery -A backend.tasks.celery_app worker --loglevel=info --pool=solo
```

**预期输出**:
```
Registered drawer: beam -> BeamDrawer
Registered drawer: cantilever_beam -> CantileverBeamDrawer
...
[tasks]
  . backend.tasks.design_task.run_design_task
  . backend.tasks.quota_tasks.reset_daily_quota_task
  . backend.tasks.quota_tasks.reset_monthly_quota_task

[2026-04-15 ...] INFO/MainProcess] Connected to redis://localhost:6379/0
[2026-04-15 ...] INFO/MainProcess] mingle: searching for neighbors
[2026-04-15 ...] INFO/MainProcess] mingle: all alone
[2026-04-15 ...] INFO/MainProcess] celery@hostname ready.
```

### 3. 启动 Celery Beat（定时任务）
**新开一个终端**:
```bash
conda activate structural-design
celery -A backend.tasks.celery_app beat --loglevel=info
```

**预期输出**:
```
LocalTime -> 2026-04-15 ...
Configuration ->
    . broker -> redis://localhost:6379/0
    . loader -> celery.loaders.app.AppLoader
    . scheduler -> celery.beat.PersistentScheduler
    . db -> celerybeat-schedule
    . logfile -> [stderr]@%INFO
    . maxinterval -> 5.00 minutes (300s)

[2026-04-15 ...] INFO/MainProcess] beat: Starting...
[2026-04-15 ...] INFO/MainProcess] Scheduler: Sending due task reset-daily-quota (backend.tasks.quota_tasks.reset_daily_quota_task)
```

### 4. 启动 FastAPI 后端
**新开一个终端**:
```bash
conda activate structural-design
cd backend
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 启动前端（可选）
**新开一个终端**:
```bash
cd frontend
pnpm dev
```

---

## 验证配额系统

### 测试配额检查
```bash
# 使用 curl 或 Postman 测试

# 1. 登录获取token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}'

# 2. 创建设计任务（会检查并扣减配额）
curl -X POST http://localhost:8000/api/design/create \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"request_text":"设计一个6米跨度的简支梁"}'

# 3. 查看用户配额
curl -X GET http://localhost:8000/api/auth/profile \
  -H "Authorization: Bearer <your_token>"
```

### 手动触发定时任务（测试）
```python
# 在 Python 环境中
from backend.tasks.quota_tasks import reset_daily_quota_task, reset_monthly_quota_task

# 触发每日配额重置
result = reset_daily_quota_task.delay()
print(result.get())

# 触发每月配额重置
result = reset_monthly_quota_task.delay()
print(result.get())
```

---

## 常见问题

### Q1: Celery worker 启动失败
**检查**:
- Redis 是否运行: `redis-cli ping` 应返回 `PONG`
- 环境变量是否正确: 检查 `.env` 文件
- Python 环境是否激活: `conda activate structural-design`

### Q2: 定时任务不执行
**检查**:
- Celery Beat 是否启动
- 查看 Beat 日志确认任务调度
- 检查 `celerybeat-schedule` 文件是否生成

### Q3: 配额扣减不生效
**检查**:
- 数据库是否有 `quota_usage_history` 表
- 运行数据库迁移: `alembic upgrade head`
- 查看 Celery worker 日志是否有错误

### Q4: ImportError 相关错误
**解决**:
- 确保在项目根目录运行命令
- 确保 `PYTHONPATH` 包含项目根目录
- 重新安装依赖: `pip install -r requirements.txt`

---

## 数据库迁移（首次运行必需）

```bash
# 生成迁移文件
alembic revision --autogenerate -m "Add quota_usage_history table"

# 应用迁移
alembic upgrade head

# 验证表是否创建
sqlite3 structural_design.db "SELECT name FROM sqlite_master WHERE type='table' AND name='quota_usage_history';"
```

---

## 监控和调试

### 查看 Celery 任务状态
```python
from backend.tasks.celery_app import celery_app

# 查看活跃任务
i = celery_app.control.inspect()
print(i.active())

# 查看已注册任务
print(i.registered())

# 查看定时任务
print(i.scheduled())
```

### 查看配额使用历史
```sql
-- 查看最近的配额使用记录
SELECT * FROM quota_usage_history
ORDER BY created_at DESC
LIMIT 10;

-- 查看某用户的配额使用
SELECT u.username, quh.*
FROM quota_usage_history quh
JOIN users u ON quh.user_id = u.id
WHERE u.username = 'test'
ORDER BY quh.created_at DESC;

-- 统计每日配额使用
SELECT DATE(created_at) as date, COUNT(*) as usage_count
FROM quota_usage_history
WHERE quota_type = 'daily'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

---

## 生产环境注意事项

1. **使用 Supervisor 或 systemd 管理进程**
   ```ini
   # /etc/supervisor/conf.d/celery-worker.conf
   [program:celery-worker]
   command=/path/to/venv/bin/celery -A backend.tasks.celery_app worker --loglevel=info
   directory=/path/to/project
   user=www-data
   autostart=true
   autorestart=true
   ```

2. **配置日志轮转**
   ```bash
   celery -A backend.tasks.celery_app worker \
     --loglevel=info \
     --logfile=/var/log/celery/worker.log \
     --pidfile=/var/run/celery/worker.pid
   ```

3. **监控工具**
   - Flower: Celery 监控工具
   ```bash
   pip install flower
   celery -A backend.tasks.celery_app flower
   # 访问 http://localhost:5555
   ```

4. **性能优化**
   - 使用 prefork pool（Linux）
   - 调整 worker 并发数: `--concurrency=4`
   - 配置任务超时: `task_time_limit=300`

---

**最后更新**: 2026-04-15
**修复提交**: 9969d03
