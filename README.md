# Meeting Agent — AI 会议纪要结构化提取工具

上传一份会议记录 `.docx`，自动调用 LLM 提取结构化信息，支持通过 Web UI 审阅编辑，并可一键推送到企业微信（日程 + 消息通知）。

## 功能特性

- **智能解析** — 读取 .docx 格式会议记录，自动提取会议时间、参会人员、待办日程、正式纪要等结构化信息
- **Web 审阅** — 内置 Vue 3 管理界面，解析结果可在线编辑修改
- **企业微信推送** — 支持将会议纪要发送到指定部门/人员，同时自动创建日程
- **CLI / Web 双模式** — 既可以命令行一键处理，也支持 Web 界面上传管理
- **LLM 无关** — 兼容任意 OpenAI 格式的 API（DeepSeek、OpenAI、通义千问等）

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | Python 3.11+ / FastAPI |
| 前端 | Vue 3 + Vite |
| LLM SDK | LangChain (OpenAI-compatible) |
| 文档解析 | python-docx |
| 数据校验 | Pydantic |
| 数据存储 | PostgreSQL |
| 包管理 | uv |

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 18+
- uv（推荐）或 pip

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

## Web UI 流程

```
上传 .docx  →  LLM 自动提取  →  在线审阅编辑  →  推送至企业微信
                                                  ↓
                              姓名 → userid 映射（PostgreSQL 用户库）
                              部门 → dept_id 映射（PostgreSQL 部门库）
                              日期字符串 → Unix 时间戳
                              消息通知 + 日历日程
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/extract` | 上传 .docx 并执行 LLM 提取 |
| `GET` | `/api/results` | 获取所有解析记录列表 |
| `GET` | `/api/results/{id}` | 获取单条解析完整数据 |
| `PUT` | `/api/results/{id}` | 更新解析结果（审阅编辑） |
| `POST` | `/api/results/{id}/push` | 推送到企业微信 |
| `GET/POST/PUT/DELETE` | `/api/users` | 用户 CRUD |
| `GET/POST/PUT/DELETE` | `/api/departments` | 部门 CRUD |

## 项目结构

```
meeting-agent/
├── main.py                        # CLI 入口
├── pyproject.toml                 # Python 项目配置
├── .env.example                   # 环境变量模板（无需修改）
├── meeting_agent/
│   ├── workflow.py                # 解析流水线编排
│   ├── document_loader.py         # .docx 解析（段落 + 表格）
│   ├── llm.py                     # LLM 客户端初始化
│   ├── prompts.py                 # 系统提示词 + 用户提示词模板
│   ├── schemas.py                 # Pydantic 数据模型
│   ├── config.py                  # 环境变量读取
│   ├── integrations/
│   │   ├── wecom_client.py        # 企业微信基础客户端（token 管理、HTTP）
│   │   ├── wecom_message_client.py# 消息推送
│   │   └── wecom_calendar_client.py # 日历日程创建
│   ├── services/
│   │   ├── message_service.py     # 推送消息业务逻辑
│   │   └── schedule_service.py    # 创建日程业务逻辑
│   └── web/
│       ├── run.py                 # FastAPI 启动入口
│       ├── database.py            # PostgreSQL 连接池 & 数据库初始化
│       ├── models.py              # CRUD 数据访问层
│       ├── converter.py           # 数据转换（姓名→ID，日期→时间戳）
│       └── api/app.py             # 所有 API 路由
├── frontend/                      # Vue 3 前端
│   ├── src/
│   │   ├── views/                 # 页面：上传、审阅、管理
│   │   ├── components/            # 组件：日程编辑器、标签输入
│   │   └── App.vue
│   └── package.json
├── data-example/                  # 示例文件
│   ├── input/                     # 存放 .docx 的位置示意
│   └── output/示例结果.json       # 输出格式示例
```

## 企业微信集成（可选）

推送功能需要配置企业微信应用：

1. 登录[企业微信后台](https://work.weixin.qq.com/wework_admin/frame#apps)
2. 创建自建应用，获取 CorpID、AgentId 和 Secret
3. 在 Web UI 的"管理"页面导入部门架构和用户映射（姓名 → userid）
4. 解析结果审阅无误后点击"推送"

## License

MIT
