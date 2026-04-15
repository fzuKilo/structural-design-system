-- ============================================
-- 结构设计系统数据库表结构
-- Database: PostgreSQL
-- Created: 2026-04-15
-- ============================================

-- ============================================
-- 1. 用户表
-- ============================================
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    api_key_encrypted TEXT,
    quota_daily INTEGER DEFAULT 100,
    quota_monthly INTEGER DEFAULT 1000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_quota_daily CHECK (quota_daily >= 0),
    CONSTRAINT chk_quota_monthly CHECK (quota_monthly >= 0)
);

-- 索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- 注释
COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.id IS 'UUID主键';
COMMENT ON COLUMN users.username IS '用户名';
COMMENT ON COLUMN users.email IS '邮箱';
COMMENT ON COLUMN users.password_hash IS '密码哈希';
COMMENT ON COLUMN users.api_key_encrypted IS 'API Key加密存储';
COMMENT ON COLUMN users.quota_daily IS '每日配额（默认100次）';
COMMENT ON COLUMN users.quota_monthly IS '每月配额（默认1000次）';
COMMENT ON COLUMN users.created_at IS '创建时间';


-- ============================================
-- 2. 任务表
-- ============================================
CREATE TABLE tasks (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    celery_task_id VARCHAR(255),
    request_text TEXT NOT NULL,
    structure_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    result_json JSONB,

    CONSTRAINT fk_tasks_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_status CHECK (status IN ('pending', 'running', 'success', 'failed'))
);

-- 索引
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
CREATE INDEX idx_tasks_structure_type ON tasks(structure_type);

-- 注释
COMMENT ON TABLE tasks IS '设计任务表';
COMMENT ON COLUMN tasks.id IS 'UUID主键';
COMMENT ON COLUMN tasks.user_id IS '用户ID（外键）';
COMMENT ON COLUMN tasks.status IS '任务状态: pending/running/success/failed';
COMMENT ON COLUMN tasks.celery_task_id IS 'Celery任务ID';
COMMENT ON COLUMN tasks.request_text IS '用户输入的设计需求';
COMMENT ON COLUMN tasks.structure_type IS '结构类型: beam/frame/truss';
COMMENT ON COLUMN tasks.created_at IS '创建时间';
COMMENT ON COLUMN tasks.completed_at IS '完成时间';
COMMENT ON COLUMN tasks.result_json IS '设计结果JSON';


-- ============================================
-- 3. 任务文件表
-- ============================================
CREATE TABLE task_files (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_task_files_task FOREIGN KEY (task_id)
        REFERENCES tasks(id) ON DELETE CASCADE,
    CONSTRAINT chk_file_size CHECK (file_size >= 0)
);

-- 索引
CREATE INDEX idx_task_files_task_id ON task_files(task_id);
CREATE INDEX idx_task_files_file_type ON task_files(file_type);

-- 注释
COMMENT ON TABLE task_files IS '任务文件表';
COMMENT ON COLUMN task_files.id IS 'UUID主键';
COMMENT ON COLUMN task_files.task_id IS '任务ID（外键）';
COMMENT ON COLUMN task_files.file_type IS '文件类型: dxf/png/html/md/json';
COMMENT ON COLUMN task_files.file_path IS '文件路径';
COMMENT ON COLUMN task_files.file_size IS '文件大小（字节）';
COMMENT ON COLUMN task_files.created_at IS '创建时间';


-- ============================================
-- 4. 角色表
-- ============================================
CREATE TABLE roles (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 注释
COMMENT ON TABLE roles IS '角色表';
COMMENT ON COLUMN roles.id IS 'UUID主键';
COMMENT ON COLUMN roles.name IS '角色名称: admin/user';
COMMENT ON COLUMN roles.display_name IS '显示名称';
COMMENT ON COLUMN roles.description IS '角色描述';
COMMENT ON COLUMN roles.created_at IS '创建时间';


-- ============================================
-- 5. 权限表
-- ============================================
CREATE TABLE permissions (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_permissions_resource ON permissions(resource);
CREATE INDEX idx_permissions_action ON permissions(action);

-- 注释
COMMENT ON TABLE permissions IS '权限表';
COMMENT ON COLUMN permissions.id IS 'UUID主键';
COMMENT ON COLUMN permissions.name IS '权限名称（唯一）';
COMMENT ON COLUMN permissions.resource IS '资源类型: task/user/admin';
COMMENT ON COLUMN permissions.action IS '操作: create/read/update/delete';
COMMENT ON COLUMN permissions.description IS '权限描述';
COMMENT ON COLUMN permissions.created_at IS '创建时间';


-- ============================================
-- 6. 用户-角色关联表
-- ============================================
CREATE TABLE user_roles (
    user_id VARCHAR(36) NOT NULL,
    role_id VARCHAR(36) NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_user_roles_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_roles_role FOREIGN KEY (role_id)
        REFERENCES roles(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role_id ON user_roles(role_id);

-- 注释
COMMENT ON TABLE user_roles IS '用户-角色关联表（多对多）';
COMMENT ON COLUMN user_roles.user_id IS '用户ID（外键）';
COMMENT ON COLUMN user_roles.role_id IS '角色ID（外键）';
COMMENT ON COLUMN user_roles.assigned_at IS '分配时间';


-- ============================================
-- 7. 角色-权限关联表
-- ============================================
CREATE TABLE role_permissions (
    role_id VARCHAR(36) NOT NULL,
    permission_id VARCHAR(36) NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (role_id, permission_id),
    CONSTRAINT fk_role_permissions_role FOREIGN KEY (role_id)
        REFERENCES roles(id) ON DELETE CASCADE,
    CONSTRAINT fk_role_permissions_permission FOREIGN KEY (permission_id)
        REFERENCES permissions(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_role_permissions_role_id ON role_permissions(role_id);
CREATE INDEX idx_role_permissions_permission_id ON role_permissions(permission_id);

-- 注释
COMMENT ON TABLE role_permissions IS '角色-权限关联表（多对多）';
COMMENT ON COLUMN role_permissions.role_id IS '角色ID（外键）';
COMMENT ON COLUMN role_permissions.permission_id IS '权限ID（外键）';
COMMENT ON COLUMN role_permissions.assigned_at IS '分配时间';


-- ============================================
-- 8. 审计日志表
-- ============================================
CREATE TABLE audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(36),
    ip_address VARCHAR(50),
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_audit_logs_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE SET NULL
);

-- 索引
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- 注释
COMMENT ON TABLE audit_logs IS '审计日志表';
COMMENT ON COLUMN audit_logs.id IS 'UUID主键';
COMMENT ON COLUMN audit_logs.user_id IS '用户ID（外键，可为空）';
COMMENT ON COLUMN audit_logs.action IS '操作类型';
COMMENT ON COLUMN audit_logs.resource_type IS '资源类型';
COMMENT ON COLUMN audit_logs.resource_id IS '资源ID';
COMMENT ON COLUMN audit_logs.ip_address IS 'IP地址';
COMMENT ON COLUMN audit_logs.user_agent IS '用户代理';
COMMENT ON COLUMN audit_logs.details IS '详细信息（JSON）';
COMMENT ON COLUMN audit_logs.created_at IS '创建时间';


-- ============================================
-- 初始化数据
-- ============================================

-- 插入默认角色
INSERT INTO roles (id, name, display_name, description) VALUES
    ('role_admin', 'admin', '管理员', '系统管理员，拥有所有权限'),
    ('role_user', 'user', '普通用户', '普通用户，可以创建和查看自己的任务');

-- 插入默认权限
INSERT INTO permissions (id, name, resource, action, description) VALUES
    ('perm_task_create', 'task:create', 'task', 'create', '创建设计任务'),
    ('perm_task_read', 'task:read', 'task', 'read', '查看设计任务'),
    ('perm_task_update', 'task:update', 'task', 'update', '更新设计任务'),
    ('perm_task_delete', 'task:delete', 'task', 'delete', '删除设计任务'),
    ('perm_user_read', 'user:read', 'user', 'read', '查看用户信息'),
    ('perm_user_update', 'user:update', 'user', 'update', '更新用户信息'),
    ('perm_user_manage', 'user:manage', 'user', 'manage', '管理用户'),
    ('perm_admin_access', 'admin:access', 'admin', 'access', '访问管理后台');

-- 分配权限给角色
-- 管理员：所有权限
INSERT INTO role_permissions (role_id, permission_id) VALUES
    ('role_admin', 'perm_task_create'),
    ('role_admin', 'perm_task_read'),
    ('role_admin', 'perm_task_update'),
    ('role_admin', 'perm_task_delete'),
    ('role_admin', 'perm_user_read'),
    ('role_admin', 'perm_user_update'),
    ('role_admin', 'perm_user_manage'),
    ('role_admin', 'perm_admin_access');

-- 普通用户：基本权限
INSERT INTO role_permissions (role_id, permission_id) VALUES
    ('role_user', 'perm_task_create'),
    ('role_user', 'perm_task_read'),
    ('role_user', 'perm_user_read'),
    ('role_user', 'perm_user_update');


-- ============================================
-- 视图：用户任务统计
-- ============================================
CREATE VIEW user_task_stats AS
SELECT
    u.id AS user_id,
    u.username,
    u.email,
    COUNT(t.id) AS total_tasks,
    COUNT(CASE WHEN t.status = 'success' THEN 1 END) AS success_tasks,
    COUNT(CASE WHEN t.status = 'failed' THEN 1 END) AS failed_tasks,
    COUNT(CASE WHEN t.status = 'running' THEN 1 END) AS running_tasks,
    COUNT(CASE WHEN t.status = 'pending' THEN 1 END) AS pending_tasks,
    MAX(t.created_at) AS last_task_time
FROM users u
LEFT JOIN tasks t ON u.id = t.user_id
GROUP BY u.id, u.username, u.email;

COMMENT ON VIEW user_task_stats IS '用户任务统计视图';


-- ============================================
-- 视图：任务详情（包含文件）
-- ============================================
CREATE VIEW task_details AS
SELECT
    t.id AS task_id,
    t.user_id,
    u.username,
    t.status,
    t.structure_type,
    t.request_text,
    t.created_at,
    t.completed_at,
    COUNT(tf.id) AS file_count,
    SUM(tf.file_size) AS total_file_size
FROM tasks t
JOIN users u ON t.user_id = u.id
LEFT JOIN task_files tf ON t.id = tf.task_id
GROUP BY t.id, t.user_id, u.username, t.status, t.structure_type,
         t.request_text, t.created_at, t.completed_at;

COMMENT ON VIEW task_details IS '任务详情视图（包含文件统计）';


-- ============================================
-- 函数：检查用户配额
-- ============================================
CREATE OR REPLACE FUNCTION check_user_quota(
    p_user_id VARCHAR(36),
    p_quota_type VARCHAR(10)
) RETURNS BOOLEAN AS $$
DECLARE
    v_quota INTEGER;
    v_used INTEGER;
BEGIN
    -- 获取配额限制
    IF p_quota_type = 'daily' THEN
        SELECT quota_daily INTO v_quota FROM users WHERE id = p_user_id;
        -- 计算今日已使用配额
        SELECT COUNT(*) INTO v_used
        FROM tasks
        WHERE user_id = p_user_id
          AND DATE(created_at) = CURRENT_DATE;
    ELSIF p_quota_type = 'monthly' THEN
        SELECT quota_monthly INTO v_quota FROM users WHERE id = p_user_id;
        -- 计算本月已使用配额
        SELECT COUNT(*) INTO v_used
        FROM tasks
        WHERE user_id = p_user_id
          AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE);
    ELSE
        RETURN FALSE;
    END IF;

    -- 检查是否超出配额
    RETURN v_used < v_quota;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION check_user_quota IS '检查用户配额是否充足';


-- ============================================
-- 完成
-- ============================================
-- 表结构创建完成
-- 总共8张表：users, tasks, task_files, roles, permissions,
--           user_roles, role_permissions, audit_logs
-- 2个视图：user_task_stats, task_details
-- 1个函数：check_user_quota
