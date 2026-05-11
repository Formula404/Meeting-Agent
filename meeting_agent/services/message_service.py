from meeting_agent.integrations.wecom_client import wecom_client


def send_meeting_summary(userids: list[str], meeting_title: str, summary: str, tasks: list) -> dict:
    lines = [
        f"【会议纪要】{meeting_title}",
        "",
        "会议总结：",
        summary,
        "",
        "待办事项："
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

    content = "\n".join(lines)

    return wecom_client.send_text_message(
        userids=userids,
        content=content,
    )