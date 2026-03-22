# OpenManus 前端

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

访问: http://localhost:5173

### 3. 构建生产版本

```bash
npm run build
```

## 功能特性

- ✅ 用户认证（登录/注册）
- ✅ 任务列表（Dashboard）
- ✅ 创建设计任务
- ✅ 实时进度跟踪（WebSocket）
- ✅ 5 阶段进度条
- ✅ AskHuman 交互模态框
- ✅ 实时日志显示

## 技术栈

- Vue 3 + TypeScript
- Ant Design Vue 4.x
- Pinia (状态管理)
- Vue Router 4
- Axios
- WebSocket

## 项目结构

```
src/
├── api/           # API 调用
├── components/    # 组件
├── views/         # 页面
├── stores/        # Pinia stores
├── router/        # 路由配置
├── utils/         # 工具函数
└── types/         # TypeScript 类型
```
