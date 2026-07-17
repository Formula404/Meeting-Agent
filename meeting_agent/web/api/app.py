from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from meeting_agent.services.file_service import send_file_from_result
from meeting_agent.services.message_service import send_meeting_summary_from_result
from meeting_agent.services.schedule_service import create_meeting_schedules_from_result
from meeting_agent.web.auth import (
    create_session_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)
from meeting_agent.web.converter import convert_result_for_push
from meeting_agent.web.database import init_db
from meeting_agent.document_loader import load_docx_text
from meeting_agent.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage
from meeting_agent.web.models import (
    create_background_task,
    create_department,
    create_template,
    create_user,
    create_users_batch,
    create_web_user,
    delete_department,
    delete_result,
    delete_session,
    delete_template,
    delete_user,
    delete_web_user,
    get_background_task,
    get_result,
    get_template,
    get_web_user_by_id,
    get_web_user_by_username,
    list_departments,
    list_results,
    list_templates,
    list_users,
    list_web_users,
    mark_result_pushed,
    update_department,
    update_pdf_filename,
    update_result,
    update_result_project,
    update_template,
    update_user,
)

# Ensure DB schema on import
init_db()

# Seed default admin if ADMIN_PASSWORD env var is set and no admin exists
_default_admin_password = os.environ.get("ADMIN_PASSWORD", "")
_admin_user_id = None
if _default_admin_password:
    existing = get_web_user_by_username("admin")
    if existing is None:
        try:
            _pw_hash = hash_password(_default_admin_password)
            admin = create_web_user("admin", _pw_hash, department_name="系统管理", role="admin")
            _admin_user_id = admin["id"]
            print("Default admin user created (username=admin, password from ADMIN_PASSWORD)")
        except Exception:
            pass  # race condition — another instance may have created it
    else:
        _admin_user_id = existing["id"]

# Seed built-in template "景枫周列会"
if _admin_user_id:
    try:
        existing_templates = list_templates()
        if not any(t.get("name") == "模板示例" for t in existing_templates):
            create_template(
                name="模板示例",
                description="系统内置模板示例，按「上周回顾」「本周计划」「需协调事项」三部分组织",
                style_prompt=(
                    "请按以下风格书写会议纪要正文：\n\n"
                    "1. 正文结构分三部分，依次为「上周工作回顾」「本周工作计划」「需协调事项」。\n"
                    "2. 每部分使用 ## 二级标题，标题后空一行再接内容。\n"
                    "3. 具体事项用 - 项目符号列表，每条一行，简洁扼要。\n"
                    "4. 【上周工作回顾】每条格式：- 事项简述 + 完成状态（已完成/进行中/滞后）\n"
                    "5. 【本周工作计划】每条格式：- 事项 + 责任人 + 计划完成时间\n"
                    "6. 【需协调事项】每条格式：- 事项 + 需协调部门/人 + 期望结果\n"
                    "7. 语言正式简洁，用词准确，避免口语化表达。\n"
                    "8. 人名使用「姓+职务」称呼（如张总、李经理），不单独用姓名。\n"
                    "9. 数字、日期、百分比等数据必须准确，不可编造。"
                ),
                sample_output=(
                    "## 上周工作回顾\n"
                    "- 景枫中心幕墙工程 — 已完成 85%，玻璃供货已协调（进行中）\n"
                    "- 招商手册修订 — 已完成排版，待张总终审（已完成）\n\n"
                    "## 本周工作计划\n"
                    "- 完成幕墙工程剩余 15% 工作量 — 李经理 — 6月13日前\n"
                    "- 确定三季度招商方案 — 招商部 — 6月11日前提交初稿\n\n"
                    "## 需协调事项\n"
                    "- 消防验收申报需工程部提供竣工图 — 协调工程部张工 — 本周三前提供\n"
                    "- 新商户进场装修需物业配合 — 物业部 — 确认时间节点"
                ),
                created_by=_admin_user_id,
                is_builtin=True,
            )
            print("Built-in template '模板示例' created")
    except Exception as e:
        print(f"Note: could not create built-in template: {e}")

router = APIRouter(prefix="/api")

INPUT_DIR = Path("data/input")
PDF_DIR = INPUT_DIR / "pdfs"
OUTPUT_DIR = Path("data/output")
INPUT_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════
#  Extraction & Results
# ═══════════════════════════════════════════════════════════════════════

@router.post("/extract")
def extract(
    file: UploadFile = File(...),
    pdf_file: Optional[UploadFile] = File(None),
    template_id: str = "",
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Upload a .docx file, enqueue extraction, and return a task id quickly."""
    if not file.filename or not file.filename.endswith(".docx"):
        raise HTTPException(400, "仅支持 .docx 文件")

    # Save uploaded docx
    stored_filename = f"{uuid.uuid4().hex}_{file.filename}"
    input_path = INPUT_DIR / stored_filename
    with input_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # Save optional PDF
    pdf_filename = ""
    if pdf_file and pdf_file.filename:
        if not pdf_file.filename.endswith(".pdf"):
            raise HTTPException(400, "PDF 文件格式不正确")
        # Prefix with result id to avoid collisions
        pdf_filename = f"{uuid.uuid4().hex}_{pdf_file.filename}"
        pdf_path = PDF_DIR / pdf_filename
        with pdf_path.open("wb") as f:
            shutil.copyfileobj(pdf_file.file, f)

    task = create_background_task(
        "extract_docx",
        {
            "input_path": str(input_path),
            "original_filename": file.filename,
            "pdf_filename": pdf_filename,
        },
        web_user_id=current_user["id"],
        template_id=template_id.strip(),
    )
    return {
        "task_id": task["id"],
        "status": task["status"],
        "original_filename": file.filename,
        "pdf_filename": pdf_filename,
    }


class ExtractFromTextBody(BaseModel):
    meeting_text: str
    original_filename: str = ""
    pdf_filename: str = ""
    template_id: str = ""


@router.post("/extract-from-text")
def extract_from_text(
    body: ExtractFromTextBody,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """接受会议纪要文本，创建后台任务提取结构化数据。

    用于录音转录流程：用户编辑完会议纪要后点击"解析"，将文本传入此接口，
    与 .docx 上传流程共用同一套 LLM 解析逻辑和同一张结果表。
    """
    meeting_text = body.meeting_text.strip()
    if not meeting_text:
        raise HTTPException(400, "会议纪要内容为空")

    filename = body.original_filename.strip() or "录音转文字_解析结果"
    task = create_background_task(
        "extract_text",
        {
            "meeting_text": meeting_text,
            "original_filename": filename,
            "pdf_filename": body.pdf_filename,
        },
        web_user_id=current_user["id"],
        template_id=body.template_id.strip(),
    )
    return {
        "task_id": task["id"],
        "status": task["status"],
        "original_filename": filename,
        "pdf_filename": body.pdf_filename,
    }


@router.get("/tasks/{task_id}")
def get_task_status(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return background task status for frontend polling."""
    task = get_background_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    if current_user.get("role") != "admin" and task.get("web_user_id") != current_user["id"]:
        raise HTTPException(403, "无权访问此任务")
    return {
        "task_id": task["id"],
        "task_type": task["task_type"],
        "status": task["status"],
        "result_type": task.get("result_type") or "",
        "result_id": task.get("result_id") or "",
        "error": task.get("error") or "",
        "created_at": task["created_at"],
        "updated_at": task["updated_at"],
        "started_at": task.get("started_at"),
        "finished_at": task.get("finished_at"),
    }


@router.get("/results")
def list_all_results(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List extraction results — admin sees all, users see only their own."""
    is_admin = current_user.get("role") == "admin"
    web_user_id = current_user["id"] if not is_admin else None
    return list_results(web_user_id=web_user_id, is_admin=is_admin)


@router.get("/results/{result_id}")
def get_extraction_result(
    result_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Fetch a single result with full JSON data."""
    record = get_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    # Check ownership
    if current_user.get("role") != "admin" and record.get("web_user_id") != current_user["id"]:
        raise HTTPException(403, "无权访问此记录")
    return record


class UpdateResultBody(BaseModel):
    result: Dict[str, Any]


@router.put("/results/{result_id}")
def update_extraction_result(
    result_id: str,
    body: UpdateResultBody,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    """Update the JSON data of a result (after user review)."""
    record = get_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    if current_user.get("role") != "admin" and record.get("web_user_id") != current_user["id"]:
        raise HTTPException(403, "无权修改此记录")
    ok = update_result(result_id, body.result)
    if not ok:
        raise HTTPException(404, "结果不存在")
    return {"status": "ok"}


@router.delete("/results/{result_id}")
def delete_extraction_result(
    result_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    """Delete a result record."""
    record = get_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    if current_user.get("role") != "admin" and record.get("web_user_id") != current_user["id"]:
        raise HTTPException(403, "无权删除此记录")
    ok = delete_result(result_id)
    if not ok:
        raise HTTPException(404, "结果不存在")
    return {"status": "deleted"}


@router.post("/results/{result_id}/delete")
def delete_extraction_result_compat(
    result_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    """Compatibility endpoint for clients/environments that block DELETE."""
    record = get_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    if current_user.get("role") != "admin" and record.get("web_user_id") != current_user["id"]:
        raise HTTPException(403, "无权删除此记录")
    ok = delete_result(result_id)
    if not ok:
        raise HTTPException(404, "结果不存在")
    return {"status": "deleted"}


@router.post("/results/{result_id}/upload-pdf")
async def upload_pdf(
    result_id: str,
    pdf_file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Upload or replace a PDF file for an existing extraction result."""
    record = get_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    if current_user.get("role") != "admin" and record.get("web_user_id") != current_user["id"]:
        raise HTTPException(403, "无权操作此记录")
    if not pdf_file.filename or not pdf_file.filename.endswith(".pdf"):
        raise HTTPException(400, "仅支持 .pdf 文件")

    # Save PDF with unique name to avoid collisions
    pdf_filename = f"{uuid.uuid4().hex}_{pdf_file.filename}"
    pdf_path = PDF_DIR / pdf_filename
    with pdf_path.open("wb") as f:
        shutil.copyfileobj(pdf_file.file, f)

    # Update database
    ok = update_pdf_filename(result_id, pdf_filename)
    if not ok:
        raise HTTPException(404, "结果不存在")

    return {"status": "ok", "pdf_filename": pdf_filename}


# ═══════════════════════════════════════════════════════════════════════
#  Template Management
# ═══════════════════════════════════════════════════════════════════════

class TemplateBody(BaseModel):
    name: str
    description: str = ""
    style_prompt: str = ""
    sample_output: str = "{}"


@router.get("/templates")
def api_list_templates(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List all templates — visible to all logged-in users."""
    return list_templates()


@router.get("/templates/{template_id}")
def api_get_template(
    template_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get a single template with full details."""
    tmpl = get_template(template_id)
    if not tmpl:
        raise HTTPException(404, "模板不存在")
    return tmpl


@router.post("/templates")
def api_create_template(
    body: TemplateBody,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new template."""
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "模板名称不能为空")
    try:
        return create_template(
            name=name,
            description=body.description.strip(),
            style_prompt=body.style_prompt.strip(),
            sample_output=body.sample_output,
            created_by=current_user["id"],
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.put("/templates/{template_id}")
def api_update_template(
    template_id: str,
    body: TemplateBody,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    """Update a template. Only creator or admin can update."""
    tmpl = get_template(template_id)
    if not tmpl:
        raise HTTPException(404, "模板不存在")
    if current_user.get("role") != "admin" and tmpl.get("created_by") != current_user["id"]:
        raise HTTPException(403, "仅模板创建者或管理员可修改")
    ok = update_template(
        template_id,
        name=body.name.strip() or None,
        description=body.description.strip() or None,
        style_prompt=body.style_prompt.strip() or None,
        sample_output=body.sample_output or None,
    )
    if not ok:
        raise HTTPException(404, "模板不存在")
    return {"status": "ok"}


@router.delete("/templates/{template_id}")
def api_delete_template(
    template_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    """Delete a template. Only creator or admin can delete. No reference check."""
    tmpl = get_template(template_id)
    if not tmpl:
        raise HTTPException(404, "模板不存在")
    if current_user.get("role") != "admin" and tmpl.get("created_by") != current_user["id"]:
        raise HTTPException(403, "仅模板创建者或管理员可删除")
    ok = delete_template(template_id)
    if not ok:
        raise HTTPException(404, "模板不存在")
    return {"status": "deleted"}


GENERATE_STYLE_PROMPT_SYSTEM = """
你是一个会议纪要风格分析专家。

用户会提供一个会议纪要示例文档。请从以下四个维度分析它的写作风格，
并输出一段自然语言描述，指导 AI 如何写出同样风格的会议纪要。

分析维度：
1. 整体结构：文档分几个部分？各部分标题是什么？段落如何组织？
2. 语言风格：正式程度如何？用词特点？句式长短？语气？
3. 条目化程度：是否大量使用项目符号、编号？还是纯段落？
4. 待办事项/决议的表述方式：如何描述后续行动？责任人和时间如何体现？

输出要求：
- 用中文自然语言描述，直接告诉 AI 助手"请按以下风格书写"。
- 包含具体格式示例，不要只说"使用项目符号"，要说"每个议题下用 - 开头的项目符号列出讨论要点"。
- 输出应直接可用作 AI 的系统提示词补充，语言简洁明确。
- 不要输出 JSON 或 markdown 代码块。
"""


@router.post("/templates/generate-prompt")
def api_generate_style_prompt(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    """Upload a .docx meeting minutes example → AI analyzes style → returns style_prompt."""
    if not file.filename or not file.filename.endswith(".docx"):
        raise HTTPException(400, "仅支持 .docx 文件")

    # Save to temp file
    tmp_path = INPUT_DIR / f"_style_analysis_{uuid.uuid4().hex}.docx"
    try:
        with tmp_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        # Read docx content
        meeting_text = load_docx_text(tmp_path)
        if not meeting_text.strip():
            raise HTTPException(400, "文档内容为空")

        # Call LLM for analysis
        llm = get_llm()
        user_prompt = f"请分析以下会议纪要示例的写作风格：\n\n{meeting_text}"
        response = llm.invoke([
            SystemMessage(content=GENERATE_STYLE_PROMPT_SYSTEM),
            HumanMessage(content=user_prompt),
        ])

        style_prompt = response.content.strip()
        if not style_prompt:
            raise HTTPException(500, "AI 分析返回为空")

        return {"style_prompt": style_prompt, "sample_output": meeting_text.strip()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"分析失败: {e}") from e
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


# ═══════════════════════════════════════════════════════════════════════
#  Push to WeCom
# ═══════════════════════════════════════════════════════════════════════

class PushBody(BaseModel):
    project_id: Optional[int] = None


@router.post("/results/{result_id}/push")
def push_result(
    result_id: str,
    body: PushBody = PushBody(),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Convert and push the result to WeChat Work (message + schedules)."""
    record = get_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    if current_user.get("role") != "admin" and record.get("web_user_id") != current_user["id"]:
        raise HTTPException(403, "无权推送此记录")

    raw: Dict[str, Any] = record["result_json"]

    # Build lookup maps
    users = list_users()
    depts = list_departments()
    user_map: Dict[str, str] = {u["name"]: u["userid"] for u in users}
    dept_map: Dict[str, str] = {d["name"]: str(d["dept_id"]) for d in depts}

    # Convert names → IDs, dates → timestamps
    try:
        push_data = convert_result_for_push(raw, user_map, dept_map)
    except Exception as e:
        raise HTTPException(500, f"数据转换失败: {e}") from e

    # Validate meeting text
    meeting_text = str(push_data.get("meeting", "")).strip()
    if not meeting_text:
        raise HTTPException(400, "meeting 内容为空，无法推送")

    # Push messages (may be split into multiple if content exceeds byte limit)
    msg_responses: list[Dict[str, Any]] = []
    try:
        msg_responses = send_meeting_summary_from_result(push_data) or []
    except Exception as e:
        raise HTTPException(400, f"消息推送失败: {e}") from e

    # Push file (PDF if exists, else docx)
    file_resp: Dict[str, Any] = {}
    try:
        file_resp = send_file_from_result(
            result=record,
            userids=push_data.get("push_user", []),
            dept_ids=push_data.get("push_dept", []),
        ) or {}
    except Exception as e:
        # File sending is non-critical; log but don't block the push
        file_resp = {"error": str(e)}

    # Push schedules
    schedule_responses: List[Dict[str, Any]] = []
    schedule_items = push_data.get("schedules", []) or []
    if schedule_items:
        try:
            schedule_responses = create_meeting_schedules_from_result(push_data) or []
        except Exception as e:
            schedule_responses = [{"error": str(e)}]

    # Update project association if provided (before marking pushed).
    # project_id=0 means "clear association" (set to NULL).
    if body.project_id is not None:
        pid = body.project_id if body.project_id > 0 else None
        update_result_project("extraction", result_id, pid)

    mark_result_pushed(result_id)

    return {
        "status": "pushed",
        "message_response": msg_responses,
        "file_response": file_resp,
        "schedule_responses": schedule_responses,
    }


# ═══════════════════════════════════════════════════════════════════════
#  Auth (Register / Login / Logout / Me)
# ═══════════════════════════════════════════════════════════════════════

class RegisterBody(BaseModel):
    username: str
    password: str
    department_name: str = ""


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/auth/register")
def register(body: RegisterBody) -> Dict[str, Any]:
    """Register a new user (default role=user)."""
    username = body.username.strip()
    if not username or not body.password:
        raise HTTPException(400, "用户名和密码不能为空")
    if len(body.password) < 6:
        raise HTTPException(400, "密码长度不能少于 6 位")
    try:
        password_hash = hash_password(body.password)
        user = create_web_user(username, password_hash, body.department_name, role="user")
        return {"id": user["id"], "username": user["username"], "role": user["role"], "department_name": user["department_name"]}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/auth/login")
def login(body: LoginBody) -> Dict[str, Any]:
    """Login and get a session token."""
    user = get_web_user_by_username(body.username.strip())
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "用户名或密码错误")
    token = create_session_token(user["id"])
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "department_name": user["department_name"],
        },
    }


@router.get("/auth/me")
def get_me(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Return the current logged-in user's info."""
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "role": current_user["role"],
        "department_name": current_user["department_name"],
    }


@router.post("/auth/logout")
def logout(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    """Logout (delete current session)."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()
    if token:
        delete_session(token)
    return {"status": "logged_out"}


# ═══════════════════════════════════════════════════════════════════════
#  User CRUD — admin only
# ═══════════════════════════════════════════════════════════════════════

class UserBody(BaseModel):
    name: str
    userid: str
    department_name: str = ""


class UserBatchBody(BaseModel):
    users: List[UserBody]


@router.get("/users")
def api_list_users(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return list_users()


@router.post("/users")
def api_create_user(body: UserBody, admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
    if not body.name.strip() or not body.userid.strip():
        raise HTTPException(400, "姓名和 UserID 不能为空")
    try:
        return create_user(body.name, body.userid, body.department_name)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/users/batch")
def api_create_users_batch(body: UserBatchBody, admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
    if not body.users:
        raise HTTPException(400, "批量用户不能为空")
    if len(body.users) > 1000:
        raise HTTPException(400, "单次最多导入 1000 个用户")
    invalid_rows = [i for i, user in enumerate(body.users, start=1) if not user.name.strip() or not user.userid.strip()]
    if invalid_rows:
        raise HTTPException(400, f"第 {', '.join(map(str, invalid_rows))} 行姓名或 UserID 为空")
    return create_users_batch([user.model_dump() for user in body.users])


class UserUpdateBody(BaseModel):
    name: str
    userid: str
    department_name: str = ""


@router.put("/users/{user_id}")
def api_update_user(user_id: int, body: UserUpdateBody, admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
    try:
        return update_user(user_id, body.name, body.userid, body.department_name)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.delete("/users/{user_id}")
def api_delete_user(user_id: int, admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, str]:
    delete_user(user_id)
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════════════════
#  Department CRUD
# ═══════════════════════════════════════════════════════════════════════

class DeptBody(BaseModel):
    name: str
    dept_id: int


@router.get("/departments")
def api_list_departments() -> List[Dict[str, Any]]:
    return list_departments()


@router.post("/departments")
def api_create_department(body: DeptBody, admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
    try:
        return create_department(body.name, body.dept_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


class DeptUpdateBody(BaseModel):
    name: str
    dept_id: int


@router.put("/departments/{dept_pk}")
def api_update_department(dept_pk: int, body: DeptUpdateBody, admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
    try:
        return update_department(dept_pk, body.name, body.dept_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.delete("/departments/{dept_pk}")
def api_delete_department(dept_pk: int, admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, str]:
    delete_department(dept_pk)
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════════════════
#  Web User (账号) CRUD — admin only
# ═══════════════════════════════════════════════════════════════════════

class WebUserBody(BaseModel):
    username: str
    password: str
    department_name: str = ""
    role: str = "user"


@router.get("/web-users")
def api_list_web_users(admin: Dict[str, Any] = Depends(require_admin)) -> List[Dict[str, Any]]:
    return list_web_users()


@router.post("/web-users")
def api_create_web_user(body: WebUserBody, admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
    username = body.username.strip()
    if not username or not body.password:
        raise HTTPException(400, "用户名和密码不能为空")
    if len(body.password) < 6:
        raise HTTPException(400, "密码长度不能少于 6 位")
    if body.role not in ("user", "admin"):
        raise HTTPException(400, "角色只能是 user 或 admin")
    try:
        password_hash = hash_password(body.password)
        user = create_web_user(username, password_hash, body.department_name, role=body.role)
        return {"id": user["id"], "username": user["username"], "role": user["role"],
                "department_name": user["department_name"], "created_at": user["created_at"]}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.delete("/web-users/{user_id}")
def api_delete_web_user(user_id: int, admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, str]:
    ok = delete_web_user(user_id)
    if not ok:
        raise HTTPException(404, "用户不存在")
    return {"status": "deleted"}
