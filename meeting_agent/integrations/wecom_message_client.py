from __future__ import annotations

from typing import Any, Dict

from meeting_agent.integrations.wecom_client import WeComClient


class WeComMessageClient(WeComClient):
    """企业微信消息客户端。

    职责：只负责发送应用消息。
    """

    def _send_message(
        self,
        *,
        msgtype: str,
        content_dict: dict,
        to_user: str = "",
        to_party: str = "",
        safe: int = 0,
    ) -> Dict[str, Any]:
        if not to_user and not to_party:
            raise ValueError("to_user 和 to_party 不能同时为空。")

        payload = {
            "touser": to_user,
            "toparty": to_party,
            "msgtype": msgtype,
            "agentid": self.config.agent_id,
            **content_dict,
            "safe": safe,
        }
        return self._request("POST", "/cgi-bin/message/send", data=payload)

    def send_text_message(
        self,
        *,
        content: str,
        to_user: str = "",
        to_party: str = "",
        safe: int = 0,
    ) -> Dict[str, Any]:
        """发送文本消息。"""
        return self._send_message(
            msgtype="text",
            content_dict={"text": {"content": content}},
            to_user=to_user,
            to_party=to_party,
            safe=safe,
        )

    def send_markdown_message(
        self,
        *,
        content: str,
        to_user: str = "",
        to_party: str = "",
        safe: int = 0,
    ) -> Dict[str, Any]:
        """发送 markdown 消息。"""
        return self._send_message(
            msgtype="markdown",
            content_dict={"markdown": {"content": content}},
            to_user=to_user,
            to_party=to_party,
            safe=safe,
        )
