from __future__ import annotations

import os
import signal
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any, Dict, Sequence

from meeting_agent.schemas import MeetingOutput
from meeting_agent.services.asr_service import get_transcribed_text_from_url, transcribe_audio_file
from meeting_agent.transcription.workflow import run_transcription_extraction
from meeting_agent.web.database import init_db
from meeting_agent.web.models import (
    claim_next_background_task,
    complete_background_task,
    create_result,
    create_transcription_result,
    fail_background_task,
    get_template,
    reset_running_background_tasks,
)
from meeting_agent.workflow import run_meeting_extraction, run_meeting_extraction_from_text

INPUT_DIR = Path("data/input/transcriptions")

_stopping = False


def _handle_stop(signum: int, frame: object) -> None:
    global _stopping
    _stopping = True


def _get_style_prompt(template_id: str) -> str:
    """Load style_prompt from a template. Returns empty string if not found."""
    if not template_id:
        return ""
    try:
        tmpl = get_template(template_id)
        return (tmpl or {}).get("style_prompt", "")
    except Exception:
        return ""


def _run_extract_task(task: Dict[str, Any]) -> None:
    payload = task["payload_json"]
    task_type = task["task_type"]
    web_user_id = task.get("web_user_id")
    template_id = task.get("template_id") or ""
    style_prompt = _get_style_prompt(template_id)

    if task_type == "extract_docx":
        meeting: MeetingOutput = run_meeting_extraction(Path(payload["input_path"]), style_prompt=style_prompt)
        result_data = meeting.model_dump(mode="json")
        record = create_result(
            original_filename=payload["original_filename"],
            result_data=result_data,
            pdf_filename=payload.get("pdf_filename", ""),
            web_user_id=web_user_id,
            template_id=template_id,
        )
        complete_background_task(task["id"], "extraction", record["id"])
        return

    if task_type == "extract_text":
        meeting_text = str(payload["meeting_text"]).strip()
        meeting: MeetingOutput = run_meeting_extraction_from_text(meeting_text, style_prompt=style_prompt)
        result_data = meeting.model_dump(mode="json")
        record = create_result(
            original_filename=payload.get("original_filename") or "录音转文字_解析结果",
            result_data=result_data,
            pdf_filename=payload.get("pdf_filename", ""),
            web_user_id=web_user_id,
            template_id=template_id,
        )
        complete_background_task(task["id"], "extraction", record["id"])
        return

    raise ValueError(f"Unsupported extract task type: {task_type}")


def _run_transcribe_task(task: Dict[str, Any]) -> None:
    payload = task["payload_json"]
    task_type = task["task_type"]
    web_user_id = task.get("web_user_id")
    template_id = task.get("template_id") or ""
    style_prompt = _get_style_prompt(template_id)

    if task_type == "transcribe_file":
        transcribed_text = transcribe_audio_file(Path(payload["audio_path"]))
        original_filename = payload["original_filename"]
    elif task_type == "transcribe_url":
        transcribed_text = get_transcribed_text_from_url(payload["audio_url"])
        original_filename = payload["original_filename"]
    else:
        raise ValueError(f"Unsupported transcribe task type: {task_type}")

    if not transcribed_text.strip():
        raise RuntimeError("语音识别结果为空")

    text_filename = f"{task['id']}_transcribed.txt"
    text_path = INPUT_DIR / text_filename
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text(transcribed_text, encoding="utf-8")

    try:
        result_data = run_transcription_extraction(
            text_path,
            meeting_name=payload.get("meeting_name", ""),
            meeting_time=payload.get("meeting_time", ""),
            meeting_location=payload.get("meeting_location", ""),
            meeting_chair=payload.get("meeting_chair", ""),
            meeting_attendees=payload.get("meeting_attendees", ""),
            meeting_departments=payload.get("meeting_departments", ""),
            meeting_recorder=payload.get("meeting_recorder", ""),
            style_prompt=style_prompt,
        )
    except Exception:
        result_data = {
            "meeting": transcribed_text,
            "meeting_date": "",
            "push_dept": [],
            "push_user": [],
            "schedules": [],
        }

    record = create_transcription_result(
        original_filename=original_filename,
        result_data=result_data,
        user_prompt="",
        web_user_id=web_user_id,
        template_id=template_id,
    )
    complete_background_task(task["id"], "transcription", record["id"])


def _run_task(task: Dict[str, Any]) -> None:
    try:
        if task["task_type"] in ("extract_docx", "extract_text"):
            _run_extract_task(task)
        elif task["task_type"] in ("transcribe_file", "transcribe_url"):
            _run_transcribe_task(task)
        else:
            raise ValueError(f"Unsupported task type: {task['task_type']}")
    except Exception as exc:
        fail_background_task(task["id"], str(exc))


def _schedule_loop(task_types: Sequence[str], concurrency: int, poll_interval: float) -> None:
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = set()
        while not _stopping:
            while len(futures) < concurrency:
                task = claim_next_background_task(task_types)
                if not task:
                    break
                futures.add(executor.submit(_run_task, task))

            if futures:
                done, futures = wait(futures, timeout=poll_interval, return_when=FIRST_COMPLETED)
                for future in done:
                    future.result()
            else:
                time.sleep(poll_interval)


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)
    init_db()
    reset_running_background_tasks()

    extract_concurrency = int(os.environ.get("EXTRACT_WORKER_CONCURRENCY", "2"))
    transcribe_concurrency = int(os.environ.get("TRANSCRIBE_WORKER_CONCURRENCY", "1"))
    poll_interval = float(os.environ.get("TASK_POLL_INTERVAL", "1"))

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                _schedule_loop,
                ("extract_docx", "extract_text"),
                extract_concurrency,
                poll_interval,
            ),
            executor.submit(
                _schedule_loop,
                ("transcribe_file", "transcribe_url"),
                transcribe_concurrency,
                poll_interval,
            ),
        ]
        while not _stopping:
            time.sleep(0.5)
        wait(futures, timeout=5)


if __name__ == "__main__":
    main()
