from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib import error, parse, request

from meeting_agent.config import get_settings


# 企业微信所有 API 请求的基础地址。
# 企业微信官方文档中所有接口都使用这个域名。
WECOM_API_BASE = "https://qyapi.weixin.qq.com"


@dataclass
class WeComConfig:
    """企业微信的鉴权配置信息。

    这个 dataclass 只是打包三个字段，不包含任何逻辑。
    三个字段分别对应：哪个企业、用什么应用密钥、哪个应用在发消息。

    Attributes:
        corp_id:     企业微信后台 -> "我的企业" -> "企业ID"。标识你的企业。
        corp_secret: 应用详情页里的 Secret。相当于该应用的密码。
        agent_id:    应用详情页里的 AgentId。标识使用哪个应用。
    """

    corp_id: str
    corp_secret: str
    agent_id: int


class WeComClient:
    """企业微信 API 的基础客户端。

    这个类只做"所有业务模块都要用"的公共事情：
    1. 从 config 或环境变量读取企业微信配置。
    2. 管理 access_token 的获取和缓存。
    3. 统一发起 HTTP 请求，处理 token 过期自动刷新和错误解析。

    具体的业务逻辑（如发消息、创建日程）不写在这里，
    由各自的客户端类（WeComMessageClient、WeComCalendarClient）继承或组合这个类来实现。
    """

    def __init__(self, config: Optional[WeComConfig] = None) -> None:
        """初始化客户端。

        如果外部没有传入配置，就从项目统一的配置模块（环境变量）中读取。
        这样在单元测试时可以直接传入 mock 配置，不需要依赖真实环境变量。

        Args:
            config: 可选。传入 WeComConfig 则直接使用，不传则从环境变量读取。
        """
        # ---------------------------------------------------------------
        # 第一步：确定配置来源
        # ---------------------------------------------------------------
        # 外部没有传 config → 从项目的 settings（即环境变量）中读取。
        if config is None:
            settings = get_settings()  # 这个函数会加载.env文件中的配置
            config = WeComConfig(
                corp_id=settings.WECOM_CORP_ID,
                corp_secret=settings.WECOM_CORP_SECRET,
                agent_id=settings.WECOM_AGENT_ID,
            )

        # ---------------------------------------------------------------
        # 第二步：校验关键配置不能为空
        # ---------------------------------------------------------------
        # corp_id 和 corp_secret 是调用任何企业微信 API 的前提条件，
        # 缺少任何一个都无法获取 access_token，后续所有请求都会失败。
        if not config.corp_id or not config.corp_secret:
            raise ValueError("缺少企业微信配置：WECOM_CORP_ID 或 WECOM_CORP_SECRET")

        # ---------------------------------------------------------------
        # 第三步：保存配置并初始化 token 缓存
        # ---------------------------------------------------------------
        self.config = config
        # access_token 有 7200 秒有效期。把它缓存在实例中，
        # 避免每次发请求都重新获取，减少网络开销和被接口限流的风险。
        self._access_token: Optional[str] = None  # 缓存的 token 字符串
        self._token_expires_at: float = 0.0  # token 过期的时间戳（Unix 时间）

    # ------------------------------------------------------------------
    # 获取 access_token
    # ------------------------------------------------------------------
    def get_access_token(self, force_refresh: bool = False) -> str:
        """获取企业微信的 access_token。

        access_token 是企业微信 API 的调用凭证，几乎所有接口都需要它。
        它的有效期通常为 7200 秒（2 小时），过期后必须重新获取。

        这个方法做了三件事：
        1. 检查本地缓存的 token 是否还在有效期内。
        2. 如果已过期（或强制刷新），向企业微信服务器请求新的 token。
        3. 将新 token 缓存下来并返回。

        Args:
            force_refresh: True 时忽略缓存，强制从服务器重新获取。

        Returns:
            有效的 access_token 字符串。
        """
        now = time.time()

        # ---------------------------------------------------------------
        # 第一步：检查缓存是否可用
        # ---------------------------------------------------------------
        # 三个条件同时满足时才复用缓存：
        #   a) self._access_token 不为空（之前成功获取过）
        #   b) force_refresh 为 False（没有要求强制刷新）
        #   c) 当前时间还没到过期时间（缓存仍有效）
        if self._access_token and not force_refresh and now < self._token_expires_at:
            return self._access_token  # 直接返回缓存的 token，不需要 HTTP 请求

        # ---------------------------------------------------------------
        # 第二步：缓存不可用 → 发请求获取新 token
        # ---------------------------------------------------------------
        # 调用 _request 方法发起 GET 请求。
        # 注意 include_token=False：获取 token 的接口本身不需要 token。
        response = self._request(
            method="GET",
            path="/cgi-bin/gettoken",
            query={
                "corpid": self.config.corp_id,
                "corpsecret": self.config.corp_secret,
            },
            include_token=False,
        )

        # ---------------------------------------------------------------
        # 第三步：解析响应，提取 token
        # ---------------------------------------------------------------
        # 成功时企业微信返回: {"errcode":0, "errmsg":"ok", "access_token":"xxx", "expires_in":7200}
        token = response.get("access_token", "")
        if not token:
            # 如果 access_token 字段为空，说明请求出错了，
            # 把整个响应内容抛出去方便排查。
            raise RuntimeError(f"获取 access_token 失败: {response}")

        # ---------------------------------------------------------------
        # 第四步：缓存新 token
        # ---------------------------------------------------------------
        expires_in = int(response.get("expires_in", 7200))
        self._access_token = token
        # 预留 60 秒安全窗口：
        # 假设 expires_in=7200，我们只认为它在 7140 秒内有效。
        # 这样可以避免并发请求时刚好在过期边界撞上 token 失效。
        self._token_expires_at = time.time() + max(expires_in - 60, 0)
        return token

    # ------------------------------------------------------------------
    # 统一 HTTP 请求方法
    # ------------------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        query: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        include_token: bool = True,
    ) -> Dict[str, Any]:
        """统一的 HTTP 请求入口。

        所有企业微信 API 的请求都经过这个方法，它集中处理：
        1. 自动追加 access_token（除了获取 token 的接口本身）。
        2. 序列化请求体为 JSON。
        3. 发起 HTTP 请求。
        4. token 过期自动刷新并重试一次。
        5. 解析和校验响应内容。

        Args:
            method:        HTTP 方法，如 "GET" 或 "POST"。
            path:          API 路径，如 "/cgi-bin/message/send"。
            query:         URL 查询参数字典，会拼接到 URL 问号后面。
            data:          JSON 请求体字典，会自动序列化。
            include_token: 是否自动在 query 中追加 access_token。
                           False 仅用于获取 token 自身的接口。

        Returns:
            企业微信返回的 JSON 解析后的字典。
            正常情况下包含 "errcode": 0 和业务数据字段。
        """
        # ---------------------------------------------------------------
        # 第一步：组装 URL
        # ---------------------------------------------------------------
        # 从 query 参数开始构建。如果调用方传了额外参数，先拷贝一份再操作。
        query_params: Dict[str, Any] = dict(query or {})

        # 大多数接口需要在 URL 参数里带上 access_token。
        # 这里会调用 get_access_token()，内部可能触发一次 token 获取请求。
        if include_token:
            query_params["access_token"] = self.get_access_token()

        # 将参数字典编码成 URL 查询字符串格式，如 "access_token=xxx&key=value"。
        query_string = parse.urlencode(query_params)

        # 拼接完整的请求 URL。
        url = f"{WECOM_API_BASE}{path}"
        if query_string:
            url = f"{url}?{query_string}"

        # ---------------------------------------------------------------
        # 第二步：准备请求体
        # ---------------------------------------------------------------
        body = None
        headers = {"Content-Type": "application/json"}
        if data is not None:
            # 企业微信所有接口的请求体都是 JSON 格式。
            # ensure_ascii=False 保证中文不会变成 \uXXXX 转义序列，
            # 便于排查问题时直接查看请求内容。
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")

        # ---------------------------------------------------------------
        # 第三步：发送 HTTP 请求
        # ---------------------------------------------------------------
        # 使用 Python 标准库 urllib 发起请求。
        # 超时设为 20 秒，防止网络异常时请求一直挂住。
        req = request.Request(url=url, data=body, headers=headers, method=method.upper())

        try:
            with request.urlopen(req, timeout=20) as resp:
                payload = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            # HTTP 层面返回了 4xx/5xx，比如 502 Bad Gateway。
            # 读取错误响应体里的详情一并吐出，方便排查。
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"企业微信 HTTP 错误: {exc.code}, {detail}") from exc
        except error.URLError as exc:
            # 网络层面失败，比如 DNS 解析失败、连接被拒绝。
            raise RuntimeError(f"企业微信网络请求失败: {exc.reason}") from exc

        # ---------------------------------------------------------------
        # 第四步：解析响应 JSON
        # ---------------------------------------------------------------
        # 企业微信所有接口都返回 JSON 格式，先尝试解析。
        try:
            result = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"企业微信返回非 JSON: {payload}") from exc

        # ---------------------------------------------------------------
        # 第五步：检查错误码，处理 token 过期自动重试
        # ---------------------------------------------------------------
        # 企业微信的响应体总是包含 errcode 字段：
        #   - 0    表示成功
        #   - 40014 表示 access_token 无效
        #   - 42001 表示 access_token 已过期
        errcode = result.get("errcode", 0)

        # 如果是 token 相关的错误（40014 或 42001），
        # 说明我们缓存的 token 已经失效了（可能在别的服务中被重置了）。
        # 做法：强制刷新 token，然后重新发起当前请求。
        if include_token and errcode in {40014, 42001}:
            # 强制刷新本地缓存的 access_token。
            self.get_access_token(force_refresh=True)
            # 用新 token 重试当前请求，递归调用自身。
            # 重试只做一次，如果还是失败就让它抛出异常，避免无限循环。
            return self._request(
                method=method,
                path=path,
                query=query,
                data=data,
                include_token=True,
            )

        # 其他非零错误码 → 直接抛出异常。
        if errcode != 0:
            raise RuntimeError(
                f"企业微信接口报错: errcode={errcode}, errmsg={result.get('errmsg')}, response={result}"
            )

        # ---------------------------------------------------------------
        # 第六步：返回成功结果
        # ---------------------------------------------------------------
        return result
