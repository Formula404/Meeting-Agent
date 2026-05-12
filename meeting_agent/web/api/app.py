from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from meeting_agent.schemas import MeetingOutput
from meeting_agent.services.message_service import send_meeting_summary_from_result
from meeting_agent.services.schedule_service import create_meeting_schedules_from_result
from meeting_agent.web.converter import convert_result_for_push
from meeting_agent.web.database import init_db
from meeting_agent.web.models import (
    create_department,
    create_result,
    create_user,
    delete_department,
    delete_result,
    delete_user,
    get_result,
    list_departments,
    list_results,
    list_users,
    mark_result_pushed,
    update_department,
    update_result,
    update_user,
)
from meeting_agent.workflow import run_meeting_extraction

# Ensure DB schema on import
init_db()

router = APIRouter(prefix="/api")

INPUT_DIR = Path("data/input")
OUTPUT_DIR = Path("data/output")
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════
#  Extraction & Results
# ═══════════════════════════════════════════════════════════════════════

@router.post("/extract")
async def extract(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload a .docx file, run LLM extraction, return the result."""
    if not file.filename or not file.filename.endswith(".docx"):
        raise HTTPException(400, "仅支持 .docx 文件")

    # Save uploaded file
    input_path = INPUT_DIR / file.filename
    with input_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # Run extraction pipeline
    try:
        meeting: MeetingOutput = run_meeting_extraction(input_path)
        result_data = meeting.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(500, f"LLM 提取失败: {e}") from e

    # Persist result
    record = create_result(original_filename=file.filename, result_data=result_data)
    return {
        "id": record["id"],
        "original_filename": record["original_filename"],
        "created_at": record["created_at"],
        "result": result_data,
    }


@router.get("/results")
def list_all_results() -> List[Dict[str, Any]]:
    """List all extraction results (metadata only, no JSON body)."""
    return list_results()


@router.get("/results/{result_id}")
def get_extraction_result(result_id: str) -> Dict[str, Any]:
    """Fetch a single result with full JSON data."""
    record = get_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    return record


class UpdateResultBody(BaseModel):
    result: Dict[str, Any]


@router.put("/results/{result_id}")
def update_extraction_result(result_id: str, body: UpdateResultBody) -> Dict[str, str]:
    """Update the JSON data of a result (after user review)."""
    ok = update_result(result_id, body.result)
    if not ok:
        raise HTTPException(404, "结果不存在")
    return {"status": "ok"}


@router.delete("/results/{result_id}")
def delete_extraction_result(result_id: str) -> Dict[str, str]:
    """Delete a result record."""
    ok = delete_result(result_id)
    if not ok:
        raise HTTPException(404, "结果不存在")
    return {"status": "deleted"}


@router.post("/results/{result_id}/delete")
def delete_extraction_result_compat(result_id: str) -> Dict[str, str]:
    """Compatibility endpoint for clients/environments that block DELETE."""
    ok = delete_result(result_id)
    if not ok:
        raise HTTPException(404, "结果不存在")
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════════════════
#  Push to WeCom
# ═══════════════════════════════════════════════════════════════════════

@router.post("/results/{result_id}/push")
def push_result(result_id: str) -> Dict[str, Any]:
    """Convert and push the result to WeChat Work (message + schedules)."""
    record = get_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")

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

    # Push messages
    msg_resp: Dict[str, Any] = {}
    try:
        msg_resp = send_meeting_summary_from_result(push_data) or {}
    except Exception as e:
        raise HTTPException(400, f"消息推送失败: {e}") from e

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
        "message_response": msg_resp,
        "schedule_responses": schedule_responses,
    }


# ═══════════════════════════════════════════════════════════════════════
#  User CRUD
# ═══════════════════════════════════════════════════════════════════════

class UserBody(BaseModel):
    name: str
    userid: str
    department_name: str = ""


@router.get("/users")
def api_list_users() -> List[Dict[str, Any]]:
    return list_users()


@router.post("/users")
def api_create_user(body: UserBody) -> Dict[str, Any]:
    try:
        return create_user(body.name, body.userid, body.department_name)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


class UserUpdateBody(BaseModel):
    name: str
    userid: str
    department_name: str = ""


@router.put("/users/{user_id}")
def api_update_user(user_id: int, body: UserUpdateBody) -> Dict[str, Any]:
    try:
        return update_user(user_id, body.name, body.userid, body.department_name)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.delete("/users/{user_id}")
def api_delete_user(user_id: int) -> Dict[str, str]:
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
def api_create_department(body: DeptBody) -> Dict[str, Any]:
    try:
        return create_department(body.name, body.dept_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


class DeptUpdateBody(BaseModel):
    name: str
    dept_id: int


@router.put("/departments/{dept_pk}")
def api_update_department(dept_pk: int, body: DeptUpdateBody) -> Dict[str, Any]:
    try:
        return update_department(dept_pk, body.name, body.dept_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.delete("/departments/{dept_pk}")
def api_delete_department(dept_pk: int) -> Dict[str, str]:
    delete_department(dept_pk)
    return {"status": "deleted"}
