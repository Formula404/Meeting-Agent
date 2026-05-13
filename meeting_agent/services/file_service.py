from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from meeting_agent.integrations.wecom_file_client import WeComFileClient

INPUT_DIR = Path("data/input")
PDF_DIR = INPUT_DIR / "pdfs"

wecom_file_client = WeComFileClient()


def send_file_from_result(
    result: Mapping[str, Any],
    userids: Sequence[str] | None = None,
    dept_ids: Sequence[str] | None = None,
) -> dict:
    """根据 result 记录，将关联的文件（PDF 优先，否则 docx）推送到企业微信。

    流程：
    1. 确定要发送的文件路径（pdf_filename 优先 → original_filename 兜底）。
    2. 上传到企业微信临时素材，获取 media_id。
    3. 发送文件消息给指定接收人。

    Args:
        result: 数据库中的 extraction_results 记录，需包含
                pdf_filename 和 original_filename 字段。
        userids: 接收人 userid 列表。不传则从 result 中取 push_user。
        dept_ids: 接收部门 id 列表。不传则从 result 中取 push_dept。

    Returns:
        企业微信文件消息 API 的返回字典。
    """
    to_users = userids if userids is not None else result.get("push_user", [])
    to_depts = dept_ids if dept_ids is not None else result.get("push_dept", [])
    if not to_users and not to_depts:
        raise ValueError("发送失败：未提供接收目标。")

    # 确定要发送的文件路径：PDF 优先，否则用原始 docx
    file_path = _resolve_file_path(result)
    if file_path is None:
        raise ValueError(
            f"发送失败：找不到关联文件（pdf_filename={result.get('pdf_filename')!r}, "
            f"original_filename={result.get('original_filename')!r}）"
        )

    # 上传到企业微信临时素材
    media_id = wecom_file_client.upload_media(file_path)

    # 发送文件消息
    return wecom_file_client.send_file_message(
        media_id=media_id,
        to_user="|".join(to_users),
        to_party="|".join(to_depts),
    )


def _resolve_file_path(result: Mapping[str, Any]) -> Path | None:
    """解析 result 记录对应的文件路径。

    优先顺序：
    1. PDF 文件（pdfs/ 目录下）。
    2. 原始 .docx 文件（input/ 目录下）。
    """
    pdf_name = result.get("pdf_filename", "") or ""
    if pdf_name:
        candidate = PDF_DIR / pdf_name
        if candidate.exists():
            return candidate

    docx_name = result.get("original_filename", "") or ""
    if docx_name:
        candidate = INPUT_DIR / docx_name
        if candidate.exists():
            return candidate

    return None
