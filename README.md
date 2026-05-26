# Meeting Agent — AI 会议纪要结构化提取 & 企业微信自动推送

上传会议记录（.docx / 录音文件），自动调用 LLM 提取结构化信息（会议时间、待办日程、推送对象等），支持 Web UI 在线审阅编辑（Tiptap 富文本），一键推送到企业微信（消息通知 + 日历日程 + 附件文件），并支持 PDF / DOCX 导出。

## 功能特性

- **智能解析** — 读取 .docx 格式会议记录，自动提取会议时间、参会人员、待办日程、正式纪要等结构化信息
- **录音转写** — 上传录音文件（MP3/WAV 等常见格式）或提供音频 URL，自动进行语音识别转写（腾讯云 ASR），支持 **tflink 中转**绕过 ASR 直传 5MB 限制，最大支持 100MB
- **两阶段转录流程** — 阶段一 ASR 转写 → LLM 生成纪要草稿 → 用户在线编辑 → 阶段二 LLM 按部门/中心分解工作任务与日程
- **富文本编辑** — 集成 Tiptap 编辑器，支持加粗、斜体、下划线、标题、对齐等富文本编辑
- **PDF 导出** — 双引擎方案：优先浏览器无头打印（Edge/Chrome），自动回退 fpdf2 引擎；支持纯文本与 HTML 两种渲染模式
- **DOCX 导出** — 通过 python-docx 导出为 .docx 文件，线下分发便捷
- **用户认证系统** — Web UI 注册登录，PBKDF2-HMAC-SHA256 密码哈希，admin/user 角色权限管理，多用户数据隔离
- **企业微信推送** — 一键推送会议纪要消息（Markdown 自动分片）、批量创建日历日程、附件（PDF/docx）文件推送
- **CLI / Web 双模式** — 既可命令行一键处理，也支持 Web 界面上传管理审阅
- **后台任务队列** — 耗时操作（ASR 语音识别、LLM 提取）异步执行，API 秒级返回，Worker 进程独立轮询处理，前端实时轮询进度
- **LLM 无关** — 兼容任意 OpenAI 格式的 API（DeepSeek、OpenAI、通义千问等），通过 .env 配置即可切换
- **Docker 部署** — 多阶段构建（Node 编译前端 → Python 运行时），一键 docker compose up

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | Python 3.11+ / FastAPI |
| 前端 | Vue 3 + Vite + Tiptap（富文本编辑器） |
| LLM SDK | LangChain（OpenAI-compatible） |
| 文档解析 | python-docx |
| 语音识别 | 腾讯云 ASR SDK（直传 ≤5MB / URL 拉取 / tflink 中转 100MB） |
| PDF 导出 | 浏览器无头打印（Edge/Chrome）+ fpdf2 双引擎回退 |
| 数据校验 | Pydantic |
| 数据存储 | PostgreSQL（ThreadedConnectionPool 连接池管理） |
| 认证 | PBKDF2-HMAC-SHA256 600K 迭代 + session token |
| 包管理 | uv |

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 18+
- uv（推荐）或 pip
- PostgreSQL 数据库（本地安装或 Docker 运行 postgres:16）
- 本地安装 Edge 或 Chrome 浏览器（PDF 导出浏览器打印方案需要）
- 腾讯云账号（ASR 语音识别需要，不配则无法使用录音转写功能）

### 1. 克隆并配置

```bash
git clone https://github.com/your-username/meeting-agent.git
cd meeting-agent

# 创建虚拟环境并安装依赖
uv sync

# 配置环境变量
cp .env.example .env
```

编辑 `.env`，填入必要的 API 密钥：

```ini
# LLM 配置（以 DeepSeek 为例）
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
TEMPERATURE=0.2

# 数据库配置
DATABASE_URL=postgresql://user:password@host:5432/meeting_agent

# 腾讯云 ASR 配置（录音转写需要）
TENCENT_SECRET_ID=your-secret-id
TENCENT_SECRET_KEY=your-secret-key

# Web 管理员密码（可选，首次启动自动创建 admin 用户）
ADMIN_PASSWORD=your-admin-password

# 企业微信配置（可选，不配则无法使用推送功能）
WECOM_CORP_ID=your-corp-id
WECOM_CORP_SECRET=your-corp-secret
WECOM_AGENT_ID=your-agent-id
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

### 3. 运行

**CLI 模式：**

```bash
uv run python main.py data/input/你的会议记录.docx
```

结果将打印到终端，同时自动保存到 `data/output/` 目录。

**Web UI 模式：**

```bash
# 终端 1：启动后端 API（开发模式，热重载）
uv run python -m meeting_agent.web.run

# 终端 2：启动后台任务 Worker（自动轮询 DB 执行任务）
uv run python -m meeting_agent.worker

# 终端 3：启动前端开发服务器
cd frontend && npm run dev
```

浏览器打开 `http://localhost:5173` 即可使用。

## Web UI 流程

```
上传 .docx / 录音  →  创建后台任务（秒级返回 task_id）  →  前端轮询 /api/tasks/{id}
                                ↓
                   Worker 异步执行：ASR / LLM 提取 / 生成纪要
                                ↓
                   PostgreSQL background_tasks 表记录状态 + result_id
                                ↓
                   在线审阅编辑（Tiptap 富文本） →  推送至企业微信 / 导出 PDF/DOCX
                                                           ↓
                                       姓名 → userid 映射（PostgreSQL 用户库）
                                       部门 → dept_id 映射（PostgreSQL 部门库）
                                       日期字符串 → Unix 时间戳
                                       消息通知 + 日历日程 + 附件文件
```

### 主解析流程

1. 在 Web UI 上传 .docx 文件（可选同时上传关联 PDF 附件）
2. 后端创建后台任务，秒级返回 `task_id`；前端开始轮询 `/api/tasks/{task_id}` 获取进度
3. Worker 进程异步执行 LLM 提取结构化数据（会议时间、推送部门/人员、日程安排、会议纪要）
4. 提取完成后前端自动跳转到审阅编辑页面，使用 Tiptap 富文本编辑器修改内容
5. 确认无误后点击"推送" — 自动执行姓名↔userid、部门↔dept_id、日期↔时间戳的转换
6. 企业微信推送：Markdown 消息通知（超长自动分片）+ 日历日程批量创建 + 附件文件（PDF优先/docx兜底）

### 转录业务流程（两阶段）

```
┌─ 阶段一 ──────────────────────────────────────────┐
│  上传录音文件（或提供音频 URL）                      │
│    → 创建后台任务，秒级返回 task_id                  │
│    → Worker 异步执行：                              │
│       tflink 中转（文件模式）→ 腾讯云 ASR 识别        │
│       或 URL 直拉 → 腾讯云 ASR 识别                  │
│    → LLM 生成会议纪要草稿（附会议基本信息表单）        │
│    → 前端轮询到完成 → 自动跳转编辑页                  │
│    → 用户在线编辑草稿                               │
└──────────────────────┬────────────────────────────┘
                        ↓
┌─ 阶段二 ──────────────────────────────────────────┐
│  编辑完成 → 提交解析                               │
│    → LLM 按部门/中心分解工作任务及日程                │
│    → 提取推送对象和日程安排                          │
│    → 推送企业微信 / 导出 PDF/DOCX 存档               │
└────────────────────────────────────────────────────┘
```

## API 接口

完整 API 文档可在 Web UI 启动后访问 `/api/docs`（Swagger UI）。

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/auth/register` | 注册账号（默认 role=user） |
| `POST` | `/api/auth/login` | 登录获取 token |
| `POST` | `/api/auth/logout` | 登出 |
| `GET` | `/api/auth/me` | 获取当前用户信息 |

### 会议纪要（提取）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/extract` | 上传 .docx（可选 PDF 附件），创建后台提取任务 |
| `POST` | `/api/extract-from-text` | 传入会议纪要文本，创建后台提取任务（用于转录流程） |
| `GET` | `/api/results` | 获取所有解析记录列表（admin 全部，用户只看自己） |
| `GET` | `/api/results/{id}` | 获取单条解析完整数据 |
| `PUT` | `/api/results/{id}` | 更新解析结果（审阅编辑） |
| `DELETE` | `/api/results/{id}` | 删除解析记录 |
| `POST` | `/api/results/{id}/push` | 推送到企业微信（消息+日程+附件） |
| `POST` | `/api/results/{id}/upload-pdf` | 上传关联 PDF 附件 |

### 录音转写

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/transcribe` | 上传录音文件，创建后台 ASR+LLM 任务（经 tflink 中转，≤100MB） |
| `POST` | `/api/transcribe/url` | 通过音频 URL 创建后台 ASR+LLM 任务（无大小限制，URL 拉取最大 5GB） |
| `GET` | `/api/transcribe/results` | 获取转写记录列表 |
| `GET` | `/api/transcribe/results/{id}` | 获取单条转写数据 |
| `PUT` | `/api/transcribe/results/{id}` | 更新转写结果 |
| `DELETE` | `/api/transcribe/results/{id}` | 删除转写记录 |
| `POST` | `/api/transcribe/results/{id}/parse` | 阶段二：解析会议纪要 → 按部门分解任务 |
| `POST` | `/api/transcribe/results/{id}/push` | 推送转写结果到企业微信 |
| `POST` | `/api/transcribe/results/{id}/export-docx` | 导出为 .docx 文件 |
| `POST` | `/api/transcribe/results/{id}/generate-pdf` | 生成 PDF 文件 |
| `GET` | `/api/transcribe/results/{id}/download-pdf` | 下载生成的 PDF |

### 后台任务

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/tasks/{task_id}` | 查询后台任务状态（前端轮询用），返回 status/result_id/error |

### 用户与部门管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET/POST/PUT/DELETE` | `/api/users` | 企业微信用户 CRUD |
| `GET/POST/PUT/DELETE` | `/api/departments` | 部门 CRUD |
| `GET/POST/DELETE` | `/api/web-users` | Web 登录账号管理（admin 专属） |

## 部署

### Docker Compose（推荐）

项目根目录提供 `Dockerfile`（多阶段构建）和 `docker-compose.yml`，一键启动所有服务。

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入必要配置（LLM API 密钥 + DATABASE_URL + 其他可选配置）

# 2. 启动
docker compose up -d

# 3. 查看日志
docker compose logs -f meeting-agent
```

首次启动会自动完成：表结构初始化 → 前端构建 → 后端启动。
访问 `http://localhost:8000` 即可使用（默认映射端口 8011，见 docker-compose.yml）。

> **注意事项：**
> - PostgreSQL 使用宿主机已有数据库（非容器内），需在 `.env` 中配置 `DATABASE_URL`
> - Docker 容器通过 `host.docker.internal` 访问宿主机数据库
> - 上传的文件（.docx / PDF / 录音）保存在 `./data/` 卷挂载目录
> - 容器内预装 Chromium + Noto Sans CJK 中文字体，支持 PDF 浏览器打印
> - `meeting-agent-worker` 容器独立运行，自动轮询 `background_tasks` 表异步执行耗时任务
> - 可通过 `EXTRACT_WORKER_CONCURRENCY` 和 `TRANSCRIBE_WORKER_CONCURRENCY` 环境变量控制提取/转写的并行任务数（默认均为 2）

### 手动部署（生产环境）

```bash
# 1. 安装 Python 依赖
uv sync --no-dev

# 2. 构建前端
cd frontend
npm ci
npm run build
cd ..

# 3. 启动（生产模式，自带前端静态文件服务）
uv run uvicorn meeting_agent.web.run:app --host 0.0.0.0 --port 8000
```

生产环境建议使用 gunicorn + uvicorn workers 管理进程：

```bash
uv pip install gunicorn
uv run gunicorn meeting_agent.web.run:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers 4
```

### Nginx 反向代理（可选）

```nginx
server {
    listen 80;
    server_name your-domain.com;
    client_max_body_size 110M;  # 支持大文件上传

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 项目结构

```
meeting-agent/
├── main.py                                # CLI 入口：命令行解析 .docx
├── pyproject.toml                         # Python 项目配置与依赖
├── .env.example                           # 环境变量模板
├── Dockerfile                             # 多阶段构建（Node → Python）
├── docker-compose.yml                     # Docker 编排
│
├── meeting_agent/
│   ├── workflow.py                        # 主解析流水线编排（.docx / 文本）
│   ├── worker.py                          # 后台任务 Worker：轮询 DB 异步执行耗时任务
│   ├── document_loader.py                 # .docx 解析（段落 + 表格 → 纯文本）
│   ├── prompts.py                         # LLM 提示词（系统 + 用户模板）
│   ├── schemas.py                         # Pydantic 数据模型（MeetingOutput）
│   ├── llm.py                             # LLM 客户端初始化（ChatOpenAI）
│   ├── config.py                          # 环境变量读取（Settings dataclass）
│   │
│   ├── integrations/                      # 企业微信集成
│   │   ├── wecom_client.py                # 基础客户端（token 管理、HTTP 重试）
│   │   ├── wecom_message_client.py        # 消息推送（text / markdown）
│   │   ├── wecom_calendar_client.py       # 日历日程创建
│   │   └── wecom_file_client.py           # 临时素材上传 + 文件消息推送
│   │
│   ├── services/                          # 业务逻辑层
│   │   ├── message_service.py             # 推送消息（格式转换、超长分片）
│   │   ├── schedule_service.py            # 批量创建日程
│   │   ├── file_service.py                # 附件文件查找与推送
│   │   ├── asr_service.py                 # 腾讯云语音识别（直传/URL 拉取/tflink 中转）
│   │   └── tflink_service.py              # tflink 匿名文件上传中转
│   │
│   ├── transcription/                     # 录音转写模块
│   │   ├── workflow.py                    # 两阶段流水线（生成 → 解析）
│   │   ├── prompts.py                     # 阶段专用提示词
│   │   ├── schemas.py                     # 转写数据模型（复用主流程）
│   │   ├── pdf_export.py                  # PDF 导出（浏览器打印 + fpdf2 回退）
│   │   └── docx_export.py                 # .docx 导出
│   │
│   └── web/                               # Web 后端
│       ├── run.py                         # FastAPI 应用入口（uvicorn）
│       ├── auth.py                        # 用户认证（PBKDF2 哈希 + session token）
│       ├── database.py                    # PostgreSQL 连接池 & 表结构初始化
│       ├── models.py                      # CRUD 数据访问层
│       ├── converter.py                   # 数据转换（姓名→ID，日期→时间戳）
│       └── api/
│           ├── app.py                     # 主 API 路由（提取/结果/用户/部门/认证）
│           └── transcription_routes.py    # 转写 API 路由（上传/解析/推送/导出）
│
├── frontend/                              # Vue 3 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── UploadView.vue             # 上传页（.docx / 录音文件 / URL 转写）
│   │   │   ├── ReviewView.vue             # 审阅编辑页（Tiptap 富文本编辑器）
│   │   │   ├── TranscribeView.vue         # 转写结果页（两阶段流程）
│   │   │   ├── AdminView.vue              # 管理页（用户/部门/注册账号 CRUD）
│   │   │   ├── LoginView.vue              # 登录页
│   │   │   └── RegisterView.vue           # 注册页
│   │   ├── components/
│   │   │   ├── MeetingEditor.vue          # Tiptap 富文本编辑组件
│   │   │   ├── ScheduleEditor.vue         # 日程编辑器
│   │   │   └── TagInput.vue               # 标签输入组件
│   │   └── App.vue
│   └── package.json
│
├── data-example/                          # 示例文件
│   ├── input/README.md                    # 使用说明
│   └── output/示例结果.json               # 输出 JSON 格式示例
```

## 企业微信集成（可选）

推送功能需要配置企业微信应用：

1. 登录[企业微信后台](https://work.weixin.qq.com/wework_admin/frame#apps)
2. 创建自建应用，获取 CorpID、AgentId 和 Secret
3. 在 `.env` 中配置 `WECOM_CORP_ID`、`WECOM_CORP_SECRET`、`WECOM_AGENT_ID`
4. 在 Web UI 的"管理"页面导入部门架构和用户映射（姓名 → userid）
5. 解析结果审阅无误后点击"推送" — 支持三种推送：Markdown 消息通知、日历日程、附件文件

## License

MIT
