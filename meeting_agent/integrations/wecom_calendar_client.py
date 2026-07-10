from __future__ import annotations

from typing import Any, Dict, List

from meeting_agent.integrations.wecom_client import WeComClient


class WeComCalendarClient(WeComClient):
    """企业微信日程客户端。"""

    # WeCom 支持的 remind_before_event_secs 有效值
    _VALID_REMIND_SECS = {0, 300, 900, 3600, 86400}

    @staticmethod
    def _normalize_remind_seconds(seconds: int) -> int:
        """将秒数就近映射到 WeCom 支持的 remind_before_event_secs 有效值。"""
        if seconds <= 0:
            return 0
        valid = sorted(WeComCalendarClient._VALID_REMIND_SECS)
        return min(valid, key=lambda x: abs(x - seconds))

    def create_schedule(
        self,
        *,
        summary: str,
        description: str,
        start_time: int,
        end_time: int,
        attendees: List[str] | None = None,
        admins: List[str] | None = None,
        remind_before_secs: int = 0,
    ) -> Dict[str, Any]:
        """创建日程。

        Args:
            summary: 日程标题
            description: 日程描述
            start_time: 开始时间（Unix 秒）
            end_time: 结束时间（Unix 秒）
            attendees: 参与者 userid 列表
            admins: 管理员 userid 列表（最多 3 人，选填）
            remind_before_secs: 提前多少秒提醒，0 表示不提醒
        """
        schedule: dict = {
            "start_time": start_time,
            "end_time": end_time,
            "attendees": [{"userid": uid} for uid in (attendees or [])],
            "summary": summary,
            "description": description,
        }

        if admins:
            schedule["admins"] = admins

        remind_secs = self._normalize_remind_seconds(remind_before_secs)
        if remind_secs > 0:
            schedule["reminders"] = {
                "is_remind": 1,
                "remind_before_event_secs": remind_secs,
            }

        return self._request("POST", "/cgi-bin/oa/schedule/add", data={"schedule": schedule})
