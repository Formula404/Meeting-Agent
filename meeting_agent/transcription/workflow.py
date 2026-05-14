"""转录处理工作流 —— 独立于主流程 workflow.py"""

import json
import re
from pathlib import Path
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import ValidationError

from meeting_agent.document_loader import load_docx_text
from meeting_agent.llm import get_llm
from meeting_agent.transcription.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from meeting_agent.transcription.schemas import TranscriptionOutput


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
    custom_prompt: str,
) -> TranscriptionOutput:
    """主函数：输入录音转文字文件 + 自定义提示词 → 输出结构化会议纪要。

    Args:
        input_file: 录音转文字文件路径（支持 .docx 或 .txt）。
        custom_prompt: 用户自定义的提取要求。

    Returns:
        验证通过的结构化会议纪要 TranscriptionOutput。
    """
    input_path = Path(input_file)

    # 1. 读取转录文本
    if input_path.suffix.lower() == ".txt":
        transcription_text = input_path.read_text(encoding="utf-8")
    else:
        transcription_text = load_docx_text(input_path)

    if not transcription_text.strip():
        raise ValueError("转录文件内容为空。")

    # 2. 调用 LLM
    llm = get_llm()
    user_prompt = USER_PROMPT_TEMPLATE.format(
        custom_prompt=custom_prompt,
        transcription_text=transcription_text,
    )

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ])

    raw_text = response.content

    # 3. 解析 JSON
    try:
        data = extract_json_from_text(raw_text)
        # 将 schedules 中的 owner 统一转为数组
        for s in data.get("schedules", []):
            if isinstance(s.get("owner"), str):
                s["owner"] = [s["owner"]] if s["owner"] else []
        result = TranscriptionOutput.model_validate(data)
    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        debug_path = Path("data/output") / "transcription_raw_output.txt"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(str(raw_text), encoding="utf-8")
        raise RuntimeError(
            f"结构化解析失败，已保存原始输出：{debug_path}\n错误：{e}"
        ) from e

    return result
