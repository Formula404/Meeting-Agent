# Meeting Agent — AI 会议纪要生成企业微信自动推送工具

上传一份会议记录 `.docx`，自动调用 LLM 提取结构化信息，支持通过 Web UI 审阅编辑，并可一键推送到企业微信（日程 + 消息通知 + 附件文件）。
同时支持**录音文件转写**（ASR，含直传与 URL 拉取两种模式）并合并至主解析流程，以及**富文本编辑**与 **PDF/DOCX 导出**。

## 功能特性

- **智能解析** — 读取 .docx 格式会议记录，自动提取会议时间、参会人员、待办日程、正式纪要等结构化信息
- **录音转写** — 上传录音文件（MP3/WAV 等）或提供音频 URL，自动进行语音识别转写（腾讯云 ASR），结果可导入主解析流程生成纪要
- **两阶段转录流程** — 阶段一生成会议纪要草稿 → 用户在线编辑 → 阶段二按部门分解工作任务与日程
- **富文本编辑** — 集成 Tiptap 编辑器，解析结果支持在线富文本编辑（加粗、斜体、下划线、标题、对齐等）
- **PDF 导出** — 编辑完成的会议纪要可一键导出为带格式的 PDF 文件（优先浏览器无头打印，回退 fpdf2 引擎）
- **DOCX 导出** — 支持导出为 .docx 格式，方便线下分发
- **用户认证系统** — Web UI 注册登录，admin/user 角色权限管理，多用户数据隔离
- **企业微信推送** — 支持将会议纪要发送到指定部门/人员，同时自动创建日程，并支持附件（PDF/.docx）文件推送
- **CLI / Web 双模式** — 既可以命令行一键处理，也支持 Web 界面上传管理
- **LLM 无关** — 兼容任意 OpenAI 格式的 API（DeepSeek、OpenAI、通义千问等）

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | Python 3.11+ / FastAPI |
| 前端 | Vue 3 + Vite + Tiptap |
| LLM SDK | LangChain (OpenAI-compatible) |
| 文档解析 | python-docx |
| 语音识别 | 腾讯云 ASR SDK（支持直传 ≤5MB 与 URL 拉取两种模式） |
| PDF 导出 | 浏览器无头打印（Edge/Chrome）+ fpdf2 回退 |
| 数据校验 | Pydantic |
| 数据存储 | PostgreSQL（连接池管理） |
| 认证 | PBKDF2-HMAC-SHA256 密码哈希 + session token |
| 包管理 | uv |

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 18+
- uv（推荐）或 pip
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
DATABASE_URL=postgresql://user:password@host:5432/dbname

# 腾讯云 ASR 配置（录音转写需要）
TENCENT_SECRET_ID=your-secret-id
TENCENT_SECRET_KEY=your-secret-key

# Web 管理员账号（可选，首次启动自动创建 admin 用户）
ADMIN_PASSWORD=your-admin-password
```

> 企业微信相关配置**可选**，不配则无法使用推送功能，解析和审阅功能不受影响。

### 2. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

### 3. 运行

首次运行 Web API 会自动创建 `data/` 目录（含 `input/`、`output/` 子目录）和数据库表结构。

**CLI 模式** — 解析一篇会议记录：

```bash
uv run python main.py 你的会议记录.docx
```

结果将打印到终端，同时自动保存到 `data/output/` 目录。

**Web UI 模式** — 启动管理界面：

```bash
# 终端 1：启动后端 API
uv run python -m meeting_agent.web.run

# 终端 2：启动前端开发服务器
cd frontend && npm run dev
```

浏览器打开 `http://localhost:5173` 即可使用。

## 部署

### Docker Compose（推荐）

项目根目录提供 `Dockerfile`（多阶段构建：Node 编译前端 → Python 运行时）和 `docker-compose.yml`，一键启动所有服务。

```bash
# 1. 确保已配置 .env（至少需要 LLM API 密钥 + DATABASE_URL）
cp .env.example .env
# 编辑 .env 填入必要配置

# 2. 启动（-d 表示后台运行）
docker compose up -d

# 3. 查看日志
docker compose logs -f meeting-agent
```

首次启动会自动完成：表结构初始化 → 前端构建 → 后端启动。
访问 `http://localhost:8000` 即可使用。

> **注意事项：**
> - `docker-compose.yml` 默认暴露 `8000` 端口，如需更改请修改 `ports` 映射
> - 上传的文件（.docx / PDF / 录音）保存在宿主机的 `./data/` 目录
> - PostgreSQL 使用宿主机已有数据库（非容器内），需在 `.env` 中配置 `DATABASE_URL`
> - 如需停止并清理数据：`docker compose down -v`（⚠️ 会删除数据库所有数据）

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

生产环境建议使用 `gunicorn + uvicorn workers` 或 `supervisor` 管理进程：

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
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Web UI 流程

```
上传 .docx / 录音  →  LLM 提取 / ASR 转写  →  在线审阅编辑（富文本） →  推送至企业微信 / 导出 PDF/DOCX
                                                           ↓
                                       姓名 → userid 映射（PostgreSQL 用户库）
                                       部门 → dept_id 映射（PostgreSQL 部门库）
                                       日期字符串 → Unix 时间戳
                                       消息通知 + 日历日程 + 附件文件
```

### 转录业务流程（两阶段）

```
┌─ 阶段一 ─────────────────────────────┐
│  上传录音（文件/URL）                  │
│    → 腾讯云 ASR 语音识别              │
│    → LLM 生成会议纪要草稿              │
│    → 用户在线编辑                     │
└──────────────────┬───────────────────┘
                   ↓
┌─ 阶段二 ─────────────────────────────┐
│  编辑完成 → 提交解析                  │
│    → LLM 按部门/中心分解工作任务       │
│    → 提取日程、推送对象                │
│    → 推送企业微信 / 导出存档           │
└──────────────────────────────────────┘
```

## API 接口

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
| `POST` | `/api/extract` | 上传 .docx（可选 PDF 附件）并执行 LLM 提取 |
| `POST` | `/api/extract-from-text` | 直接传入会议纪要文本执行 LLM 提取（用于转录流程） |
| `GET` | `/api/results` | 获取所有解析记录列表（admin 全部，用户只看自己） |
| `GET` | `/api/results/{id}` | 获取单条解析完整数据 |
| `PUT` | `/api/results/{id}` | 更新解析结果（审阅编辑） |
| `DELETE` | `/api/results/{id}` | 删除解析记录 |
| `POST` | `/api/results/{id}/delete` | 兼容 POST 的删除 |
| `POST` | `/api/results/{id}/push` | 推送到企业微信（消息+日程+附件） |
| `POST` | `/api/results/{id}/upload-pdf` | 上传关联 PDF 附件 |
| `GET` | `/api/results/{id}/export-pdf` | 导出会议纪要 PDF |

### 录音转写

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/transcribe` | 上传录音文件（≤5MB），ASR + 生成纪要草稿 |
| `POST` | `/api/transcribe/url` | 通过音频 URL 转写（无大小限制） |
| `GET` | `/api/transcribe/results` | 获取转写记录列表 |
| `GET` | `/api/transcribe/results/{id}` | 获取单条转写数据 |
| `PUT` | `/api/transcribe/results/{id}` | 更新转写结果 |
| `DELETE` | `/api/transcribe/results/{id}` | 删除转写记录 |
| `POST` | `/api/transcribe/results/{id}/parse` | 阶段二：解析会议纪要 → 按部门分解任务 |
| `POST` | `/api/transcribe/results/{id}/push` | 推送转写结果到企业微信 |
| `POST` | `/api/transcribe/results/{id}/export-docx` | 导出为 .docx 文件 |
| `POST` | `/api/transcribe/results/{id}/generate-pdf` | 生成 PDF 文件 |
| `GET` | `/api/transcribe/results/{id}/download-pdf` | 下载生成的 PDF |

### 用户与部门管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET/POST/PUT/DELETE` | `/api/users` | 企业微信用户 CRUD |
| `POST` | `/api/users/import` | 批量导入企业微信用户 |
| `GET/POST/PUT/DELETE` | `/api/departments` | 部门 CRUD |
| `POST` | `/api/departments/import` | 批量导入部门 |
| `GET/POST/DELETE` | `/api/web-users` | Web 登录账号管理（admin 专属） |

## 项目结构

```
meeting-agent/
├── main.py                                # CLI 入口
├── pyproject.toml                         # Python 项目配置
├── .env.example                           # 环境变量模板
├── meeting_agent/
│   ├── workflow.py                        # 主解析流水线编排（.docx 提取 + 文本提取）
│   ├── document_loader.py                 # .docx 解析（段落 + 表格）
│   ├── llm.py                             # LLM 客户端初始化
│   ├── prompts.py                         # 系统提示词 + 用户提示词模板
│   ├── schemas.py                         # Pydantic 数据模型
│   ├── config.py                          # 环境变量读取（Settings 单例）
│   ├── tools/                             # 工具包占位
│   ├── integrations/
│   │   ├── wecom_client.py                # 企业微信基础客户端（token 管理、HTTP 重试）
│   │   ├── wecom_message_client.py        # 消息推送
│   │   ├── wecom_calendar_client.py       # 日历日程创建
│   │   └── wecom_file_client.py           # 附件文件上传与推送
│   ├── services/
│   │   ├── message_service.py             # 推送消息业务逻辑
│   │   ├── schedule_service.py            # 创建日程业务逻辑
│   │   ├── file_service.py                # 推送附件文件业务逻辑
│   │   └── asr_service.py                 # 腾讯云语音识别（直传 + URL 拉取）
│   ├── transcription/                     # 录音转写模块
│   │   ├── workflow.py                    # 两阶段流水线（生成纪要 + 任务分解）
│   │   ├── pdf_export.py                  # PDF 导出（浏览器打印 + fpdf2 回退）
│   │   ├── docx_export.py                 # .docx 导出
│   │   ├── prompts.py                     # 两阶段专用提示词
│   │   └── schemas.py                     # 转写数据模型（复用主流程）
│   └── web/
│       ├── run.py                         # FastAPI 启动入口（uvicorn）
│       ├── auth.py                        # 用户认证（PBKDF2 哈希 + session token）
│       ├── database.py                    # PostgreSQL 连接池 & 表结构初始化
│       ├── models.py                      # CRUD 数据访问层
│       ├── converter.py                   # 数据转换（姓名→ID，日期→时间戳）
│       └── api/
│           ├── app.py                     # 主 API 路由（提取、用户、部门、认证）
│           └── transcription_routes.py    # 转写 API 路由
├── frontend/                              # Vue 3 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── UploadView.vue             # 上传页（.docx 上传 / 录音上传 / URL 转写）
│   │   │   ├── ReviewView.vue             # 审阅编辑页（Tiptap 富文本）
│   │   │   ├── TranscribeView.vue         # 转写结果页（两阶段流程）
│   │   │   ├── AdminView.vue              # 管理页（用户/部门/注册账号管理）
│   │   │   ├── LoginView.vue              # 登录页
│   │   │   └── RegisterView.vue           # 注册页
│   │   ├── components/
│   │   │   ├── MeetingEditor.vue          # 富文本编辑组件（Tiptap）
│   │   │   ├── ScheduleEditor.vue         # 日程编辑器
│   │   │   └── TagInput.vue               # 标签输入组件
│   │   └── App.vue
│   └── package.json
├── data-example/                          # 示例文件
│   ├── input/                             # 存放 .docx 的位置示意
│   └── output/示例结果.json               # 输出格式示例
```

## 企业微信集成（可选）

推送功能需要配置企业微信应用：

1. 登录[企业微信后台](https://work.weixin.qq.com/wework_admin/frame#apps)
2. 创建自建应用，获取 CorpID、AgentId 和 Secret
3. 在 Web UI 的"管理"页面导入部门架构和用户映射（姓名 → userid）
4. 解析结果审阅无误后点击"推送" — 支持**消息通知**、**日历日程**、**附件文件**推送

## License

MIT
