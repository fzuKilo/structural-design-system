# 数据库表结构说明

## 📋 表清单

| 序号 | 表名 | 说明 | 记录数预估 |
|------|------|------|-----------|
| 1 | users | 用户表 | 1000+ |
| 2 | tasks | 任务表 | 10000+ |
| 3 | task_files | 任务文件表 | 50000+ |
| 4 | roles | 角色表 | <10 |
| 5 | permissions | 权限表 | <50 |
| 6 | user_roles | 用户-角色关联表 | 1000+ |
| 7 | role_permissions | 角色-权限关联表 | <100 |
| 8 | audit_logs | 审计日志表 | 100000+ |

---

## 1. users（用户表）

### 字段列表

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | VARCHAR(36) | PK | UUID | 用户ID |
| username | VARCHAR(50) | UNIQUE, NOT NULL | - | 用户名 |
| email | VARCHAR(100) | UNIQUE, NOT NULL | - | 邮箱 |
| password_hash | VARCHAR(255) | NOT NULL | - | 密码哈希 |
| api_key_encrypted | TEXT | NULL | - | API Key加密存储 |
| quota_daily | INTEGER | CHECK >= 0 | 100 | 每日配额 |
| quota_monthly | INTEGER | CHECK >= 0 | 1000 | 每月配额 |
| created_at | TIMESTAMP | - | now() | 创建时间 |

### 索引
- `idx_users_username` - username
- `idx_users_email` - email

### 关系
- 1:N → tasks
- 1:N → audit_logs
- M:N → roles (通过user_roles)

---

## 2. tasks（任务表）

### 字段列表

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | VARCHAR(36) | PK | UUID | 任务ID |
| user_id | VARCHAR(36) | FK, NOT NULL | - | 用户ID |
| status | VARCHAR(20) | CHECK | 'pending' | 任务状态 |
| celery_task_id | VARCHAR(255) | NULL | - | Celery任务ID |
| request_text | TEXT | NOT NULL | - | 用户输入 |
| structure_type | VARCHAR(50) | NULL | - | 结构类型 |
| created_at | TIMESTAMP | - | now() | 创建时间 |
| completed_at | TIMESTAMP | NULL | - | 完成时间 |
| result_json | JSONB | NULL | - | 结果JSON |

### 枚举值
- **status**: `pending`, `running`, `success`, `failed`
- **structure_type**: `beam`, `frame`, `truss`

### 索引
- `idx_tasks_user_id` - user_id
- `idx_tasks_status` - status
- `idx_tasks_created_at` - created_at
- `idx_tasks_structure_type` - structure_type

### 外键
- `user_id` → users.id (ON DELETE CASCADE)

### 关系
- N:1 → users
- 1:N → task_files

---

## 3. task_files（任务文件表）

### 字段列表

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | VARCHAR(36) | PK | UUID | 文件ID |
| task_id | VARCHAR(36) | FK, NOT NULL | - | 任务ID |
| file_type | VARCHAR(50) | NOT NULL | - | 文件类型 |
| file_path | TEXT | NOT NULL | - | 文件路径 |
| file_size | BIGINT | CHECK >= 0 | - | 文件大小 |
| created_at | TIMESTAMP | - | now() | 创建时间 |

### 枚举值
- **file_type**: `dxf`, `png`, `html`, `md`, `json`

### 索引
- `idx_task_files_task_id` - task_id
- `idx_task_files_file_type` - file_type

### 外键
- `task_id` → tasks.id (ON DELETE CASCADE)

### 关系
- N:1 → tasks

---

## 4. roles（角色表）

### 字段列表

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | VARCHAR(36) | PK | UUID | 角色ID |
| name | VARCHAR(50) | UNIQUE, NOT NULL | - | 角色名称 |
| display_name | VARCHAR(100) | NOT NULL | - | 显示名称 |
| description | TEXT | NULL | - | 角色描述 |
| created_at | TIMESTAMP | - | now() | 创建时间 |

### 预置角色

| name | display_name | 说明 |
|------|--------------|------|
| admin | 管理员 | 系统管理员，拥有所有权限 |
| user | 普通用户 | 可以创建和查看自己的任务 |

### 关系
- M:N → users (通过user_roles)
- M:N → permissions (通过role_permissions)

---

## 5. permissions（权限表）

### 字段列表

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | VARCHAR(36) | PK | UUID | 权限ID |
| name | VARCHAR(100) | UNIQUE, NOT NULL | - | 权限名称 |
| resource | VARCHAR(50) | NOT NULL | - | 资源类型 |
| action | VARCHAR(50) | NOT NULL | - | 操作 |
| description | TEXT | NULL | - | 权限描述 |
| created_at | TIMESTAMP | - | now() | 创建时间 |

### 索引
- `idx_permissions_resource` - resource
- `idx_permissions_action` - action

### 预置权限

| name | resource | action | 说明 |
|------|----------|--------|------|
| task:create | task | create | 创建设计任务 |
| task:read | task | read | 查看设计任务 |
| task:update | task | update | 更新设计任务 |
| task:delete | task | delete | 删除设计任务 |
| user:read | user | read | 查看用户信息 |
| user:update | user | update | 更新用户信息 |
| user:manage | user | manage | 管理用户 |
| admin:access | admin | access | 访问管理后台 |

### 关系
- M:N → roles (通过role_permissions)

---

## 6. user_roles（用户-角色关联表）

### 字段列表

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| user_id | VARCHAR(36) | PK, FK | - | 用户ID |
| role_id | VARCHAR(36) | PK, FK | - | 角色ID |
| assigned_at | TIMESTAMP | - | now() | 分配时间 |

### 索引
- `idx_user_roles_user_id` - user_id
- `idx_user_roles_role_id` - role_id

### 外键
- `user_id` → users.id (ON DELETE CASCADE)
- `role_id` → roles.id (ON DELETE CASCADE)

---

## 7. role_permissions（角色-权限关联表）

### 字段列表

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| role_id | VARCHAR(36) | PK, FK | - | 角色ID |
| permission_id | VARCHAR(36) | PK, FK | - | 权限ID |
| assigned_at | TIMESTAMP | - | now() | 分配时间 |

### 索引
- `idx_role_permissions_role_id` - role_id
- `idx_role_permissions_permission_id` - permission_id

### 外键
- `role_id` → roles.id (ON DELETE CASCADE)
- `permission_id` → permissions.id (ON DELETE CASCADE)

### 预置权限分配

**管理员（admin）**：
- task:create, task:read, task:update, task:delete
- user:read, user:update, user:manage
- admin:access

**普通用户（user）**：
- task:create, task:read
- user:read, user:update

---

## 8. audit_logs（审计日志表）

### 字段列表

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | VARCHAR(36) | PK | UUID | 日志ID |
| user_id | VARCHAR(36) | FK, NULL | - | 用户ID |
| action | VARCHAR(100) | NOT NULL | - | 操作类型 |
| resource_type | VARCHAR(50) | NULL | - | 资源类型 |
| resource_id | VARCHAR(36) | NULL | - | 资源ID |
| ip_address | VARCHAR(50) | NULL | - | IP地址 |
| user_agent | TEXT | NULL | - | 用户代理 |
| details | JSONB | NULL | - | 详细信息 |
| created_at | TIMESTAMP | - | now() | 创建时间 |

### 索引
- `idx_audit_logs_user_id` - user_id
- `idx_audit_logs_action` - action
- `idx_audit_logs_created_at` - created_at
- `idx_audit_logs_resource` - (resource_type, resource_id)

### 外键
- `user_id` → users.id (ON DELETE SET NULL)

### 关系
- N:1 → users

---

## 📊 视图

### user_task_stats（用户任务统计）

统计每个用户的任务情况

**字段**：
- user_id, username, email
- total_tasks - 总任务数
- success_tasks - 成功任务数
- failed_tasks - 失败任务数
- running_tasks - 运行中任务数
- pending_tasks - 待处理任务数
- last_task_time - 最后任务时间

### task_details（任务详情）

任务详情及文件统计

**字段**：
- task_id, user_id, username
- status, structure_type, request_text
- created_at, completed_at
- file_count - 文件数量
- total_file_size - 总文件大小

---

## 🔧 函数

### check_user_quota(user_id, quota_type)

检查用户配额是否充足

**参数**：
- `user_id` - 用户ID
- `quota_type` - 配额类型（'daily' 或 'monthly'）

**返回**：
- `BOOLEAN` - true表示配额充足，false表示配额不足

**用法**：
```sql
SELECT check_user_quota('user_id_here', 'daily');
```

---

## 🔐 级联删除规则

| 父表 | 子表 | 规则 |
|------|------|------|
| users | tasks | CASCADE（删除用户时删除其所有任务） |
| users | user_roles | CASCADE（删除用户时删除其角色关联） |
| users | audit_logs | SET NULL（删除用户时日志保留，user_id置空） |
| tasks | task_files | CASCADE（删除任务时删除其所有文件） |
| roles | user_roles | CASCADE（删除角色时删除其用户关联） |
| roles | role_permissions | CASCADE（删除角色时删除其权限关联） |
| permissions | role_permissions | CASCADE（删除权限时删除其角色关联） |

---

## 📈 性能优化建议

### 已实现的优化
1. ✅ 高频查询字段添加索引（username, email, status, created_at）
2. ✅ 外键字段添加索引（user_id, task_id等）
3. ✅ 使用JSONB类型存储JSON数据（支持索引和查询）
4. ✅ 复合索引（resource_type, resource_id）

### 未来可能需要的优化
1. 分区表（audit_logs按月分区）
2. 物化视图（user_task_stats）
3. 定期归档历史数据
4. 添加全文搜索索引（request_text）

---

## 🗄️ 存储空间估算

假设：
- 1000个用户
- 每个用户平均10个任务
- 每个任务平均5个文件
- 每个任务平均10条审计日志

| 表名 | 记录数 | 单条大小 | 总大小 |
|------|--------|----------|--------|
| users | 1,000 | ~500B | ~500KB |
| tasks | 10,000 | ~2KB | ~20MB |
| task_files | 50,000 | ~300B | ~15MB |
| roles | 2 | ~200B | <1KB |
| permissions | 8 | ~200B | <2KB |
| user_roles | 1,000 | ~100B | ~100KB |
| role_permissions | 12 | ~100B | <2KB |
| audit_logs | 100,000 | ~500B | ~50MB |
| **总计** | - | - | **~85MB** |

---

## 📝 维护建议

### 定期任务
1. **每日**：清理超过30天的审计日志
2. **每周**：分析慢查询，优化索引
3. **每月**：归档已完成的任务数据
4. **每季度**：数据库性能分析和优化

### 备份策略
1. **全量备份**：每天凌晨
2. **增量备份**：每小时
3. **保留周期**：30天

### 监控指标
1. 数据库连接数
2. 慢查询数量
3. 表大小增长趋势
4. 索引使用率
