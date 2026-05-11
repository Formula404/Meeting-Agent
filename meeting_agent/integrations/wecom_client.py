from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib import error, parse, request

from meeting_agent.config import get_settings


# 企业微信 API 根地址。
WECOM_API_BASE = "https://qyapi.weixin.qq.com"


@dataclass
class WeComConfig:
    """企业微信相关配置。

    作用：
    1. 保存鉴权和应用标识字段。
    2. 由 config.py 统一读取环境变量后在这里使用。
    """

    corp_id: str
    corp_secret: str
    agent_id: int


class WeComClient:
    """企业微信基础客户端。

    这个类只处理“公共逻辑”：
    1. 读取企业微信配置。
    2. 获取 access_token。
    3. 统一发起 HTTP 请求并处理错误。

    业务逻辑（发消息、建日程）不要写在这里，
    由专门的客户端文件分别实现。
    """

    def __init__(self, config: Optional[WeComConfig] = None) -> None:
        # 如果外部没传配置，则从项目统一配置中读取。
        if config is None:
            settings = get_settings()
            config = WeComConfig(
                corp_id=settings.WECOM_CORP_ID,
                corp_secret=settings.WECOM_CORP_SECRET,
                agent_id=settings.WECOM_AGENT_ID,
            )

        if not config.corp_id or not config.corp_secret:
            raise ValueError("缺少企业微信配置：WECOM_CORP_ID 或 WECOM_CORP_SECRET")

        self.config = config
        # token 缓存在实例中，避免每次请求都重复获取。
        self._access_token: Optional[str] = None

    def get_access_token(self, force_refresh: bool = False) -> str:
        """获取 access_token。

        - 默认复用实例缓存 token。
        - force_refresh=True 时强制重新拉取。
        """
        if self._access_token and not force_refresh:
            return self._access_token

        response = self._request(
            method="GET",
            path="/cgi-bin/gettoken",
            query={
                "corpid": self.config.corp_id,
                "corpsecret": self.config.corp_secret,
            },
            include_token=False,
        )

        token = response.get("access_token", "")
        if not token:
            raise RuntimeError(f"获取 access_token 失败: {response}")

        self._access_token = token
        return token

    def _request(
        self,
        method: str,
        path: str,
        query: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        include_token: bool = True,
    ) -> Dict[str, Any]:
        """统一请求入口。

        参数说明：
        - method: HTTP 方法（GET/POST）。
        - path: API 路径，如 /cgi-bin/message/send。
        - query: URL 查询参数。
        - data: JSON 请求体。
        - include_token: 是否自动追加 access_token。
        """
        query_params: Dict[str, Any] = dict(query or {})
        if include_token:
            query_params["access_token"] = self.get_access_token()

        query_string = parse.urlencode(query_params)
        url = f"{WECOM_API_BASE}{path}"
        if query_string:
            url = f"{url}?{query_string}"

        body = None
        headers = {"Content-Type": "application/json"}
        if data is not None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")

        req = request.Request(url=url, data=body, headers=headers, method=method.upper())

        try:
            with request.urlopen(req, timeout=20) as resp:
                payload = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"企业微信 HTTP 错误: {exc.code}, {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"企业微信网络请求失败: {exc.reason}") from exc

        try:
            result = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"企业微信返回非 JSON: {payload}") from exc

        errcode = result.get("errcode", 0)
        if errcode != 0:
            raise RuntimeError(
                f"企业微信接口报错: errcode={errcode}, errmsg={result.get('errmsg')}, response={result}"
            )
        return result
