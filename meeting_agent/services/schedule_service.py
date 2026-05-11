from __future__ import annotations

from typing import Any, Mapping

from meeting_agent.integrations.wecom_calendar_client import WeComCalendarClient


wecom_calendar_client = WeComCalendarClient()


def _as_int_timestamp(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} 必须是时间戳（秒），当前值: {value!r}") from exc


def create_meeting_schedules_from_result(
    result: Mapping[str, Any],
) -> list[dict]:
    """按输出 JSON 结构批量创建企业微信日程。

    字段映射：
    - schedules[].title -> summary
    - schedules[].description -> description
    - schedules[].owner -> attendees(userid)
    - schedules[].start_time/end_time -> Unix 时间戳（秒）
    """
    schedule_items = result.get("schedules", []) or []
    responses: list[dict] = []

    for idx, item in enumerate(schedule_items, start=1):
        title = str(item.get("title", "")).strip()
        if not title:
            raise ValueError(f"schedules[{idx}] 缺少 title。")

        description = str(item.get("description", "")).strip()
        attendees = list(item.get("owner", []) or [])

        start_ts = _as_int_timestamp(item.get("start_time"), f"schedules[{idx}].start_time")
        end_ts = _as_int_timestamp(item.get("end_time"), f"schedules[{idx}].end_time")
        if end_ts <= start_ts:
            raise ValueError(f"schedules[{idx}] 的 end_time 必须大于 start_time。")

        responses.append(
            wecom_calendar_client.create_schedule(
                summary=title,
                description=description,
                start_time=start_ts,
                end_time=end_ts,
                attendees=attendees,
            )
        )

    return responses
