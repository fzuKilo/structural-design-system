-- RBAC Migration Script
-- Creates roles, permissions, and associations

-- Insert default roles
INSERT INTO roles (id, name, display_name, description) VALUES
('role-admin', 'admin', '管理员', '系统管理员，拥有所有权限'),
('role-user', 'user', '普通用户', '普通用户，可以创建和查看自己的设计'),
('role-guest', 'guest', '访客', '只读访客，只能查看公开内容');

-- Insert permissions
INSERT INTO permissions (id, name, resource, action, description) VALUES
-- Design permissions
('perm-design-create', 'design:create', 'design', 'create', '创建设计任务'),
('perm-design-read', 'design:read', 'design', 'read', '查看设计任务'),
('perm-design-update', 'design:update', 'design', 'update', '更新设计任务'),
('perm-design-delete', 'design:delete', 'design', 'delete', '删除设计任务'),
-- User management
('perm-user-manage', 'user:manage', 'user', 'manage', '管理用户'),
('perm-role-manage', 'role:manage', 'role', 'manage', '管理角色'),
-- System management
('perm-system-config', 'system:config', 'system', 'config', '系统配置');

-- Assign all permissions to admin role
INSERT INTO role_permissions (role_id, permission_id)
SELECT 'role-admin', id FROM permissions;

-- Assign design permissions to user role
INSERT INTO role_permissions (role_id, permission_id) VALUES
('role-user', 'perm-design-create'),
('role-user', 'perm-design-read'),
('role-user', 'perm-design-update'),
('role-user', 'perm-design-delete');

-- Assign read-only permission to guest role
INSERT INTO role_permissions (role_id, permission_id) VALUES
('role-guest', 'perm-design-read');
