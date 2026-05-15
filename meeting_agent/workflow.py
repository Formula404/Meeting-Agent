# 导入处理JSON的工具
import json
# 导入正则表达式工具（用来从AI输出里抠出JSON）
import re
# 导入文件路径工具
from pathlib import Path

# LangChain 消息类型：系统提示词、用户提示词
from langchain_core.messages import SystemMessage, HumanMessage
# Pydantic 格式校验错误
from pydantic import ValidationError

# 导入你自己写的所有模块！！！
from meeting_agent.document_loader import load_docx_text  # 读取Word
from meeting_agent.llm import get_llm                    # 获取AI模型
from meeting_agent.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE  # 提示词
from meeting_agent.schemas import MeetingOutput          # 输出格式


# ----------------------
# 工具函数：从AI返回的文本里提取出 JSON 内容
# 处理AI偶尔会返回 ```json {...} ``` 这种格式
# ----------------------
def extract_json_from_text(text: str) -> dict:
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


# ----------------------
# 核心函数：输入会议纪要文本 → 输出结构化结果（MeetingOutput）
# 由 run_meeting_extraction 和 run_meeting_extraction_from_text 共用
# ----------------------
def _extract_from_meeting_text(
    meeting_text: str,
) -> MeetingOutput:
    """给定会议纪要文本，调用 LLM 提取结构化数据。"""
    # 1. 获取配置好的 AI 大模型
    llm = get_llm()

    # 2. 拼接用户提示词：把会议文本填进模板
    user_prompt = USER_PROMPT_TEMPLATE.format(meeting_text=meeting_text)

    # 3. 调用大模型！
    response = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),  # 系统规则
            HumanMessage(content=user_prompt),     # 会议内容 + 输出格式
        ]
    )

    # AI 返回的原始文本
    raw_text = response.content

    # 4. 解析 AI 返回的 JSON
    try:
        data = extract_json_from_text(raw_text)  # 提取JSON
        result = MeetingOutput.model_validate(data)  # 校验格式是否正确
    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        debug_path = Path("data/output") / "raw_model_output.txt"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(str(raw_text), encoding="utf-8")
        raise RuntimeError(
            f"结构化解析失败，已保存原始输出：{debug_path}\n错误：{e}"
        ) from e

    return result


# ----------------------
# 主函数：输入一个Word会议纪要 → 输出结构化结果（MeetingOutput）
# ----------------------
def run_meeting_extraction(
    input_docx: str | Path,    # 输入：会议纪要 .docx 文件
    output_dir: str | Path = "data/output"  # 输出：结果保存目录
) -> MeetingOutput:

    # 1. 路径处理
    input_docx = Path(input_docx)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)  # 自动创建输出目录

    # 2. 读取 Word 文档 → 纯文本
    meeting_text = load_docx_text(input_docx)

    # 3. 提取结构化数据
    result = _extract_from_meeting_text(meeting_text)

    # 4. 把最终结果保存成 JSON 文件
    output_path = output_dir / f"{input_docx.stem}_result.json"
    output_path.write_text(
        result.model_dump_json(indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 返回结构化结果给程序用
    return result


# ----------------------
# 文本版：直接输入会议纪要文本 → 输出结构化结果（MeetingOutput）
# 用于录音转录流程中，用户编辑完文本后调用
# ----------------------
def run_meeting_extraction_from_text(
    meeting_text: str,           # 输入：会议纪要文本
) -> MeetingOutput:
    """直接输入会议纪要文本，运行 LLM 提取结构化数据（不经过 .docx 文件）。"""
    return _extract_from_meeting_text(meeting_text)