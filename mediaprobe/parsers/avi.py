"""AVI (RIFF) 解析器：avih 主头。"""

from __future__ import annotations

from typing import Any, Dict

from ..utils import BinaryReader, clamp_int


def parse(reader: BinaryReader) -> Dict[str, Any]:
    """解析 AVI 文件的基础信息。"""

    out: Dict[str, Any] = {
        "streams": [], "container": {}, "duration_ms": None, "width": None,
        "height": None, "codec": "", "tags": {}, "findings": [],
    }
    if reader.size < 12 or reader.at(0, 4) != b"RIFF" or reader.at(8, 4) != b"AVI ":
        out["findings"].append(("E040", "error", "不是合法 RIFF/AVI 文件", ""))
        return out

    declared = reader.u32le(4)
    out["container"]["riff_size"] = declared
    if declared + 8 > reader.size:
        out["findings"].append((
            "W041", "warn", "RIFF 声明长度 %d 超过实际文件大小 %d" % (declared + 8, reader.size),
            "文件可能被截断",
        ))

    pos = 12
    chunks = []
    while pos + 8 <= reader.size:
        try:
            cid = reader.fourcc(pos)
            csize = reader.u32le(pos + 4)
        except ValueError:
            break
        chunks.append(cid)
        payload = pos + 8
        if cid == "avih" and csize >= 56 and payload + 56 <= reader.size:
            usec_per_frame = reader.u32le(payload)
            max_bytes = reader.u32le(payload + 4)
            total_frames = reader.u32le(payload + 16)
            width = reader.u32le(payload + 32)
            height = reader.u32le(payload + 36)
            out["width"] = width or None
            out["height"] = height or None
            if total_frames:
                out["duration_ms"] = clamp_int(usec_per_frame * total_frames / 1000000.0)
            out["container"]["total_frames"] = total_frames
            out["container"]["max_bytes_per_frame"] = max_bytes
            if out["duration_ms"]:
                out["bitrate_bps"] = int(reader.size * 8 * 1000 / out["duration_ms"])
        pos = payload + csize + (csize & 1)
        if len(chunks) > 64:
            break
    out["container"]["chunks"] = chunks[:32]
    return out
