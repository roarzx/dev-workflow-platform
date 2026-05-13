# Dev Workflow Platform

个人开发工作流自动化平台 —— 从需求到提测的全流程 AI 辅助管线。

## 功能概览

| 模块 | 说明 | 状态 |
|------|------|------|
| **需求看板** | 从 TAPD 增量同步需求，分页浏览 / 筛选 / 排序 | ✅ 已完成 |
| **开发管线** | 规划 → 代码生成 → 审查 → 测试 → 提测，状态机驱动 | 🚧 框架就绪，AI 执行待集成 |
| **AI 对话** | 管线规划阶段与 AI 讨论方案 | 🚧 Phase 2 |
| **系统设置** | 可视化配置 TAPD / GitLab / LLM / CI-CD，支持连接测试 | ✅ 已完成 |
| **代码审查** | AI 自动审查生成的代码 | 📅 Phase 3 |
| **CI/CD 集成** | 触发 GitLab CI 部署测试环境 | 📅 Phase 3 |

### 管线状态流转

```
idle → planning → dispatching → reviewing → testing → ready_to_submit → completed
         ↑            ↑             ↑            ↑
         └────────────┴─────────────┴────────────┘ ← failed (可重试)
```

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI · async SQLAlchemy (asyncpg) · Pydantic Settings · structlog |
| 前端 | React 19 · Vite 6 · Ant Design 5 · React Router 7 |
| 数据库 | PostgreSQL 16 · Alembic 迁移 |
| 队列 | Redis 7 · RQ Worker |
| AI | LangChain (OpenAI / Anthropic / Gemini) |
| 部署 | Docker Compose |

## 快速开始

### 前置条件

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose（用于 PostgreSQL / Redis）

### 1. 启动依赖服务

```bash
docker compose up -d postgres redis
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 TAPD / GitLab / LLM 等配置
# 也可启动后在「设置」页面中配置
```

### 3. 启动后端

```bash
cd backend
uv sync                  # 安装依赖（使用 uv 包管理器）
alembic upgrade head     # 数据库迁移
uvicorn app.main:app --port 8000 --reload
```

### 4. 启动前端

```bash
cd frontend
npm install
npx vite --port 3000
```

访问 http://localhost:3000 即可使用。

### Docker Compose 一键启动

```bash
docker compose up -d
```

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 项目结构

```
dev-workflow-platform/
├── backend/
│   ├── app/
│   │   ├── api/             # API 路由
│   │   │   ├── tasks.py          # 需求看板 CRUD + TAPD 同步
│   │   │   ├── pipelines.py      # 开发管线全生命周期
│   │   │   ├── llm_providers.py  # LLM 提供商管理
│   │   │   ├── webhooks.py       # GitLab / CI Webhook
│   │   │   └── system_settings.py# 系统设置 + TAPD 连接测试
│   │   ├── models/          # SQLAlchemy 数据模型
│   │   ├── schemas/         # Pydantic 请求/响应模型
│   │   ├── services/        # 业务逻辑
│   │   │   └── tapd_sync.py      # TAPD 增量同步服务
│   │   ├── prompts/         # AI Prompt 模板
│   │   ├── workers/         # RQ 异步任务
│   │   ├── config.py        # 配置（pydantic-settings）
│   │   ├── database.py      # 数据库连接
│   │   └── main.py          # FastAPI 入口
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── TaskBoard.tsx        # 需求看板
│   │   │   ├── PipelineWorkbench.tsx# 管线工作台
│   │   │   └── Settings.tsx        # 系统设置
│   │   ├── components/
│   │   │   └── MainLayout.tsx      # 导航布局
│   │   ├── api/
│   │   │   └── client.ts           # API 请求封装
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── Dockerfile
│   └── package.json
├── alembic/                  # 数据库迁移
│   └── versions/
│       └── 001_initial.py
├── docker-compose.yml
└── .env                      # 环境变量（不入库）
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/tasks` | 需求列表（分页/筛选） |
| POST | `/api/v1/tasks/sync` | 手动触发 TAPD 同步 |
| GET | `/api/v1/tasks/{id}` | 需求详情 |
| POST | `/api/v1/pipelines` | 创建开发管线 |
| GET | `/api/v1/pipelines/{id}` | 查询管线状态 |
| POST | `/api/v1/pipelines/{id}/chat` | AI 对话（规划阶段） |
| POST | `/api/v1/pipelines/{id}/confirm-plan` | 确认方案 |
| POST | `/api/v1/pipelines/{id}/start-review` | AI 代码审查 |
| POST | `/api/v1/pipelines/{id}/generate-tests` | 生成测试用例 |
| POST | `/api/v1/pipelines/{id}/deploy` | 触发测试环境部署 |
| POST | `/api/v1/pipelines/{id}/submit` | 提测（更新 TAPD） |
| GET | `/api/v1/settings` | 获取系统设置 |
| PUT | `/api/v1/settings` | 更新系统设置 |
| POST | `/api/v1/settings/test-tapd` | 测试 TAPD 连接 |
| GET | `/api/v1/llm-providers` | LLM 提供商列表 |
| GET | `/api/v1/health` | 健康检查 |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_ENV` | 运行环境 | `development` |
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql+asyncpg://devwf:devwf_secret@localhost:5432/dev_workflow` |
| `REDIS_URL` | Redis 连接串 | `redis://localhost:6379/0` |
| `TAPD_API_URL` | TAPD API 地址 | `https://api.tapd.cn` |
| `TAPD_API_TOKEN` | TAPD Access Token | （在设置页面配置） |
| `TAPD_WORKSPACE_ID` | TAPD 工作区 ID | （在设置页面配置） |
| `GITLAB_URL` | GitLab 地址 | |
| `GITLAB_TOKEN` | GitLab Access Token | |

> 敏感字段（Token 等）在设置页面以脱敏方式展示，保存时空值不会覆盖已有密钥。

## 开发路线

- **Phase 1** ✅ 基础框架：需求同步、管线状态机、设置页面
- **Phase 2** 🚧 AI 集成：LangChain 对话式规划、Claude Code 代码生成
- **Phase 3** 📅 完整闭环：代码审查、自动测试、CI/CD 部署、TAPD 状态回写

## License

MIT
