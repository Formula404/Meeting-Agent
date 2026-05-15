# Meeting Agent — AI 会议纪要生成企业微信自动推送工具

上传一份会议记录 `.docx`，自动调用 LLM 提取结构化信息，支持通过 Web UI 审阅编辑，并可一键推送到企业微信（日程 + 消息通知）。  
同时支持**录音文件转写**（ASR）并合并至主解析流程，以及**富文本编辑**与**PDF 导出**。

## 功能特性

- **智能解析** — 读取 .docx 格式会议记录，自动提取会议时间、参会人员、待办日程、正式纪要等结构化信息
- **录音转写** — 上传录音文件（MP3/WAV 等），自动进行语音识别转写，结果可导入主解析流程生成纪要
- **富文本编辑** — 集成 Tiptap 编辑器，解析结果支持在线富文本编辑（加粗、斜体、下划线、标题等）
- **PDF 导出** — 编辑完成的会议纪要可一键导出为带格式的 PDF 文件
- **企业微信推送** — 支持将会议纪要发送到指定部门/人员，同时自动创建日程，并支持附件（PDF/.docx）文件推送
- **CLI / Web 双模式** — 既可以命令行一键处理，也支持 Web 界面上传管理
- **LLM 无关** — 兼容任意 OpenAI 格式的 API（DeepSeek、OpenAI、通义千问等）
- **用户系统** — 支持 Web UI 注册登录，多用户隔离管理

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | Python 3.11+ / FastAPI |
| 前端 | Vue 3 + Vite + Tiptap |
| LLM SDK | LangChain (OpenAI-compatible) |
| 文档解析 | python-docx |
| 语音识别 | OpenAI 兼容 ASR API |
| PDF 导出 | WeasyPrint + HTML/CSS |
| 数据校验 | Pydantic |
| 数据存储 | PostgreSQL |
| 包管理 | uv |

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 18+
- uv（推荐）或 pip
- WeasyPrint 系统依赖（PDF 导出需用，见 [WeasyPrint 安装文档](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation)）

### 1. 克隆并配置

```bash
git clone https://github.com/your-username/meeting-agent.git
cd meeting-agent

# 创建虚拟环境并安装依赖
uv sync

# 配置环境变量
cp .env.example .env
```

编辑 `.env`，填入你的 LLM API 密钥（以 DeepSeek 为例）：

```ini
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
TEMPERATURE=0.2
```

> 企业微信相关配置**可选**，不配则无法使用推送功能，解析和审阅功能不受影响。

### 2. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

### 3. 运行

首次运行 Web API 会自动创建 `data/` 目录（含 `input/`、`output/` 子目录）。

**数据库**：使用 PostgreSQL，需在 `.env` 中配置 `DATABASE_URL`：

```ini
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

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

项目根目录提供 `Dockerfile`（多阶段构建：Node 编译前端 → Python 运行时）和 `docker-compose.yml`（含 PostgreSQL），一键启动所有服务。

```bash
# 1. 确保已配置 .env（至少需要 LLM API 密钥）
cp .env.example .env
# 编辑 .env 填入必要配置

# 2. 启动（-d 表示后台运行）
docker compose up -d

# 3. 查看日志
docker compose logs -f meeting-agent
```

首次启动会自动完成：PostgreSQL 数据库创建 → 表结构初始化 → 前端构建 → 后端启动。  
访问 `http://localhost:8000` 即可使用（开发时前端访问 `http://localhost:5173` 有热更新）。

> **注意事项：**
> - `docker-compose.yml` 默认暴露 `8000` 端口，如需更改请修改 `ports` 映射
> - 上传的文件（.docx / PDF）保存在宿主机的 `./data/` 目录
> - PostgreSQL 数据存储在 Docker 卷 `pgdata` 中，`docker compose down` 不会丢失数据
> - 如需停止并清理数据：`docker compose down -v`（⚠️ 会删除数据库所有数据）

### 手动部署（生产环境）

无 Docker 环境时，可直接在服务器上运行：

```bash
# 1. 安装系统依赖（PDF 导出需要 WeasyPrint）
#   Ubuntu/Debian:
#     sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
#   CentOS/RHEL:
#     sudo yum install pango pango-devel cairo cairo-devel gdk-pixbuf2 libffi-devel

# 2. 安装 Python 依赖
uv sync --no-dev

# 3. 构建前端
cd frontend
npm ci
npm run build
cd ..

# 4. 启动（生产模式，自带前端静态文件服务）
uv run uvicorn meeting_agent.web.run:app --host 0.0.0.0 --port 8000
```

生产环境建议使用 `gunicorn + uvicorn workers` 或 `supervisor` 管理进程:

```bash
# 安装 gunicorn
uv pip install gunicorn

# 启动（4 个 worker 进程）
uv run gunicorn meeting_agent.web.run:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers 4
```

### Nginx 反向代理（可选）

如需通过 Nginx 暴露服务并配置 HTTPS：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 上传文件大小限制（docx 通常 10MB+）
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
上传 .docx / 录音  →  LLM 提取 / ASR 转写  →  在线审阅编辑（富文本） →  推送至企业微信 / 导出 PDF
                                                           ↓
                                       姓名 → userid 映射（PostgreSQL 用户库）
                                       部门 → dept_id 映射（PostgreSQL 部门库）
                                       日期字符串 → Unix 时间戳
                                       消息通知 + 日历日程 + 附件文件
```

## API 接口

### 会议纪要

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/extract` | 上传 .docx 并执行 LLM 提取 |
| `GET` | `/api/results` | 获取所有解析记录列表 |
| `GET` | `/api/results/{id}` | 获取单条解析完整数据 |
| `PUT` | `/api/results/{id}` | 更新解析结果（审阅编辑） |
| `DELETE` | `/api/results/{id}` | 删除解析记录 |
| `POST` | `/api/results/{id}/push` | 推送到企业微信 |
| `POST` | `/api/results/{id}/upload-pdf` | 上传关联 PDF 附件 |
| `GET` | `/api/results/{id}/export-pdf` | 导出会议纪要 PDF |

### 录音转写

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/transcribe/upload` | 上传录音文件 |
| `GET` | `/api/transcribe/results` | 获取转写记录列表 |
| `GET` | `/api/transcribe/results/{id}` | 获取单条转写结果与全文 |
| `DELETE` | `/api/transcribe/results/{id}` | 删除转写记录 |
| `POST` | `/api/transcribe/results/{id}/extract` | 将转写文本导入主解析流程 |

### 用户与部门管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET/POST/PUT/DELETE` | `/api/users` | 企业微信用户 CRUD |
| `POST` | `/api/users/import` | 批量导入企业微信用户 |
| `GET/POST/PUT/DELETE` | `/api/departments` | 部门 CRUD |
| `POST` | `/api/departments/import` | 批量导入部门 |

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/auth/register` | 注册管理账号 |
| `POST` | `/api/auth/login` | 登录获取 token |
| `POST` | `/api/auth/logout` | 登出 |
| `GET` | `/api/auth/me` | 获取当前用户信息 |

## 项目结构

```
meeting-agent/
├── main.py                                # CLI 入口
├── pyproject.toml                         # Python 项目配置
├── .env.example                           # 环境变量模板
├── meeting_agent/
│   ├── workflow.py                        # 主解析流水线编排
│   ├── document_loader.py                 # .docx 解析（段落 + 表格）
│   ├── llm.py                             # LLM 客户端初始化
│   ├── prompts.py                         # 系统提示词 + 用户提示词模板
│   ├── schemas.py                         # Pydantic 数据模型
│   ├── config.py                          # 环境变量读取
│   ├── tools/                             # 工具包占位
│   ├── integrations/
│   │   ├── wecom_client.py                # 企业微信基础客户端（token 管理、HTTP）
│   │   ├── wecom_message_client.py        # 消息推送
│   │   ├── wecom_calendar_client.py       # 日历日程创建
│   │   └── wecom_file_client.py           # 附件文件上传与推送
│   ├── services/
│   │   ├── message_service.py             # 推送消息业务逻辑
│   │   ├── schedule_service.py            # 创建日程业务逻辑
│   │   ├── file_service.py                # 推送附件文件业务逻辑
│   │   └── asr_service.py                 # 语音识别服务（OpenAI ASR）
│   ├── transcription/                     # 录音转写模块
│   │   ├── workflow.py                    # 转写 & 解析流水线
│   │   ├── pdf_export.py                  # PDF 导出（WeasyPrint + HTML/CSS）
│   │   ├── docx_export.py                 # .docx 导出
│   │   ├── prompts.py                     # 转写专用提示词
│   │   └── schemas.py                     # 转写数据模型
│   └── web/
│       ├── run.py                         # FastAPI 启动入口
│       ├── auth.py                        # 用户认证（注册/登录/鉴权）
│       ├── database.py                    # PostgreSQL 连接池 & 数据库初始化
│       ├── models.py                      # CRUD 数据访问层
│       ├── converter.py                   # 数据转换（姓名→ID，日期→时间戳）
│       └── api/
│           ├── app.py                     # 主 API 路由（纪要、用户、部门）
│           └── transcription_routes.py    # 转写 API 路由
├── frontend/                              # Vue 3 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── UploadView.vue             # 上传页（.docx 上传 或 录音上传）
│   │   │   ├── ReviewView.vue             # 审阅编辑页（Tiptap 富文本）
│   │   │   ├── TranscribeView.vue         # 转写结果页
│   │   │   ├── AdminView.vue              # 管理页（用户/部门/注册账号）
│   │   │   ├── LoginView.vue              # 登录页
│   │   │   └── RegisterView.vue           # 注册页
│   │   ├── components/
│   │   │   ├── MeetingEditor.vue          # 富文本编辑组件
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
