# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Build & Run

```bash
# Activate virtual environment (Python 3.11+)
source .venv/bin/activate

# CLI: Run meeting extraction (input .docx -> structured JSON output)
uv run python main.py data/input/<meeting-file>.docx

# Web UI: Start backend API server (port 8000, reload enabled)
uv run python -m meeting_agent.web.run

# Web UI: Start background task worker (polls DB for pending tasks)
uv run python -m meeting_agent.worker

# Web UI: Start frontend dev server (port 5173, proxies /api -> :8000)
cd frontend && npm run dev
```

Test inputs go in `data/input/` (`自动发送测试会议.docx` is the latest test file); outputs go to `data/output/` as `*_result.json`. Optional PDF attachments go to `data/input/pdfs/`. Uploaded audio files for ASR go to `data/input/transcriptions/audio/`.

## Project Architecture

**Purpose**: Read Chinese meeting minutes (.docx / transcription text / recording), extract structured data via LLM, optionally push results to WeChat Work (企业微信). Supports recording transcription via Tencent Cloud ASR (with tflink proxy for files >5MB), rich text editing via Tiptap, and PDF / DOCX export.

### Module Map

| Package | Module | Responsibility |
|---------|--------|---------------|
| **root** | `workflow.py` | Orchestrates extraction pipeline (both .docx and text inputs) |
| | `worker.py` | Background task worker: polls `background_tasks` table, dispatches ASR/LLM tasks to thread pool |
| | `document_loader.py` | Reads .docx paragraphs + tables → plain text with `\|` separators |
| | `llm.py` | Creates ChatOpenAI instance from `.env` config (model, base URL, key, temperature) |
| | `prompts.py` | System prompt + user prompt template (JSON output format) |
| | `schemas.py` | Pydantic models: `MeetingOutput`, `ScheduleItem` |
| | `config.py` | Loads `.env` via python-dotenv into `Settings` dataclass singleton |
| **services/** | `asr_service.py` | Tencent Cloud ASR: 3 modes — direct upload (≤5MB), URL pull (unlimited), tflink proxy (≤100MB) |
| | `tflink_service.py` | Anonymous file upload to `tmpfile.link` to get a public URL for ASR |
| | `message_service.py` | Format meeting text as Markdown, split into ≤2000-byte chunks, push via WeCom |
| | `schedule_service.py` | Batch-create WeCom calendar schedules from LLM output, validate timestamps |
| | `file_service.py` | Resolve and push attached files (PDF priority, .docx fallback) via WeCom |
| **integrations/** | `wecom_client.py` | Base client: token management (cached, 60s safety margin), unified `_request()` with auto-retry on 40014/42001 |
| | `wecom_message_client.py` | `send_text_message()` / `send_markdown_message()` — inherits token/request from base |
| | `wecom_calendar_client.py` | `create_schedule()` — single-method, inherits base |
| | `wecom_file_client.py` | `upload_media()` via httpx multipart + `send_file_message()` — inherits base |
| **transcription/** | `workflow.py` | Two-phase pipeline: `run_transcription_extraction()` (generate draft) → `run_transcription_parse()` (break down tasks) |
| | `prompts.py` | Phase-specific prompts: GENERATE (plain text draft) vs PARSE (structured JSON with per-dept task breakdown) |
| | `schemas.py` | `TranscriptionOutput` inherits `MeetingOutput` for push-flow compatibility |
| | `pdf_export.py` | Dual engine: browser headless print (msedge/chrome/chromium via subprocess) → fpdf2 fallback. Supports both plain text (`export_to_pdf`) and HTML (`export_to_pdf_from_html`). Custom `_HtmlParser` class for HTML→PDF rendering. |
| | `docx_export.py` | DOCX export via python-docx: heading, info table, schedule table |
| **web/** | `run.py` | FastAPI app creation, CORS (→localhost:5173), static files mount, SPA catch-all |
| | `auth.py` | PBKDF2-HMAC-SHA256 (600K iterations, 32-byte salt), `get_current_user`/`require_admin` FastAPI dependencies |
| | `database.py` | psycopg2 `ThreadedConnectionPool` (min 2, max 10), `_PoolConnectionWrapper` returns connections on close, auto-migration via `information_schema` column checks |
| | `models.py` | CRUD for users, departments, web_users, sessions, extraction_results, transcription_results, background_tasks |
| | `converter.py` | Name→userid / dept name→dept_id / date string→Unix timestamp conversion for push |
| | `api/app.py` | Main routes: extract, extract-from-text, tasks CRUD, results CRUD, push, auth, users/depts/web-users CRUD |
| | `api/transcription_routes.py` | Transcription routes: upload (file/URL), results CRUD, parse, push, export (.docx/PDF) |
| **frontend/** | Vue 3 SPA | Views: UploadView, ReviewView, TranscribeView, AdminView, LoginView, RegisterView. Components: MeetingEditor (Tiptap), ScheduleEditor, TagInput. |

### Data Flow

#### Main extraction (`.docx` / text input)

```
main.py (CLI) or POST /api/extract or POST /api/extract-from-text
  → create_background_task()                # Enqueue task in DB, return task_id immediately
  → Worker picks up: claim_next_background_task()
  → workflow.run_meeting_extraction() / run_meeting_extraction_from_text()
      → document_loader.load_docx_text()    # Parse .docx paragraphs + tables → plain text
      → llm.get_llm()                       # Init ChatOpenAI from config
      → prompts.py (SYSTEM_PROMPT + USER_PROMPT_TEMPLATE with {meeting_text})
      → LLM.invoke()                        # Returns raw text with JSON
      → extract_json_from_text()            # Regex to strip ```json``` and extract {...}
      → schemas.MeetingOutput.validate()    # Pydantic parse & validate
      → save to data/output/*_result.json   # CLI only; Web saves to DB
      → complete_background_task()          # Mark task success with result_id
  → Frontend polling GET /api/tasks/{task_id} until status='success'
```

#### Transcription (two-phase)

```
Phase 1 — Generate draft (async via worker):
  POST /api/transcribe (file upload, ≤100MB via tflink proxy)  or  POST /api/transcribe/url
    → create_background_task()              # Enqueue task (transcribe_file / transcribe_url)
    → return { task_id } to frontend immediately
    → Worker picks up: claim_next_background_task()
    → tflink_service.upload_to_tflink()     # Anonymous upload → public download URL (file mode only)
    → asr_service.get_transcribed_text_via_proxy() or get_transcribed_text_from_url()
        → create_rec_task_from_url(url)     # Tencent Cloud ASR URL-pull mode
        → poll DescribeTaskStatus until done or timeout (30 min max)
    → transcription/workflow.run_transcription_extraction()
        → LLM generates plain-text meeting draft (no JSON structure)
        → Uses meeting basic info (name, time, location, chair, attendees) to improve accuracy
    → save to transcription_results table
    → complete_background_task()            # Mark task success with result_id
  → Frontend polling GET /api/tasks/{task_id} until status='success'

Phase 2 — Parse into tasks (after user edits):
  POST /api/transcribe/{id}/parse
    → transcription/workflow.run_transcription_parse(meeting_text)
        → LLM with PARSE_SYSTEM_PROMPT: extracts tasks grouped by department/center
        → Returns structured JSON: meeting_date, push_dept, push_user, schedules, meeting (text)
    → update transcription_results table with parsed data
```

#### Push flow

```
POST /api/results/{id}/push or POST /api/transcribe/{id}/push
  → convert_result_for_push()               # Converts Chinese names → userids, dept names → dept_ids, dates → timestamps
      → Looks up from users + departments tables
  → send_meeting_summary_from_result()       # Format meeting as Markdown, split into ≤2000-byte chunks, send
  → send_file_from_result()                  # Find file (PDF > .docx), upload to WeCom temp media, send
  → create_meeting_schedules_from_result()   # Batch-create calendar schedules from LLM output
  → mark_result_pushed()                     # Update status='pushed' + pushed_at timestamp
```

### Database Schema (PostgreSQL)

All tables created/auto-migrated in `web/database.py:init_db()` via `information_schema` column checks.

- **users**: `id SERIAL PK`, `name TEXT UNIQUE` (中文姓名), `userid TEXT UNIQUE` (企微ID), `department_name TEXT`, `created_at`, `updated_at`
- **web_users**: `id SERIAL PK`, `username TEXT UNIQUE` (登录名), `password_hash TEXT`, `role TEXT CHECK(role IN ('user','admin'))`, `department_name TEXT`, `created_at`, `updated_at`
- **sessions**: `id SERIAL PK`, `user_id INT FK→web_users(id) ON DELETE CASCADE`, `token TEXT UNIQUE`, `created_at`
- **departments**: `id SERIAL PK`, `name TEXT UNIQUE` (部门名称), `dept_id INT UNIQUE` (企微部门ID), `parent_dept_id INT FK→departments(dept_id) ON DELETE SET NULL`, `created_at`, `updated_at`
- **extraction_results**: `id TEXT PK` (UUID), `original_filename TEXT`, `pdf_filename TEXT`, `web_user_id INT FK→web_users(id) ON DELETE SET NULL`, `status TEXT CHECK(IN ('draft','pushed'))`, `result_json TEXT`, `created_at`, `updated_at`, `pushed_at`
- **transcription_results**: Same structure as extraction_results, plus `user_prompt TEXT`
- **background_tasks**: `id TEXT PK` (UUID), `task_type TEXT CHECK(extract_docx|extract_text|transcribe_file|transcribe_url)`, `status TEXT CHECK(pending|running|success|failed)`, `web_user_id INT FK→web_users(id)`, `payload_json TEXT`, `result_type TEXT`, `result_id TEXT`, `error TEXT`, `started_at`, `finished_at`, `created_at`, `updated_at`. Indexed on `(status, task_type, created_at)` for worker polling.

### Key Patterns

#### LLM output parsing
- Both `workflow.py` and `transcription/workflow.py` have their own `extract_json_from_text()` — strips markdown code blocks (````json`), regex `{...}`, `json.loads()`
- Phase 1 (generate): LLM returns **plain text only** (no JSON) — the `meeting` field
- Phase 2 (parse): LLM returns **structured JSON** matching `MeetingOutput` schema
- On parse failure, raw output is saved to `data/output/raw_model_output.txt` or `data/output/parse_raw_output.txt` for debugging

#### PDF export dual engine
- Browser headless print (`_print_html_with_browser`): tries msedge → chrome → chromium via subprocess with `--headless=new` → `--headless` fallback, `--print-to-pdf`, 60s timeout
- fpdf2 fallback (`MeetingPDF` extends FPDF): finds CJK fonts (Windows: msyh.ttc, macOS: PingFang.ttc, Linux: Noto Sans CJK / wqy), supports `CJK` font family with regular/bold/italic/BI variants
- HTML→PDF mode: custom `_HtmlParser` class handles Tiptap HTML subset (h1/h2/h3/p/hr/ul/ol/li, strong/b/em/i/u, text-align)
- CJK font search order: Windows → macOS → Linux (known paths) → `fonts/` directory fallback

#### WeCom client hierarchy
- `WeComClient` (base): `get_access_token()` with caching (7200s TTL, 60s safety margin), `_request()` with auto-retry on errcode 40014/42001
- `WeComMessageClient(WeComClient)`: `send_text_message()`, `send_markdown_message()`
- `WeComCalendarClient(WeComClient)`: `create_schedule()`
- `WeComFileClient(WeComClient)`: `upload_media()` (uses httpx for multipart), `send_file_message()` (uses parent `_request()`)
- Service layer: module-level singletons (`wecom_message_client = WeComMessageClient()`)

#### Database
- `ThreadedConnectionPool` (min 2, max 10) initialized lazily on first `get_connection()`
- `_PoolConnectionWrapper`: wraps psycopg2 connection, `.close()` returns to pool (not actually closes), delegates all other attrs via `__getattr__`
- Auto-migration: `init_db()` creates tables via `CREATE TABLE IF NOT EXISTS`, adds missing columns via `information_schema.columns` checks
- Admin auto-seed: if `ADMIN_PASSWORD` env var is set and no admin exists, creates one on first `import`

#### Authentication
- PBKDF2-HMAC-SHA256, 600K iterations, 32-byte random salt, stored as `$salt_hex$hash_hex`
- Session tokens: `secrets.token_urlsafe(48)`, stored in `sessions` table
- FastAPI dependencies: `get_current_user` (Bearer token → session → user), `require_admin` (check role='admin')
- Result ownership: `web_user_id` FK on both result tables; admin sees all, non-admin only own records

#### Push data conversion
- `convert_result_for_push()` in `web/converter.py`: maps Chinese names → WeCom userids, Chinese dept names → dept_ids, date strings → Unix timestamps
- Uses in-memory dicts from `list_users()` / `list_departments()` — not per-item DB queries
- Unknown names/depts pass through as-is (fallback for WeCom to handle)
- Time parsing: accepts timestamps, `YYYY-MM-DD HH:mm`, `YYYY-MM-DDTHH:mm`, returns 0 for empty/未明确

#### ASR service
- `EngineModelType=16k_zh` (Chinese Mandarin), `ChannelNum=1`, `ResTextFormat=2` (detailed with word timestamps + punctuation)
- 3 upload modes:
  - Direct upload (`SourceType=1`): base64-encoded data, ≤5MB limit
  - URL pull (`SourceType=0`): provide public URL, no size limit (up to 5GB)
  - tflink proxy: upload file to `tmpfile.link` → get download URL → URL pull mode
- Polling: 3s interval, 1800s (30 min) timeout, prints status changes

#### Pydantic field defaults
- `ScheduleItem.owner`: `default=""` (should be `default_factory=list` — known issue, LLM often returns string)
- `MeetingOutput.push_dept / push_user / schedules`: `default_factory=list`
- `TranscriptionOutput` inherits `MeetingOutput` for push-flow compatibility
- Phase 2 `run_transcription_parse()` patches `owner` from string to list after JSON parse

#### Frontend
- Vue 3 SPA with Vue Router, Tiptap v3 (rich text), Vite build
- Proxy `/api` → `http://localhost:8000` in dev mode (configured in vite config)
- `frontend/dist/` is served by FastAPI in production
- Views: Upload (docx/audio/URL), Review (Tiptap editor + Schedule editor), Transcribe (two-phase flow), Admin (CRUD), Login, Register

#### Background Task Worker
- **Worker entry**: `meeting_agent/worker.py:main()` — initializes DB, resets stuck tasks, spawns 2 scheduler loops (extract + transcribe) in a `ThreadPoolExecutor`
- **Extract loop**: claims `extract_docx` / `extract_text` tasks, concurrency controlled by `EXTRACT_WORKER_CONCURRENCY` (default 2)
- **Transcribe loop**: claims `transcribe_file` / `transcribe_url` tasks, concurrency controlled by `TRANSCRIBE_WORKER_CONCURRENCY` (default 2)
- **Polling**: `claim_next_background_task()` uses `SELECT ... FOR UPDATE SKIP LOCKED` to safely claim tasks across multiple worker instances
- **Task lifecycle**: `pending → running → success/failed`. On startup, `reset_running_background_tasks()` resets any stale `running` tasks back to `pending`
- **Frontend polling**: Both `UploadView.vue` and `TranscribeView.vue` poll `GET /api/tasks/{task_id}` every 3s, with a 30-min timeout. Shows user-friendly status messages ("任务排队中...", "后台正在识别并生成会议纪要...")
