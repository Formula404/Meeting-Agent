"""转录处理 API 路由 —— 独立于主流程 app.py"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from meeting_agent.transcription.workflow import run_transcription_extraction
from meeting_agent.transcription.docx_export import export_to_docx
from meeting_agent.web.converter import convert_result_for_push
from meeting_agent.services.message_service import send_meeting_summary_from_result
from meeting_agent.services.schedule_service import create_meeting_schedules_from_result
from meeting_agent.web.models import (
    create_transcription_result,
    delete_transcription_result,
    get_transcription_result,
    list_transcription_results,
    list_users,
    list_departments,
    update_transcription_result,
    mark_transcription_result_pushed,
)

router = APIRouter(prefix="/api")

INPUT_DIR = Path("data/input/transcriptions")
OUTPUT_DIR = Path("data/output")
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    custom_prompt: str = Form(""),
) -> Dict[str, Any]:
    """上传录音转文字文件，执行 LLM 提取，返回结构化会议纪要。

    Args:
        file: 录音转文字文件（支持 .docx 或 .txt）。
        custom_prompt: 用户自定义提取要求。
    """
    if not file.filename:
        raise HTTPException(400, "文件名为空")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".docx", ".txt"):
        raise HTTPException(400, "仅支持 .docx 或 .txt 文件")

    # 保存文件
    input_filename = f"{uuid.uuid4().hex}_{file.filename}"
    input_path = INPUT_DIR / input_filename
    with input_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # 执行 LLM 提取
    try:
        meeting = run_transcription_extraction(input_path, custom_prompt)
        result_data = meeting.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(500, f"LLM 提取失败: {e}") from e

    # 持久化
    record = create_transcription_result(
        original_filename=file.filename,
        result_data=result_data,
        user_prompt=custom_prompt,
    )

    return {
        "id": record["id"],
        "original_filename": record["original_filename"],
        "created_at": record["created_at"],
        "result": result_data,
    }


@router.get("/transcribe")
def list_all_transcriptions() -> List[Dict[str, Any]]:
    """列出所有转录处理记录（元数据，不含完整 JSON）。"""
    return list_transcription_results()


@router.get("/transcribe/{result_id}")
def get_transcription_result_endpoint(result_id: str) -> Dict[str, Any]:
    """获取单条转录处理结果（含完整 JSON 数据）。"""
    record = get_transcription_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    return record


class UpdateTranscriptionBody(BaseModel):
    result: Dict[str, Any]


@router.put("/transcribe/{result_id}")
def update_transcription_result_endpoint(
    result_id: str, body: UpdateTranscriptionBody
) -> Dict[str, str]:
    """更新转录处理结果（用户编辑后保存）。"""
    ok = update_transcription_result(result_id, body.result)
    if not ok:
        raise HTTPException(404, "结果不存在")
    return {"status": "ok"}


@router.delete("/transcribe/{result_id}")
def delete_transcription_result_endpoint(result_id: str) -> Dict[str, str]:
    """删除转录处理记录。"""
    ok = delete_transcription_result(result_id)
    if not ok:
        raise HTTPException(404, "结果不存在")
    return {"status": "deleted"}


@router.post("/transcribe/{result_id}/delete")
def delete_transcription_result_compat(result_id: str) -> Dict[str, str]:
    """兼容 DELETE 被限制的环境。"""
    ok = delete_transcription_result(result_id)
    if not ok:
        raise HTTPException(404, "结果不存在")
    return {"status": "deleted"}


@router.post("/transcribe/{result_id}/export-docx")
def export_transcription_docx(result_id: str) -> Any:
    """将转录处理结果导出为 .docx 文件并下载。"""
    from fastapi.responses import FileResponse

    record = get_transcription_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")

    result_data = record["result_json"]
    stem = Path(record["original_filename"]).stem
    output_filename = f"{stem}_会议纪要_{uuid.uuid4().hex[:8]}.docx"
    output_path = OUTPUT_DIR / output_filename

    try:
        export_to_docx(result_data, output_path)
    except Exception as e:
        raise HTTPException(500, f"导出失败: {e}") from e

    return FileResponse(
        path=str(output_path),
        filename=output_filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.post("/transcribe/{result_id}/push")
def push_transcription_result(result_id: str) -> Dict[str, Any]:
    """推送转录处理结果到企业微信（复用现有推送流程）。"""
    record = get_transcription_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")

    raw: Dict[str, Any] = record["result_json"]

    # 构建转换映射
    users = list_users()
    depts = list_departments()
    user_map: Dict[str, str] = {u["name"]: u["userid"] for u in users}
    dept_map: Dict[str, str] = {d["name"]: str(d["dept_id"]) for d in depts}

    # 转换数据
    try:
        push_data = convert_result_for_push(raw, user_map, dept_map)
    except Exception as e:
        raise HTTPException(500, f"数据转换失败: {e}") from e

    # 校验
    meeting_text = str(push_data.get("meeting", "")).strip()
    if not meeting_text:
        raise HTTPException(400, "meeting 内容为空，无法推送")

    # 推送消息
    msg_responses: list[Dict[str, Any]] = []
    try:
        msg_responses = send_meeting_summary_from_result(push_data) or []
    except Exception as e:
        raise HTTPException(400, f"消息推送失败: {e}") from e

    # 推送日程
    schedule_responses: List[Dict[str, Any]] = []
    schedule_items = push_data.get("schedules", []) or []
    if schedule_items:
        try:
            schedule_responses = create_meeting_schedules_from_result(push_data) or []
        except Exception as e:
            schedule_responses = [{"error": str(e)}]

    mark_transcription_result_pushed(result_id)

    return {
        "status": "pushed",
        "message_response": msg_responses,
        "schedule_responses": schedule_responses,
    }
