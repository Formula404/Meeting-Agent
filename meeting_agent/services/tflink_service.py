"""tflink 临时文件上传服务 —— 用于中转大文件到腾讯云 ASR"""

from __future__ import annotations

from pathlib import Path

import httpx

TFLINK_UPLOAD_URL = "https://tmpfile.link/api/upload"
MAX_TFLINK_FILE_SIZE = 100 * 1024 * 1024  # tflink 单文件上限 100MB


def upload_to_tflink(file_path: Path) -> str:
    """匿名上传文件到 tflink，返回公网可访问的下载链接。

    Args:
        file_path: 本地文件路径。

    Returns:
        文件的公网下载链接（downloadLink），可用于腾讯云 ASR URL 拉取。

    Raises:
        RuntimeError: 上传失败或响应异常时。
    """
    file_size = file_path.stat().st_size
    if file_size > MAX_TFLINK_FILE_SIZE:
        raise RuntimeError(
            f"文件大小 ({file_size / 1024 / 1024:.1f}MB) 超过 tflink 限制 (100MB)"
        )

    try:
        with httpx.Client(timeout=120.0) as client:
            with file_path.open("rb") as f:
                resp = client.post(
                    TFLINK_UPLOAD_URL,
                    files={"file": f},
                )
    except httpx.TimeoutException as e:
        raise RuntimeError("上传文件到 tflink 超时，请检查网络连接") from e
    except httpx.RequestError as e:
        raise RuntimeError(f"上传文件到 tflink 失败: {e}") from e

    if resp.status_code != 200:
        raise RuntimeError(
            f"tflink 上传返回异常状态码 {resp.status_code}: {resp.text[:200]}"
        )

    try:
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f"解析 tflink 响应失败: {e}") from e

    download_link = data.get("downloadLinkEncoded") or data.get("downloadLink")
    if not download_link:
        raise RuntimeError("tflink 响应中未找到下载链接")

    return download_link
