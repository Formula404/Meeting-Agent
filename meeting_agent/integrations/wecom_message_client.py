from __future__ import annotations

from typing import Any, Dict

from meeting_agent.integrations.wecom_client import WeComClient


class WeComMessageClient(WeComClient):
    """企业微信消息客户端。

    职责：只负责发送应用消息。
    """

    def send_text_message(self, *, to_user: str, content: str, safe: int = 0) -> Dict[str, Any]:
        """发送文本消息。

        参数：
        - to_user: 接收人，多个用 "|" 分隔。
        - content: 消息正文。
        - safe: 是否保密消息，0/1。
        """
        payload = {
            "touser": to_user,
            "msgtype": "text",
            "agentid": self.config.agent_id,
            "text": {"content": content},
            "safe": safe,
        }
        return self._request("POST", "/cgi-bin/message/send", data=payload)
