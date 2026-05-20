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

Test inputs are in `data/input/` (`自动发送测试会议.docx` is the latest test file); outputs go to `data/output/` as `*_result.json`. Optional PDF attachments go to `data/input/pdfs/`. Uploaded audio files used by ASR go to `data/input/transcriptions/audio/`.

## Project Architecture

**Purpose**: Read Chinese meeting minutes (.docx / transcription text), extract structured data via LLM, optionally push results to WeChat Work (企业微信). Supports recording transcription via Tencent Cloud ASR, rich text editing, and PDF / DOCX export.

### Data Flow

#### Main extraction (`.docx` / text input)

```
main.py (CLI) or POST /api/extract or POST /api/extract-from-text
  → meeting_agent.workflow.run_meeting_extraction() / run_meeting_extraction_from_text()
      → document_loader.load_docx_text()    # Parse .docx paragraphs + tables
      → llm.get_llm()                       # Init OpenAI-compatible LLM (DeepSeek)
      → prompts.py (SYSTEM_PROMPT + USER_PROMPT_TEMPLATE)
      → LLM.invoke()                        # Returns JSON
      → schemas.MeetingOutput.validate()    # Pydantic validation
      → save to data/output/*_result.json
```

#### Transcription (two-phase)

```
Phase 1 — Generate draft:
  POST /api/transcribe (file upload) or POST /api/transcribe/url (URL pull)
    → asr_service.get_transcribed_text() / get_transcribed_text_from_url()
        → Tencent Cloud ASR (CreateRecTask → poll → result)
    → transcription/workflow.run_transcription_extraction()
        → LLM generates meeting text draft (no JSON structure)
    → save to transcription_results table

Phase 2 — Parse into tasks (after user edits):
  POST /api/transcribe/{id}/parse
    → transcription/workflow.run_transcription_parse()
        → LLM extracts tasks by department, schedules, push targets
    → update transcription_results table
```

### Web UI Flow

```
Upload .docx [+ optional .pdf]  →  LLM extraction  →  Review & Edit (Tiptap)  →  Push to WeCom
                                                                                send_meeting_summary_from_result()
                                                                                send_file_from_result() (PDF > docx)
                                                                                create_meeting_schedules_from_result()

Upload recording (file/URL)     →  ASR → LLM draft  →  Edit draft  →  Parse (task breakdown)  →  Push to WeCom
                                                                                                  export PDF/DOCX
```

### Key Modules

| Module | Responsibility |
|--------|---------------|
| `workflow.py` | Orchestrates extraction pipeline (.docx + text) |
| `document_loader.py` | Reads .docx (paragraphs + tables → plain text with `\|` separators) |
| `llm.py` | Creates ChatOpenAI instance from .env config |
| `prompts.py` | System prompt + user prompt template (JSON output format) |
| `schemas.py` | Pydantic models: `MeetingOutput`, `ScheduleItem` |
| `config.py` | Loads .env via python-dotenv into `Settings` singleton |
| `services/asr_service.py` | Tencent Cloud ASR: create task (direct upload / URL pull), poll for result |
| `transcription/workflow.py` | Two-phase pipeline: generate draft → parse tasks |
| `transcription/prompts.py` | Phase-specific prompts (generate / parse) |
| `transcription/pdf_export.py` | PDF export: browser headless print (Edge/Chrome) → fpdf2 fallback |
| `transcription/docx_export.py` | DOCX export via python-docx |
| `integrations/wecom_client.py` | Base WeCom API client (access_token, HTTP, retry) |
| `integrations/wecom_message_client.py` | Send text/markdown messages via WeCom |
| `integrations/wecom_calendar_client.py` | Create schedules via WeCom |
| `integrations/wecom_file_client.py` | Upload temporary media & send file messages via WeCom |
| `services/message_service.py` | Business logic: push meeting summaries to users/depts |
| `services/file_service.py` | Business logic: push attached file (PDF/docx) to users/depts |
| `services/schedule_service.py` | Business logic: batch-create schedules from LLM output |
| `web/run.py` | FastAPI app entry (uvicorn) |
| `web/database.py` | PostgreSQL connection pool & schema init (auto-migration) |
| `web/auth.py` | User auth: PBKDF2-HMAC-SHA256 hashing, session tokens, FastAPI deps |
| `web/models.py` | CRUD for users, departments, extraction_results, transcription_results, sessions, web_users |
| `web/converter.py` | Name→userid / date→timestamp conversion for push |
| `web/api/app.py` | Main API routes (extract, results, users, depts, auth, web-users) |
| `web/api/transcription_routes.py` | Transcription API routes (upload, URL, parse, push, export) |
| `frontend/` | Vue 3 SPA (Vite build, proxy /api → :8000) |

### PostgreSQL Database (via `DATABASE_URL`)

- **users**: `name` (中文姓名), `userid` (企微ID), `department_name` — 约500行
- **web_users**: `username`, `password_hash`, `role` (user/admin), `department_name` — 登录账号
- **sessions**: `user_id`, `token` — 会话认证
- **departments**: `name` (部门名称), `dept_id` (企微部门ID), `parent_dept_id` (上级部门, 自引用 FK)
- **extraction_results**: `id` (UUID), `original_filename`, `pdf_filename`, `result_json` (完整JSON), `status` (draft/pushed), `web_user_id`
- **transcription_results**: `id` (UUID), `original_filename`, `user_prompt`, `result_json`, `status` (draft/pushed), `web_user_id`

### Key Patterns

- **LLM config** (.env): `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `MODEL_NAME` — currently using DeepSeek via OpenAI-compatible API
- **Output parsing**: LLM returns markdown-wrapped JSON → `extract_json_from_text()` regex extracts `{...}` → Pydantic validates
- **Two-phase transcription**: Phase 1 generates plain-text meeting draft (no structure); user edits; Phase 2 parses into structured tasks/schedules/push targets. Two separate LLM calls with different prompts.
- **PDF export dual engine**: Try browser headless print first (`msedge` / `chrome` / `chromium` via subprocess), fall back to `fpdf2`-based engine. `export_to_pdf()` for plain text, `export_to_pdf_from_html()` for rich HTML. Both share `MeetingPDF` (FPDF subclass with CJK font handling).
- **WeCom client hierarchy**: `WeComClient` (base, handles token + HTTP) → `WeComMessageClient` / `WeComCalendarClient` / `WeComFileClient` (single-method subclasses). `WeComFileClient` uses `httpx` for multipart file upload, parent `_request()` for JSON calls.
- **Service layer**: stateless module-level functions, instantiate WeCom clients at module level
- **Auth**: PBKDF2-HMAC-SHA256 password hashing (600K iterations, 32-byte salt), session tokens via FastAPI `Depends(get_current_user)`. Admin-only endpoints via `Depends(require_admin)`. Session stored in `sessions` table.
- **Database**: Connection pool via psycopg2 `ThreadedConnectionPool` (min 2, max 10). `_PoolConnectionWrapper` returns connections to pool on `.close()` so existing `try/finally` patterns work unchanged. Auto-migration via `information_schema` column checks.
- **Default admin seeding**: If `ADMIN_PASSWORD` env var is set and no admin user exists, auto-creates one on first `import`.
- **Pydantic fields**: use `default` for single values (can be overridden by LLM), `default_factory` for lists. `TranscriptionOutput` inherits from `MeetingOutput` for push-flow compatibility.
- **Result ownership**: Both `extraction_results` and `transcription_results` have `web_user_id` FK; admin sees all records, non-admin users see only their own.
