from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import httpx

from meeting_agent.integrations.wecom_client import WECOM_API_BASE, WeComClient


class WeComFileClient(WeComClient):
    """企业微信文件客户端。

    负责上传文件到临时素材，以及发送文件消息。
    """

    def upload_media(self, file_path: str | Path, file_type: str = "file") -> str:
        """上传文件到企业微信临时素材。

        上传后得到 media_id，有效期 3 天。
        目前仅用于发送文件消息，故 file_type 固定为 "file"。

        Args:
            file_path: 本地文件路径。
            file_type: 媒体文件类型，默认 "file"。

        Returns:
            media_id 字符串，用于后续发送文件消息。
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")

        token = self.get_access_token()
        url = f"{WECOM_API_BASE}/cgi-bin/media/upload?access_token={token}&type={file_type}"

        with httpx.Client() as client:
            resp = client.post(url, files={"media": (path.name, path.read_bytes())})
            result = resp.json()

        errcode = result.get("errcode", 0)
        if errcode != 0:
            raise RuntimeError(
                f"企业微信素材上传失败: errcode={errcode}, errmsg={result.get('errmsg')}, response={result}"
            )

        media_id = result.get("media_id", "")
        if not media_id:
            raise RuntimeError(f"企业微信素材上传返回缺少 media_id: {result}")
        return media_id

    def send_file_message(
        self,
        *,
        media_id: str,
        to_user: str = "",
        to_party: str = "",
        safe: int = 0,
    ) -> Dict[str, Any]:
        """发送文件消息。

        Args:
            media_id: 通过 upload_media 获取的 media_id。
            to_user:  接收人 userid，多个用 | 分隔。
            to_party: 接收部门 id，多个用 | 分隔。
            safe:     是否为保密消息。

        Returns:
            企业微信 API 返回的响应字典。
        """
        if not to_user and not to_party:
            raise ValueError("to_user 和 to_party 不能同时为空。")

        return self._request(
            method="POST",
            path="/cgi-bin/message/send",
            data={
                "touser": to_user,
                "toparty": to_party,
                "msgtype": "file",
                "agentid": self.config.agent_id,
                "file": {"media_id": media_id},
                "safe": safe,
            },
        )
