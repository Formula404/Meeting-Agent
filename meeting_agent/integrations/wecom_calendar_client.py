from __future__ import annotations

from typing import Any, Dict, List

from meeting_agent.integrations.wecom_client import WeComClient


class WeComCalendarClient(WeComClient):
    """企业微信日程客户端。"""

    def create_schedule(
        self,
        *,
        summary: str,
        description: str,
        start_time: int,
        end_time: int,
        attendees: List[str] | None = None,
    ) -> Dict[str, Any]:
        """创建日程（按约定仅保留核心字段）。"""
        payload = {
            "schedule": {
                "start_time": start_time,
                "end_time": end_time,
                "attendees": [{"userid": uid} for uid in (attendees or [])],
                "summary": summary,
                "description": description,
            }
        }
        return self._request("POST", "/cgi-bin/oa/schedule/add", data=payload)
