"""腾讯云语音识别 ASR 服务 —— 录音文件识别"""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Optional

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.asr.v20190614 import asr_client, models

from meeting_agent.config import get_settings

# 音频文件 5MB 上限（SourceType=1 直传数据限制）
MAX_FILE_SIZE = 5 * 1024 * 1024

# 支持的音频扩展名
SUPPORTED_AUDIO_EXTENSIONS = {
    ".wav", ".mp3", ".m4a", ".flv", ".mp4", ".wma",
    ".3gp", ".amr", ".aac", ".ogg", ".flac",
}

POLL_INTERVAL = 3  # 轮询间隔（秒）
MAX_POLL_TIME = 1800  # 最长等待 30 分钟


def _get_client() -> asr_client.AsrClient:
    settings = get_settings()
    if not settings.TENCENT_SECRET_ID or not settings.TENCENT_SECRET_KEY:
        raise RuntimeError("TENCENT_SECRET_ID / TENCENT_SECRET_KEY 未配置")
    cred = credential.Credential(settings.TENCENT_SECRET_ID, settings.TENCENT_SECRET_KEY)
    return asr_client.AsrClient(cred, "ap-shanghai")


def create_rec_task(audio_data: bytes) -> int:
    """提交录音文件识别任务（直传模式），返回 TaskId。

    Args:
        audio_data: 音频文件原始字节数据（≤5MB）。

    Returns:
        识别任务的 TaskId。
    """
    if len(audio_data) > MAX_FILE_SIZE:
        raise ValueError(f"音频文件超过 {MAX_FILE_SIZE // 1024 // 1024}MB 限制")

    client = _get_client()
    req = models.CreateRecTaskRequest()
    req.EngineModelType = "16k_zh"  # 中文普通话通用引擎（标准版，兼容大部分资源包）
    req.ChannelNum = 1
    req.ResTextFormat = 2  # 详细识别结果 + 词级时间戳 + 标点
    req.SourceType = 1  # 直接上传音频数据
    req.Data = base64.b64encode(audio_data).decode("ascii")
    req.DataLen = len(audio_data)

    try:
        resp = client.CreateRecTask(req)
    except TencentCloudSDKException as e:
        raise RuntimeError(f"创建 ASR 任务失败: {e}") from e

    return resp.Data.TaskId


def create_rec_task_from_url(audio_url: str) -> int:
    """提交录音文件识别任务（URL 拉取模式），返回 TaskId。

    通过公网可访问的音频文件 URL 提交识别，无 5MB 大小限制。
    URL 需保证腾讯云 ASR 服务可正常访问。

    Args:
        audio_url: 音频文件的公网可访问 URL。

    Returns:
        识别任务的 TaskId。
    """
    client = _get_client()
    req = models.CreateRecTaskRequest()
    req.EngineModelType = "16k_zh"
    req.ChannelNum = 1
    req.ResTextFormat = 2
    req.SourceType = 0  # URL 拉取数据
    req.Url = audio_url

    try:
        resp = client.CreateRecTask(req)
    except TencentCloudSDKException as e:
        raise RuntimeError(f"创建 ASR 任务(URL)失败: {e}") from e

    return resp.Data.TaskId


def describe_task_status(task_id: int) -> models.DescribeTaskStatusResponse:
    """查询识别任务状态。

    Args:
        task_id: CreateRecTask 返回的 TaskId。

    Returns:
        任务状态响应对象。
    """
    client = _get_client()
    req = models.DescribeTaskStatusRequest()
    req.TaskId = task_id

    try:
        return client.DescribeTaskStatus(req)
    except TencentCloudSDKException as e:
        raise RuntimeError(f"查询 ASR 任务状态失败: {e}") from e


def wait_for_result(task_id: int) -> str:
    """轮询等待识别任务完成，返回完整转写文本。

    Status 值说明：
      0 — waiting（排队中）
      1 — doing（识别中）
      2 — success（成功）
      3 — failed（失败）

    Args:
        task_id: 识别任务 ID。

    Returns:
        完整的转写文本（Result 字段）。
    """
    start = time.time()
    last_status = -1

    while True:
        elapsed = time.time() - start
        if elapsed > MAX_POLL_TIME:
            raise TimeoutError(f"ASR 任务 {task_id} 超时（超过 {MAX_POLL_TIME // 60} 分钟）")

        resp = describe_task_status(task_id)
        data = resp.Data
        status = data.Status

        if status != last_status:
            status_str = data.StatusStr or str(status)
            print(f"[ASR] Task {task_id}: {status_str} ({elapsed:.0f}s)")
            last_status = status

        if status == 2:
            return data.Result
        if status == 3:
            err_msg = data.ErrorMsg or "未知错误"
            raise RuntimeError(f"ASR 任务 {task_id} 识别失败: {err_msg}")

        time.sleep(POLL_INTERVAL)


def get_transcribed_text(audio_path: Path) -> str:
    """完整流程：读取音频文件 → 提交 ASR 任务（直传） → 等待结果 → 返回转写文本。

    Args:
        audio_path: 音频文件路径。

    Returns:
        语音转写文本。
    """
    audio_data = audio_path.read_bytes()
    task_id = create_rec_task(audio_data)
    return wait_for_result(task_id)


def get_transcribed_text_from_url(audio_url: str) -> str:
    """完整流程：通过 URL 提交 ASR 任务 → 等待结果 → 返回转写文本。

    无 5MB 大小限制，适用于大文件录音。
    需保证 URL 可被腾讯云 ASR 服务公网访问。

    Args:
        audio_url: 音频文件的公网可访问 URL。

    Returns:
        语音转写文本。
    """
    task_id = create_rec_task_from_url(audio_url)
    return wait_for_result(task_id)


def get_transcribed_text_via_proxy(audio_path: Path) -> str:
    """完整流程：上传文件到 tflink 中转 → URL 提交 ASR → 等待结果 → 返回转写文本。

    通过 tflink 匿名上传获取公网 URL，再使用腾讯云 ASR URL 拉取模式识别，
    绕过 ASR 直传 5MB 限制。支持最大 100MB 的音频文件。

    Args:
        audio_path: 音频文件路径。

    Returns:
        语音转写文本。
    """
    from meeting_agent.services.tflink_service import upload_to_tflink

    print(f"[tflink] 上传文件 {audio_path.name} 到 tflink...")
    audio_url = upload_to_tflink(audio_path)
    print(f"[tflink] 获取到下载链接: {audio_url}")

    task_id = create_rec_task_from_url(audio_url)
    return wait_for_result(task_id)
