"""转录处理工作流 —— 独立于主流程 workflow.py"""

import json
import re
from pathlib import Path
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage

from meeting_agent.document_loader import load_docx_text
from meeting_agent.llm import get_llm
from meeting_agent.transcription.prompts import (
    GENERATE_SYSTEM_PROMPT,
    GENERATE_USER_PROMPT_TEMPLATE,
    PARSE_SYSTEM_PROMPT,
    PARSE_USER_PROMPT_TEMPLATE,
)


def extract_json_from_text(text: str) -> dict:
    """从AI返回的文本中提取 JSON 内容。"""
    cleaned = text.strip()

    # 去掉 markdown 代码块 ```json ... ```
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    # 用正则找到 {...} 格式的 JSON
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError(f"模型输出中没有找到 JSON：\n{cleaned}")

    json_text = match.group(0)
    return json.loads(json_text)


def run_transcription_extraction(
    input_file: str | Path,
    meeting_name: str = "",
    meeting_time: str = "",
    meeting_location: str = "",
    meeting_chair: str = "",
    meeting_attendees: str = "",
    meeting_departments: str = "",
    meeting_recorder: str = "",
    style_prompt: str = "",
) -> Dict[str, Any]:
    """阶段一：输入会议录音转写文字文件 → 生成会议纪要草稿。

    Args:
        input_file: 会议录音转写文字文件路径（支持 .txt）。
        meeting_name: 会议名称。
        meeting_time: 会议时间。
        meeting_location: 会议地点。
        meeting_chair: 会议主持。
        meeting_attendees: 与会人员（逗号分隔）。
        meeting_departments: 参会部门（逗号分隔）。
        meeting_recorder: 记录人。

    Returns:
        包含会议纪要文本的字典 {"meeting": str}。
    """
    input_path = Path(input_file)

    # 1. 读取转录文本
    if input_path.suffix.lower() == ".txt":
        transcription_text = input_path.read_text(encoding="utf-8")
    else:
        transcription_text = load_docx_text(input_path)

    if not transcription_text.strip():
        raise ValueError("转录文件内容为空。")

    # 2. 构造 system prompt（追加模板风格要求）
    system_content = GENERATE_SYSTEM_PROMPT
    if style_prompt.strip():
        system_content += f"\n\n【模板风格要求】\n{style_prompt.strip()}\n【模板风格要求结束】\n"

    # 3. 调用 LLM 生成会议纪要草稿
    llm = get_llm()
    user_prompt = GENERATE_USER_PROMPT_TEMPLATE.format(
        transcription_text=transcription_text,
        meeting_name=meeting_name or "未明确",
        meeting_time=meeting_time or "未明确",
        meeting_location=meeting_location or "未明确",
        meeting_chair=meeting_chair or "未明确",
        meeting_attendees=meeting_attendees or "未明确",
        meeting_departments=meeting_departments or "未明确",
        meeting_recorder=meeting_recorder or "未明确",
    )

    response = llm.invoke([
        SystemMessage(content=system_content),
        HumanMessage(content=user_prompt),
    ])

    meeting_text = response.content.strip()

    if not meeting_text:
        raise RuntimeError("LLM 生成的会议纪要为空")

    return {
        "meeting": meeting_text,
        "meeting_date": "",
        "push_dept": [],
        "push_user": [],
        "schedules": [],
    }


def run_transcription_parse(meeting_text: str) -> Dict[str, Any]:
    """阶段二：解析会议纪要 → 按部门分解工作任务。

    Args:
        meeting_text: 会议纪要文本（用户可编辑后传入）。

    Returns:
        结构化任务分解结果字典。
    """
    if not meeting_text.strip():
        raise ValueError("会议纪要内容为空，无法解析。")

    llm = get_llm()
    user_prompt = PARSE_USER_PROMPT_TEMPLATE.format(
        meeting_text=meeting_text,
    )

    response = llm.invoke([
        SystemMessage(content=PARSE_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ])

    raw_text = response.content

    try:
        data = extract_json_from_text(raw_text)
        for s in data.get("schedules", []):
            if isinstance(s.get("owner"), str):
                s["owner"] = [s["owner"]] if s["owner"] else []
        return data
    except (json.JSONDecodeError, ValueError) as e:
        debug_path = Path("data/output") / "parse_raw_output.txt"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(str(raw_text), encoding="utf-8")
        raise RuntimeError(
            f"任务分解解析失败，已保存原始输出：{debug_path}\n错误：{e}"
        ) from e
