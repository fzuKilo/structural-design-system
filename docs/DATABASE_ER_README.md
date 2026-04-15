# 数据库ER图

本目录包含两种风格的ER图：

1. **database_er_diagram.dbml** - 现代数据库表结构图（类似UML类图）
2. **database_er_diagram.drawio** - 传统Chen's ER图（实体-关系-属性风格）

---

## 方式1：DBML格式（现代风格）

### 在线查看和编辑

1. 访问 [dbdiagram.io](https://dbdiagram.io/)
2. 点击 "Go to App"
3. 将 `database_er_diagram.dbml` 文件内容复制粘贴到编辑器
4. 自动生成可视化ER图
5. 可以导出为PNG、PDF或SQL

### 本地使用

```bash
# 安装 dbml-renderer
npm install -g @dbml/cli

# 生成PNG图片
dbml2img database_er_diagram.dbml -o database_er_diagram.png

# 生成SQL
dbml2sql database_er_diagram.dbml -o database_schema.sql
```

---

## 方式2：Draw.io格式（传统Chen's ER图）

### 在线查看和编辑

1. 访问 [draw.io](https://app.diagrams.net/)
2. 点击 "Open Existing Diagram"
3. 选择 `database_er_diagram.drawio` 文件
4. 可以编辑和导出为PNG、PDF、SVG等格式

### 本地使用

```bash
# 下载 draw.io 桌面版
# https://github.com/jgraph/drawio-desktop/releases

# 直接双击打开 database_er_diagram.drawio 文件
```

### 图例说明

- **矩形** - 实体（如：用户、任务、角色等）
- **菱形** - 关系（如：创建、包含、拥有等）
- **椭圆** - 属性（如：用户ID、用户名、邮箱等）
- **连线标注** - 基数（1, n, m表示一对一、一对多、多对多）

## 数据库结构概览

### 核心表

#### users (用户表)
- 存储用户基本信息
- 包含API Key加密字段
- 包含每日/每月配额字段

#### tasks (任务表)
- 存储设计任务信息
- 关联用户和Celery任务
- 存储任务状态和结果

#### task_files (任务文件表)
- 存储任务生成的文件
- 包含DXF、PNG、HTML、MD等文件类型

### 权限管理表

#### roles (角色表)
- 定义系统角色（admin、user等）

#### permissions (权限表)
- 定义系统权限（资源+操作）

#### user_roles (用户-角色关联表)
- 多对多关系

#### role_permissions (角色-权限关联表)
- 多对多关系

### 审计表

#### audit_logs (审计日志表)
- 记录用户操作历史
- 包含IP地址、用户代理等信息

## 关系说明

```
User 1:N Task          (一个用户有多个任务)
User 1:N AuditLog      (一个用户有多条审计日志)
Task 1:N TaskFile      (一个任务有多个文件)
User M:N Role          (用户和角色多对多)
Role M:N Permission    (角色和权限多对多)
```

## 索引

- `users.username` - 用户名索引
- `users.email` - 邮箱索引
- `tasks.status` - 任务状态索引
- `tasks.created_at` - 任务创建时间索引
- `audit_logs.created_at` - 审计日志创建时间索引

## 字段说明

### 任务状态 (tasks.status)
- `pending` - 待处理
- `running` - 运行中
- `success` - 成功
- `failed` - 失败

### 结构类型 (tasks.structure_type)
- `beam` - 梁
- `frame` - 框架
- `truss` - 桁架

### 文件类型 (task_files.file_type)
- `dxf` - CAD图纸
- `png` - 预览图/云图
- `html` - 交互式可视化
- `md` - Markdown报告
- `json` - JSON数据
