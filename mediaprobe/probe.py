"""探查入口：格式探测 → 解析 → 审计 → 组装 Manifest。"""

from __future__ import annotations

import io
import os
import tempfile
from typing import Any, Dict, Optional

from .audit import audit_manifest
from .detect import detect, mime_for
from .models import Manifest, StreamInfo
from .parsers import PARSERS
from .utils import BinaryReader, sha256_file
from . import __version__


def _build_manifest(
    path: str,
    reader: BinaryReader,
    parsed: Dict[str, Any],
    fmt: str,
    digest: str,
) -> Manifest:
    """把解析结果转换为 Manifest 数据模型。"""

    override = parsed.get("fmt_override")
    final_fmt = override if override else fmt
    findings = audit_manifest(reader, parsed)

    streams = []
    for raw in parsed.get("streams", []):
        info = dict(raw)
        info.pop("fmt_override", None)
        streams.append(StreamInfo(**info))

    return Manifest(
        path=path,
        size_bytes=reader.size,
        sha256=digest,
        fmt=final_fmt,
        mime=mime_for(final_fmt),
        duration_ms=parsed.get("duration_ms"),
        width=parsed.get("width"),
        height=parsed.get("height"),
        bitrate_bps=parsed.get("bitrate_bps"),
        sample_rate=parsed.get("sample_rate"),
        channels=parsed.get("channels"),
        codec=parsed.get("codec", ""),
        tags=parsed.get("tags", {}),
        streams=streams,
        findings=findings,
        container=parsed.get("container", {}),
        tool={"name": "mediaprobe", "version": __version__},
    )


def probe_file(path: str, compute_hash: bool = True) -> Manifest:
    """探查一个媒体文件，返回 Manifest。

    Args:
        path: 文件路径
        compute_hash: 是否计算 SHA-256（大文件可关闭以提速）

    Raises:
        FileNotFoundError: 文件不存在
        OSError: 无法读取文件
    """

    if not os.path.isfile(path):
        raise FileNotFoundError("文件不存在或不是普通文件: %s" % path)
    digest = sha256_file(path) if compute_hash else ""
    with BinaryReader.from_path(path) as reader:
        fmt = detect(reader)
        parser = PARSERS.get(fmt)
        parsed: Dict[str, Any] = parser(reader) if parser else {
            "streams": [], "container": {}, "duration_ms": None,
            "width": None, "height": None, "codec": "", "tags": {}, "findings": [],
        }
        parsed["fmt"] = fmt
        return _build_manifest(path, reader, parsed, fmt, digest)


def probe_bytes(data: bytes, name: str = "<bytes>", compute_hash: bool = True) -> Manifest:
    """探查内存中的字节数据（便于测试与库集成）。"""

    import hashlib
    digest = hashlib.sha256(data).hexdigest() if compute_hash else ""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        return _probe_temp(tmp_path, name, digest)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _probe_temp(tmp_path: str, display_name: str, digest: str) -> Manifest:
    """probe_bytes 的内部实现。"""

    with BinaryReader.from_path(tmp_path) as reader:
        fmt = detect(reader)
        parser = PARSERS.get(fmt)
        parsed: Dict[str, Any] = parser(reader) if parser else {
            "streams": [], "container": {}, "duration_ms": None,
            "width": None, "height": None, "codec": "", "tags": {}, "findings": [],
        }
        parsed["fmt"] = fmt
        manifest = _build_manifest(tmp_path, reader, parsed, fmt, digest)
        manifest.path = display_name
        return manifest
