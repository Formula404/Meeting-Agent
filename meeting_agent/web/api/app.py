from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from meeting_agent.schemas import MeetingOutput
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
from meeting_agent.web.models import (
    create_department,
    create_result,
    create_user,
    create_web_user,
    delete_department,
    delete_result,
    delete_session,
    delete_user,
    get_result,
    get_web_user_by_id,
    get_web_user_by_username,
    list_departments,
    list_results,
    list_users,
    mark_result_pushed,
    update_department,
    update_pdf_filename,
    update_result,
    update_user,
)
from meeting_agent.workflow import run_meeting_extraction

# Ensure DB schema on import
init_db()

# Seed default admin if ADMIN_PASSWORD env var is set and no admin exists
_default_admin_password = os.environ.get("ADMIN_PASSWORD", "")
if _default_admin_password:
    existing = get_web_user_by_username("admin")
    if existing is None:
        try:
            _pw_hash = hash_password(_default_admin_password)
            create_web_user("admin", _pw_hash, department_name="系统管理", role="admin")
            print("Default admin user created (username=admin, password from ADMIN_PASSWORD)")
        except Exception:
            pass  # race condition — another instance may have created it

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
async def extract(
    file: UploadFile = File(...),
    pdf_file: Optional[UploadFile] = File(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Upload a .docx file (and optional .pdf), run LLM extraction, return the result."""
    if not file.filename or not file.filename.endswith(".docx"):
        raise HTTPException(400, "仅支持 .docx 文件")

    # Save uploaded docx
    input_path = INPUT_DIR / file.filename
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

    # Run extraction pipeline
    try:
        meeting: MeetingOutput = run_meeting_extraction(input_path)
        result_data = meeting.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(500, f"LLM 提取失败: {e}") from e

    # Persist result with owner
    record = create_result(
        original_filename=file.filename,
        result_data=result_data,
        pdf_filename=pdf_filename,
        web_user_id=current_user["id"],
    )
    return {
        "id": record["id"],
        "original_filename": record["original_filename"],
        "pdf_filename": pdf_filename,
        "created_at": record["created_at"],
        "result": result_data,
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
#  Push to WeCom
# ═══════════════════════════════════════════════════════════════════════

@router.post("/results/{result_id}/push")
def push_result(
    result_id: str,
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


@router.get("/users")
def api_list_users(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return list_users()


@router.post("/users")
def api_create_user(body: UserBody, admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
    try:
        return create_user(body.name, body.userid, body.department_name)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


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
