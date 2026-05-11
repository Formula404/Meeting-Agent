from __future__ import annotations

from typing import Any, Dict

from meeting_agent.integrations.wecom_client import WeComClient


class WeComMessageClient(WeComClient):
    """企业微信消息客户端。

    职责：只负责发送应用消息。
    """

    def send_text_message(
        self,
        *,
        content: str,
        to_user: str = "",
        to_party: str = "",
        safe: int = 0,
    ) -> Dict[str, Any]:
        """发送文本消息。

        参数：
        - to_user: 接收人，多个用 "|" 分隔。
        - to_party: 接收部门，多个用 "|" 分隔（部门 ID）。
        - content: 消息正文。
        - safe: 是否保密消息，0/1。
        """
        if not to_user and not to_party:
            raise ValueError("to_user 和 to_party 不能同时为空。")

        payload = {
            "touser": to_user,
            "toparty": to_party,
            "msgtype": "text",
            "agentid": self.config.agent_id,
            "text": {"content": content},
            "safe": safe,
        }
        return self._request("POST", "/cgi-bin/message/send", data=payload)
