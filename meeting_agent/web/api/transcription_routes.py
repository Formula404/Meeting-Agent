"""转录处理 API 路由 —— 独立于主流程 app.py"""

from __future__ import annotations

import json
import logging
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

perf_logger = logging.getLogger("perf")


def log_stage(name: str, start: float) -> float:
    """记录阶段耗时并返回新的起始时间。"""
    cost = time.perf_counter() - start
    perf_logger.info("STAGE %s cost=%.3fs", name, cost)
    return time.perf_counter()

from meeting_agent.transcription.workflow import (
    run_transcription_extraction,
    run_transcription_parse,
)
from meeting_agent.transcription.docx_export import export_to_docx
from meeting_agent.transcription.pdf_export import export_to_pdf, export_to_pdf_from_html
from meeting_agent.services.asr_service import (
    SUPPORTED_AUDIO_EXTENSIONS,
    get_transcribed_text_via_proxy,
    get_transcribed_text_from_url,
)
from meeting_agent.web.auth import get_current_user
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
ASR_AUDIO_DIR = INPUT_DIR / "audio"
PDF_DIR = Path("data/input/pdfs")
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ASR_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/transcribe")
def transcribe(
    file: UploadFile = File(...),
    meeting_name: str = Form(""),
    meeting_time: str = Form(""),
    meeting_location: str = Form(""),
    meeting_chair: str = Form(""),
    meeting_attendees: str = Form(""),
    meeting_departments: str = Form(""),
    meeting_recorder: str = Form(""),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """上传录音文件，经过 ASR 语音识别 → 生成会议纪要草稿。

    文件先匿名上传到 tflink 中转获取公网 URL，再提交腾讯云 ASR URL 拉取模式识别，
    绕过了 ASR 直传 5MB 限制，最大支持 100MB 的音频文件。

    可附带会议基本信息（名称、时间、地点等），辅助 LLM 生成更准确的纪要。

    阶段一：仅生成会议纪要文本，不提取结构化字段。
    用户审阅编辑后可调用 /parse 接口进行结构化解析。

    Args:
        file: 录音文件（支持 wav/mp3/m4a 等常见音频格式，≤100MB）。
        meeting_name: 会议名称。
        meeting_time: 会议时间。
        meeting_location: 会议地点。
        meeting_chair: 会议主持。
        meeting_attendees: 与会人员（逗号分隔）。
        meeting_departments: 参会部门（逗号分隔）。
        meeting_recorder: 记录人。
    """
    if not file.filename:
        raise HTTPException(400, "文件名为空")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_AUDIO_EXTENSIONS:
        raise HTTPException(
            400,
            f"不支持的音频格式：{suffix}，支持格式：{', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}",
        )

    _stage_start = time.perf_counter()

    # 保存音频文件
    audio_filename = f"{uuid.uuid4().hex}_{file.filename}"
    audio_path = ASR_AUDIO_DIR / audio_filename
    with audio_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    _stage_start = log_stage("save_audio", _stage_start)

    # Step 1: ASR 语音识别（经 tflink 中转，无 5MB 限制）
    try:
        transcribed_text = get_transcribed_text_via_proxy(audio_path)
    except Exception as e:
        raise HTTPException(500, f"语音识别失败: {e}") from e
    _stage_start = log_stage("asr_total", _stage_start)

    if not transcribed_text.strip():
        raise HTTPException(500, "语音识别结果为空")

    # 将转写文本保存为 .txt 供 LLM 使用
    text_filename = f"{uuid.uuid4().hex}_transcribed.txt"
    text_path = INPUT_DIR / text_filename
    text_path.write_text(transcribed_text, encoding="utf-8")
    _stage_start = log_stage("save_text", _stage_start)

    # Step 2: LLM 生成会议纪要草稿
    try:
        result_data = run_transcription_extraction(
            text_path,
            meeting_name=meeting_name,
            meeting_time=meeting_time,
            meeting_location=meeting_location,
            meeting_chair=meeting_chair,
            meeting_attendees=meeting_attendees,
            meeting_departments=meeting_departments,
            meeting_recorder=meeting_recorder,
        )
    except Exception as e:
        # 即使 LLM 生成失败，也保存 ASR 原始结果
        result_data = {
            "meeting": transcribed_text,
            "meeting_date": "",
            "push_dept": [],
            "push_user": [],
            "schedules": [],
        }
    _stage_start = log_stage("llm_generate", _stage_start)

    # 持久化
    record = create_transcription_result(
        original_filename=file.filename,
        result_data=result_data,
        user_prompt="",
        web_user_id=current_user["id"],
    )
    log_stage("db_write", _stage_start)

    return {
        "id": record["id"],
        "original_filename": record["original_filename"],
        "created_at": record["created_at"],
        "result": result_data,
    }


class TranscribeUrlBody(BaseModel):
    """URL 转写请求体"""
    audio_url: str
    audio_filename: str = ""
    meeting_name: str = ""
    meeting_time: str = ""
    meeting_location: str = ""
    meeting_chair: str = ""
    meeting_attendees: str = ""
    meeting_departments: str = ""
    meeting_recorder: str = ""


@router.post("/transcribe/url")
def transcribe_from_url(
    body: TranscribeUrlBody,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """通过音频文件 URL 进行语音识别 → 生成会议纪要草稿。

    适用于大于 5MB 的录音文件。需提供公网可访问的音频文件 URL
    （如阿里云 OSS 签名 URL），由腾讯云 ASR 服务拉取识别。

    URL 文件大小上限：腾讯云 ASR URL 拉取模式支持最大 5GB 的音频文件。
    """
    audio_url = body.audio_url.strip()
    if not audio_url:
        raise HTTPException(400, "音频 URL 不能为空")

    # 校验文件扩展名（从 URL 或 audio_filename 推断）
    url_path = Path(audio_url.split("?")[0])  # 去掉查询参数
    filename = body.audio_filename or url_path.name
    suffix = Path(filename).suffix.lower()
    if suffix and suffix not in SUPPORTED_AUDIO_EXTENSIONS:
        raise HTTPException(
            400,
            f"不支持的音频格式：{suffix}，支持格式：{', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}",
        )

    _stage_start = time.perf_counter()

    # Step 1: ASR 语音识别（URL 拉取模式，无 5MB 限制）
    try:
        transcribed_text = get_transcribed_text_from_url(audio_url)
    except Exception as e:
        raise HTTPException(500, f"语音识别失败: {e}") from e
    _stage_start = log_stage("asr_total", _stage_start)

    if not transcribed_text.strip():
        raise HTTPException(500, "语音识别结果为空")

    # 将转写文本保存为 .txt 供 LLM 使用
    text_filename = f"{uuid.uuid4().hex}_transcribed.txt"
    text_path = INPUT_DIR / text_filename
    text_path.write_text(transcribed_text, encoding="utf-8")
    _stage_start = log_stage("save_text", _stage_start)

    # Step 2: LLM 生成会议纪要草稿
    try:
        result_data = run_transcription_extraction(
            text_path,
            meeting_name=body.meeting_name,
            meeting_time=body.meeting_time,
            meeting_location=body.meeting_location,
            meeting_chair=body.meeting_chair,
            meeting_attendees=body.meeting_attendees,
            meeting_departments=body.meeting_departments,
            meeting_recorder=body.meeting_recorder,
        )
    except Exception as e:
        result_data = {
            "meeting": transcribed_text,
            "meeting_date": "",
            "push_dept": [],
            "push_user": [],
            "schedules": [],
        }
    _stage_start = log_stage("llm_generate", _stage_start)

    # 持久化
    record = create_transcription_result(
        original_filename=filename,
        result_data=result_data,
        user_prompt="",
        web_user_id=current_user["id"],
    )
    log_stage("db_write", _stage_start)

    return {
        "id": record["id"],
        "original_filename": filename,
        "created_at": record["created_at"],
        "result": result_data,
    }


@router.get("/transcribe")
def list_all_transcriptions(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """列出所有转录处理记录 — admin 看到全部，用户只看自己的。"""
    is_admin = current_user.get("role") == "admin"
    web_user_id = current_user["id"] if not is_admin else None
    return list_transcription_results(web_user_id=web_user_id, is_admin=is_admin)


@router.get("/transcribe/{result_id}")
def get_transcription_result_endpoint(
    result_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取单条转录处理结果（含完整 JSON 数据）。"""
    record = get_transcription_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    if current_user.get("role") != "admin" and record.get("web_user_id") != current_user["id"]:
        raise HTTPException(403, "无权访问此记录")
    return record


class UpdateTranscriptionBody(BaseModel):
    result: Dict[str, Any]


@router.put("/transcribe/{result_id}")
def update_transcription_result_endpoint(
    result_id: str,
    body: UpdateTranscriptionBody,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    """更新转录处理结果（用户编辑后保存）。"""
    record = get_transcription_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    if current_user.get("role") != "admin" and record.get("web_user_id") != current_user["id"]:
        raise HTTPException(403, "无权修改此记录")
    ok = update_transcription_result(result_id, body.result)
    if not ok:
        raise HTTPException(404, "结果不存在")
    return {"status": "ok"}


@router.delete("/transcribe/{result_id}")
def delete_transcription_result_endpoint(
    result_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    """删除转录处理记录。"""
    record = get_transcription_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    if current_user.get("role") != "admin" and record.get("web_user_id") != current_user["id"]:
        raise HTTPException(403, "无权删除此记录")
    ok = delete_transcription_result(result_id)
    if not ok:
        raise HTTPException(404, "结果不存在")
    return {"status": "deleted"}


@router.post("/transcribe/{result_id}/delete")
def delete_transcription_result_compat(
    result_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    """兼容 DELETE 被限制的环境。"""
    record = get_transcription_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    if current_user.get("role") != "admin" and record.get("web_user_id") != current_user["id"]:
        raise HTTPException(403, "无权删除此记录")
    ok = delete_transcription_result(result_id)
    if not ok:
        raise HTTPException(404, "结果不存在")
    return {"status": "deleted"}


@router.post("/transcribe/{result_id}/export-docx")
def export_transcription_docx(
    result_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
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


@router.post("/transcribe/{result_id}/generate-pdf")
def generate_transcription_pdf(
    result_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    """将转录结果的会议纪要文本生成为 PDF 文件，保存到 data/input/pdfs/。

    优先使用 HTML 格式（保留加粗/对齐/标题等富文本），
    如无 HTML 则回退到纯文本。

    后续可传递给 extract-from-text 接口作为附件，也可通过 download-pdf 接口下载预览。
    """
    record = get_transcription_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    if current_user.get("role") != "admin" and record.get("web_user_id") != current_user["id"]:
        raise HTTPException(403, "无权操作此记录")

    result_data = record["result_json"]
    meeting_html = (result_data.get("meeting_html", "") or "").strip()
    meeting_text = (result_data.get("meeting", "") or "").strip()

    if not meeting_html and not meeting_text:
        raise HTTPException(400, "会议纪要内容为空，无法生成 PDF")

    stem = Path(record["original_filename"]).stem
    pdf_filename = f"{uuid.uuid4().hex}_{stem}.pdf"
    output_path = PDF_DIR / pdf_filename

    try:
        if meeting_html:
            export_to_pdf_from_html(meeting_html, output_path)
        else:
            export_to_pdf(meeting_text, output_path)
    except Exception as e:
        raise HTTPException(500, f"PDF 生成失败: {e}") from e

    return {"status": "ok", "pdf_filename": pdf_filename}


@router.get("/transcribe/{result_id}/download-pdf")
def download_transcription_pdf(
    result_id: str,
    pdf_filename: str = "",
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """下载转录结果的 PDF 文件。

    需提供 generate-pdf 返回的 pdf_filename 作为查询参数。
    """
    from fastapi.responses import FileResponse

    record = get_transcription_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    if current_user.get("role") != "admin" and record.get("web_user_id") != current_user["id"]:
        raise HTTPException(403, "无权操作此记录")

    if not pdf_filename:
        raise HTTPException(400, "请提供 pdf_filename 查询参数")

    pdf_path = PDF_DIR / pdf_filename
    if not pdf_path.exists():
        raise HTTPException(404, "PDF 文件不存在，请先调用 generate-pdf 生成")

    return FileResponse(
        path=str(pdf_path),
        filename=pdf_filename,
        media_type="application/pdf",
    )


class ParseBody(BaseModel):
    meeting_text: str


@router.post("/transcribe/{result_id}/parse")
def parse_transcription_result(
    result_id: str,
    body: ParseBody,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """阶段二：解析会议纪要 → 按部门分解工作任务。

    用户编辑完会议纪要后调用此接口，将自然语言纪要解析为
    按部门/中心分类的结构化任务清单，同时提取推送对象与日程。
    """
    record = get_transcription_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    if current_user.get("role") != "admin" and record.get("web_user_id") != current_user["id"]:
        raise HTTPException(403, "无权操作此记录")

    meeting_text = body.meeting_text.strip()
    if not meeting_text:
        raise HTTPException(400, "会议纪要内容为空，无法解析")

    try:
        result_data = run_transcription_parse(meeting_text)
    except Exception as e:
        raise HTTPException(500, f"任务分解失败: {e}") from e

    # 持久化解析结果（打上已解析标记）
    result_data["_parsed"] = True
    ok = update_transcription_result(result_id, result_data)
    if not ok:
        raise HTTPException(404, "更新记录失败")

    return {
        "status": "parsed",
        "result": result_data,
    }


@router.post("/transcribe/{result_id}/push")
def push_transcription_result(
    result_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """推送转录处理结果到企业微信（复用现有推送流程）。"""
    record = get_transcription_result(result_id)
    if not record:
        raise HTTPException(404, "结果不存在")
    if current_user.get("role") != "admin" and record.get("web_user_id") != current_user["id"]:
        raise HTTPException(403, "无权推送此记录")

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
