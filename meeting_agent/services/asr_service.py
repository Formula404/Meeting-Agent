"""腾讯云语音识别 ASR 服务 —— 录音文件识别"""

from __future__ import annotations

import base64
import json
import math
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

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

# ── 大文件自动分片 ──
MAX_CHUNK_DURATION = 7200  # 每片最长 2 小时（ASR 单任务约 3h 上限，留 buffer）
MAX_CHUNK_SIZE = 90 * 1024 * 1024  # 每片最大 90MB（tflink 单文件 100MB 上限，留 buffer）
CHUNK_OVERLAP = 30  # 相邻片之间重叠 30 秒，避免切分点丢词


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


# ═══════════════════════════════════════════════════════════════
# 大文件自动分片转写（超 100MB 或超 3h 录音）
# ═══════════════════════════════════════════════════════════════

def _get_audio_info(file_path: Path) -> dict:
    """通过 ffprobe 获取音频文件时长（秒）和大小（字节）。"""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration,size",
        "-of", "json",
        str(file_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        raise RuntimeError(
            "未找到 ffprobe/ffmpeg，请确保已安装 ffmpeg。\n"
            "  apt-get install ffmpeg   (Debian/Ubuntu)\n"
            "  brew install ffmpeg      (macOS)"
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe 分析音频文件失败: {e.stderr[:500] if e.stderr else str(e)}")

    info = json.loads(result.stdout)
    fmt = info.get("format", {})
    duration = float(fmt.get("duration", 0))
    size = int(fmt.get("size", 0))
    if duration <= 0:
        raise RuntimeError(f"无法获取音频文件时长 (ffprobe 返回 duration={duration}): {file_path}")
    return {"duration": duration, "size": size}


def _calculate_chunks(file_path: Path) -> int:
    """根据时长和大小双约束计算所需分片数。"""
    info = _get_audio_info(file_path)
    duration = info["duration"]
    file_size = info["size"]

    n_by_duration = max(1, math.ceil(duration / MAX_CHUNK_DURATION))
    n_by_size = max(1, math.ceil(file_size / MAX_CHUNK_SIZE))
    n = max(n_by_duration, n_by_size)

    if n > 1:
        print(f"[ASR] 文件 {file_path.name}: 时长 {duration:.0f}s / 大小 {file_size / 1024 / 1024:.0f}MB "
              f"→ 自动分 {n} 片处理")
    return n


def _split_audio_with_overlap(file_path: Path, num_chunks: int, output_dir: Path) -> list[Path]:
    """用 ffmpeg 将音频切分为 N 片，相邻片之间重叠 CHUNK_OVERLAP 秒。"""
    info = _get_audio_info(file_path)
    total_duration = info["duration"]
    chunk_duration = total_duration / num_chunks
    suffix = file_path.suffix

    chunk_paths = []
    for i in range(num_chunks):
        start = max(0, i * chunk_duration - (CHUNK_OVERLAP if i > 0 else 0))
        if i < num_chunks - 1:
            chunk_len = chunk_duration + CHUNK_OVERLAP
        else:
            chunk_len = total_duration - start

        output_path = output_dir / f"{file_path.stem}_chunk_{i:03d}{suffix}"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(file_path),
            "-t", str(chunk_len),
            "-c", "copy",
            str(output_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg 分片失败 (chunk {i}): {e.stderr[:500] if e.stderr else str(e)}")

        chunk_paths.append(output_path)
        print(f"[ASR]   分片 {i + 1}/{num_chunks}: {start:.0f}s → {start + chunk_len:.0f}s ({output_path.name})")

    return chunk_paths


def _merge_chunk_results(results: list[str]) -> str:
    """合并多片 ASR 结果，在文本层去重重叠部分。"""
    if not results:
        return ""
    if len(results) == 1:
        return results[0]

    merged = results[0]
    for i in range(1, len(results)):
        curr = results[i]
        tail = merged[-300:].strip()
        head = curr[:300].strip()

        # 从长到短匹配尾部与首部的公共部分（最小匹配 5 个字符避免误判）
        overlap_len = 0
        max_check = min(len(tail), len(head), 300)
        for ol in range(max_check, 4, -1):
            if tail[-ol:] == head[:ol]:
                overlap_len = ol
                break

        if overlap_len > 0:
            merged += curr[overlap_len:]
        else:
            merged += "\n" + curr

    return merged


def get_transcribed_text_via_proxy_chunked(audio_path: Path) -> str:
    """分片版转写：切分 → 逐片上传 tflink → 全部提交 ASR → 并行等待 → 合并。

    适用于超大型录音文件（>100MB 或 >3 小时）。

    Args:
        audio_path: 音频文件路径。

    Returns:
        合并后的完整语音转写文本。
    """
    from meeting_agent.services.tflink_service import upload_to_tflink

    num_chunks = _calculate_chunks(audio_path)
    if num_chunks <= 1:
        return get_transcribed_text_via_proxy(audio_path)

    with tempfile.TemporaryDirectory(prefix="asr_chunks_") as tmp_dir:
        work_dir = Path(tmp_dir)
        chunk_paths = _split_audio_with_overlap(audio_path, num_chunks, work_dir)

        # Phase 1: 串行上传 tflink → 提交 ASR，收集 TaskId
        task_ids: list[int] = []
        for chunk_path in chunk_paths:
            print(f"[ASR] 上传分片 {chunk_path.name} 到 tflink...")
            audio_url = upload_to_tflink(chunk_path)
            print(f"[ASR]   获取到链接，提交 ASR 任务...")
            task_id = create_rec_task_from_url(audio_url)
            task_ids.append(task_id)
            print(f"[ASR]   ASR TaskId: {task_id}")

        # Phase 2: 并行等待所有 ASR 任务完成
        print(f"[ASR] 等待 {len(task_ids)} 个 ASR 任务完成...")
        results: list[str | None] = [None] * len(task_ids)
        with ThreadPoolExecutor(max_workers=len(task_ids)) as pool:
            fut_map = {pool.submit(wait_for_result, tid): idx for idx, tid in enumerate(task_ids)}
            for future in as_completed(fut_map):
                idx = fut_map[future]
                results[idx] = future.result()

        # 确保所有结果到位
        if any(r is None for r in results):
            raise RuntimeError("部分 ASR 分片任务未返回结果")

    # Phase 3: 按序合并
    merged = _merge_chunk_results(results)  # type: ignore[arg-type]
    print(f"[ASR] 合并完成: {len(results)} 片 → {len(merged)} 字符")
    return merged


def transcribe_audio_file(audio_path: Path) -> str:
    """智能音频转写入口：自动判断是否需要分片，透明返回转写文本。

    - 小文件（≤90MB / ≤2h）：走原有单次 tflink→ASR 路径
    - 大文件（超限）：自动分片 → 逐片 tflink → 并行 ASR → 合并结果

    Args:
        audio_path: 音频文件路径。

    Returns:
        完整的语音转写文本。
    """
    try:
        num_chunks = _calculate_chunks(audio_path)
    except RuntimeError as e:
        # ffprobe 不可用时 fallback 到原有逻辑
        print(f"[ASR] 无法探测音频信息 ({e})，使用单次转写（如文件过大可能失败）")
        return get_transcribed_text_via_proxy(audio_path)

    if num_chunks <= 1:
        return get_transcribed_text_via_proxy(audio_path)

    return get_transcribed_text_via_proxy_chunked(audio_path)
