from __future__ import annotations

from typing import Any, Mapping, Sequence

from meeting_agent.integrations.wecom_message_client import WeComMessageClient


wecom_message_client = WeComMessageClient()


def send_meeting_summary_from_result(
    result: Mapping[str, Any],
    userids: Sequence[str] | None = None,
    dept_ids: Sequence[str] | None = None,
) -> dict:
    """按输出 JSON 结构发送会议纪要消息。

    规则：
    - 消息内容仅发送 result["meeting"]。
    - 接收人优先用入参 userids，否则使用 result["push_user"]。
    - 接收部门优先用入参 dept_ids，否则使用 result["push_dept"]。
    """
    to_users = list(userids) if userids is not None else list(result.get("push_user", []))
    to_depts = list(dept_ids) if dept_ids is not None else list(result.get("push_dept", []))
    meeting_text = str(result.get("meeting", "")).strip()
    if not to_users and not to_depts:
        raise ValueError("发送失败：未提供接收目标（push_user/userids 或 push_dept/dept_ids）。")
    if not meeting_text:
        raise ValueError("发送失败：meeting 为空。")

    return wecom_message_client.send_text_message(
        content=meeting_text,
        to_user="|".join(map(str, to_users)),
        to_party="|".join(map(str, to_depts)),
    )


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
