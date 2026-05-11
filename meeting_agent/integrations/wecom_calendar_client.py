from __future__ import annotations

from typing import Any, Dict, List

from meeting_agent.integrations.wecom_client import WeComClient


class WeComCalendarClient(WeComClient):
    """企业微信日程客户端。

    职责：只负责创建日程。
    """

    def create_schedule(
        self,
        *,
        organizer_userid: str,
        summary: str,
        description: str,
        start_time: int,
        end_time: int,
        attendees: List[str] | None = None,
    ) -> Dict[str, Any]:
        """创建日程。

        参数：
        - organizer_userid: 组织者 userid。
        - summary: 日程标题。
        - description: 日程描述。
        - start_time/end_time: Unix 时间戳（秒）。
        - attendees: 参会人 userid 列表。
        """
        payload = {
            "schedule": {
                "organizer": organizer_userid,
                "summary": summary,
                "description": description,
                "start_time": {"timestamp": start_time},
                "end_time": {"timestamp": end_time},
                "attendees": [{"userid": uid} for uid in (attendees or [])],
            }
        }

        return self._request("POST", "/cgi-bin/oa/schedule/add", data=payload)
