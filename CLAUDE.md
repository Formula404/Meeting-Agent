# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
# Activate virtual environment (Python 3.11+)
source .venv/bin/activate

# CLI: Run meeting extraction (input .docx -> structured JSON output)
uv run python main.py data/input/<meeting-file>.docx

# Web UI: Start backend API server (port 8000)
uv run python -m meeting_agent.web.run

# Web UI: Start frontend dev server (port 5173, proxies /api -> :8000)
cd frontend && npm run dev
```

Test inputs are in `data/input/` (`自动发送测试会议.docx` is the latest test file); outputs go to `data/output/` as `*_result.json`. Optional PDF attachments go to `data/input/pdfs/`.

## Project Architecture

**Purpose**: Read Chinese meeting minutes (.docx), extract structured data via LLM, optionally push results to WeChat Work (企业微信).

### Data Flow

```
main.py (CLI)
  → meeting_agent.workflow.run_meeting_extraction()
      → document_loader.load_docx_text()    # Parse .docx paragraphs + tables
      → llm.get_llm()                       # Init OpenAI-compatible LLM (DeepSeek)
      → prompts.py (SYSTEM_PROMPT + USER_PROMPT_TEMPLATE)
      → LLM.invoke()                        # Returns JSON
      → schemas.MeetingOutput.validate()    # Pydantic validation
      → save to data/output/*_result.json
```

Post-extraction (optional, via web UI push):
- `services/message_service.py` → send meeting text (markdown) to WeCom users/departments
- `services/file_service.py` → send attached file (PDF preferred, docx fallback) via WeCom temporary media
- `services/schedule_service.py` → create WeCom calendar schedules

### Key Modules

| Module | Responsibility |
|--------|---------------|
| `workflow.py` | Orchestrates the full extraction pipeline |
| `document_loader.py` | Reads .docx (paragraphs + tables → plain text with `\|` separators) |
| `llm.py` | Creates ChatOpenAI instance from .env config |
| `prompts.py` | System prompt + user prompt template (JSON output format) |
| `schemas.py` | Pydantic models: `MeetingOutput`, `ScheduleItem` |
| `config.py` | Loads .env via python-dotenv into `Settings` dataclass |
| `integrations/wecom_client.py` | Base WeCom API client (access_token, HTTP, retry) |
| `integrations/wecom_message_client.py` | Send text/markdown messages via WeCom |
| `integrations/wecom_calendar_client.py` | Create schedules via WeCom |
| `integrations/wecom_file_client.py` | Upload temporary media & send file messages via WeCom |
| `services/message_service.py` | Business logic: push meeting summaries to users/depts |
| `services/file_service.py` | Business logic: push attached file (PDF/docx) to users/depts |
| `services/schedule_service.py` | Business logic: batch-create schedules from LLM output |
| `web/run.py` | FastAPI app entry (uvicorn) |
| `web/api/app.py` | All REST API routes (extract, results, users, depts) |
| `web/database.py` | PostgreSQL connection pool & schema init |
| `web/models.py` | CRUD for users, departments, extraction_results |
| `web/converter.py` | Name→userid / date→timestamp conversion for push |
| `frontend/` | Vue 3 SPA (Vite build, proxy /api → :8000) |

### Web UI Flow

```
Upload .docx [+ optional .pdf]  →  LLM extraction  →  Review & Edit Form  →  Push to WeCom
                                                      ↓                          ↓
                                              Change/upload PDF          send_meeting_summary_from_result()
                                              (via upload-pdf API)       send_file_from_result() (PDF > docx)
                                                                         create_meeting_schedules_from_result()
                                                      ↓
                                        Name→userid (SQLite users)
                                        Dept name→dept_id (SQLite departments)
                                        Date string→Unix timestamp
```

### PostgreSQL Database (via `DATABASE_URL`)

- **users**: `name` (中文姓名), `userid` (企微ID), `department_name` — 约500行
- **web_users**: `username`, `password_hash`, `role` (user/admin), `department_name` — 登录账号
- **sessions**: `user_id`, `token` — 会话认证
- **departments**: `name` (部门名称), `dept_id` (企微部门ID)
- **extraction_results**: `id` (UUID), `original_filename`, `pdf_filename`, `result_json` (完整JSON), `status` (draft/pushed), `web_user_id`
- **transcription_results**: `id` (UUID), `original_filename`, `user_prompt`, `result_json`, `status`, `web_user_id`

### Key Patterns

- **LLM config** (.env): `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `MODEL_NAME` — currently using DeepSeek via OpenAI-compatible API
- **Output parsing**: LLM returns markdown-wrapped JSON → `extract_json_from_text()` regex extracts `{...}` → Pydantic validates
- **WeCom client hierarchy**: `WeComClient` (base, handles token + HTTP) → `WeComMessageClient` / `WeComCalendarClient` / `WeComFileClient` (single-method subclasses). `WeComFileClient` uses `httpx` for multipart file upload, parent `_request()` for JSON calls.
- **Service layer**: stateless module-level functions, instantiate WeCom clients at module level
- **Pydantic fields**: use `default` for single values (can be overridden by LLM), `default_factory` for lists
