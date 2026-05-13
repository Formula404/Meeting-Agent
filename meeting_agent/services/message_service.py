from __future__ import annotations

import logging
from typing import Any, Mapping, Sequence

from meeting_agent.integrations.wecom_message_client import WeComMessageClient


wecom_message_client = WeComMessageClient()
logger = logging.getLogger(__name__)

_MAX_MARKDOWN_BYTES = 2000


def _split_content(content: str, max_bytes: int = _MAX_MARKDOWN_BYTES) -> list[str]:
    """Split markdown content at paragraph boundaries when it exceeds byte limit."""
    paragraphs = content.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []
    current_bytes = 0

    for para in paragraphs:
        para_bytes = len(para.encode("utf-8"))
        sep_bytes = 2 if current else 0  # "\n\n" separator

        if current_bytes + sep_bytes + para_bytes <= max_bytes:
            current.append(para)
            current_bytes += sep_bytes + para_bytes
        else:
            if current:
                chunks.append("\n\n".join(current))
            current = [para]
            current_bytes = para_bytes

    if current:
        chunks.append("\n\n".join(current))

    logger.info("_split_content: %d paragraphs → %d chunks (content=%d bytes, max=%d)",
                len(paragraphs), len(chunks), len(content.encode("utf-8")), max_bytes)
    if chunks:
        for i, c in enumerate(chunks):
            logger.info("  chunk %d: %d bytes", i + 1, len(c.encode("utf-8")))

    return chunks


def format_meeting_markdown(meeting_text: str) -> str:
    """将纯文本会议纪要转为 markdown 格式。

    规则：
    - 第一行（标题）→ ## 标题
    - 会议时间第二行 → **加粗**
    - 其余段落 → 首行缩进
    """
    lines = meeting_text.strip().split("\n")
    parts = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        if i == 0:
            parts.append(f"## {line}")
        elif i == 1:
            parts.append(f"**{line}**")
        else:
            parts.append(f"　　{line}")
    return "\n\n".join(parts)


def send_meeting_summary_from_result(
    result: Mapping[str, Any],
    userids: Sequence[str] | None = None,
    dept_ids: Sequence[str] | None = None,
) -> list[dict]:
    """按输出 JSON 结构发送会议纪要消息。

    规则：
    - 消息内容仅发送 result["meeting"]（转为 markdown 格式）。
    - 接收人优先用入参 userids，否则使用 result["push_user"]。
    - 接收部门优先用参 dept_ids，否则使用 result["push_dept"]。
    - 超过字节限制时按段落拆分多条发送。
    """
    to_users = userids if userids is not None else result.get("push_user", [])
    to_depts = dept_ids if dept_ids is not None else result.get("push_dept", [])
    meeting_text = str(result.get("meeting", "")).strip()
    if not to_users and not to_depts:
        raise ValueError("发送失败：未提供接收目标（push_user/userids 或 push_dept/dept_ids）。")
    if not meeting_text:
        raise ValueError("发送失败：meeting 为空。")

    markdown_content = format_meeting_markdown(meeting_text)
    chunks = _split_content(markdown_content)

    to_user_str = "|".join(to_users)
    to_party_str = "|".join(to_depts)

    logger.info("send_meeting_summary_from_result: meeting_text=%d bytes, markdown=%d bytes, chunks=%d",
                len(meeting_text.encode("utf-8")), len(markdown_content.encode("utf-8")), len(chunks))

    responses: list[dict] = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        if total > 1:
            chunk = f"（{i + 1}/{total}）\n\n{chunk}"
        responses.append(
            wecom_message_client.send_markdown_message(
                content=chunk,
                to_user=to_user_str,
                to_party=to_party_str,
            )
        )

    return responses


def send_meeting_summary(userids: list[str], meeting_title: str, summary: str, tasks: list) -> dict:
    """兼容旧接口，继续可用。"""
    lines = [
        f"【会议纪要】{meeting_title}",
        "",
        "会议总结：",
        summary,
        "",
        "待办事项：",
    ]

    for i, task in enumerate(tasks, start=1):
        owner = "、".join(task.owner) if hasattr(task, "owner") else ""
        deadline = task.deadline or "待确认"
        remark = task.remark or ""
        lines.append(
            f"{i}. {task.task}\n"
            f"   负责人：{owner}\n"
            f"   截止时间：{deadline}\n"
            f"   备注：{remark}"
        )

    return wecom_message_client.send_text_message(
        content="\n".join(lines),
        to_user="|".join(userids),
    )
