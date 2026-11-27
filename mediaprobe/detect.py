"""基于魔数的格式探测（无扩展名依赖）。"""

from __future__ import annotations

from .utils import BinaryReader

# (format, mime) 映射表
MIME = {
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "m4a": "audio/mp4",
    "mkv": "video/x-matroska",
    "webm": "video/webm",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "avi": "video/x-msvideo",
    "aiff": "audio/aiff",
    "flac": "audio/flac",
    "png": "image/png",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "unknown": "application/octet-stream",
}


def detect(reader: BinaryReader) -> str:
    """探测容器格式。返回 formats.MIME 中的键之一。"""

    if reader.size < 4:
        return "unknown"
    head = reader.at(0, min(64, reader.size))

    # ISO BMFF: ftyp box
    if head[4:8] == b"ftyp" and reader.size >= 12:
        brand = head[8:12]
        if brand in (b"qt  ", b"qt  "):
            return "mov"
        if brand in (b"M4A ", b"M4B "):
            return "m4a"
        return "mp4"

    # EBML (Matroska / WebM)
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "ebml"  # 由 ebml 解析器进一步区分 mkv/webm

    # ID3v2 标签
    if head[:3] == b"ID3":
        return "mp3"

    # MPEG 音频帧同步 (11 bit all ones)
    if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
        # 排除 JPEG (FF D8) 与 FF F7 等
        if not (head[1] == 0xD8 or head[1] == 0xF7):
            return "mp3"

    # RIFF 家族
    if head[:4] == b"RIFF" and reader.size >= 12:
        form = head[8:12]
        if form == b"WAVE":
            return "wav"
        if form == b"AVI ":
            return "avi"
        if form == b"WEBP":
            return "webp"

    # AIFF / AIFC
    if head[:4] == b"FORM" and reader.size >= 12 and head[8:12] in (b"AIFF", b"AIFC"):
        return "aiff"

    # FLAC
    if head[:4] == b"fLaC":
        return "flac"

    # 图片
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if head[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"

    return "unknown"


def mime_for(fmt: str) -> str:
    return MIME.get(fmt, MIME["unknown"])
