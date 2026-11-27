"""RIFF/WAVE 解析器：fmt 与 data chunk。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..utils import BinaryReader, clamp_int, safe_div

WAVE_FORMATS = {
    1: "PCM", 3: "IEEE Float", 6: "A-law", 7: "μ-law",
    0xFFFE: "WAVE_FORMAT_EXTENSIBLE",
}


def parse(reader: BinaryReader) -> Dict[str, Any]:
    """解析 WAVE 文件。"""

    out: Dict[str, Any] = {
        "streams": [], "container": {}, "duration_ms": None, "width": None,
        "height": None, "codec": "", "tags": {}, "findings": [],
    }
    if reader.size < 12 or reader.at(0, 4) != b"RIFF" or reader.at(8, 4) != b"WAVE":
        out["findings"].append(("E030", "error", "不是合法 RIFF/WAVE 文件", ""))
        return out

    declared = reader.u32le(4)
    if declared + 8 > reader.size:
        out["findings"].append((
            "W031", "warn", "RIFF 声明长度 %d 超过实际文件大小 %d" % (declared + 8, reader.size),
            "文件可能被截断",
        ))
    out["container"]["riff_size"] = declared

    pos = 12
    fmt: Optional[Dict[str, Any]] = None
    data_size = None
    chunks = []
    while pos + 8 <= reader.size:
        try:
            cid = reader.fourcc(pos)
            csize = reader.u32le(pos + 4)
        except ValueError:
            break
        chunks.append(cid)
        payload = pos + 8
        if cid == "fmt " and csize >= 16 and payload + 16 <= reader.size:
            audio_format = reader.u16le(payload)
            channels = reader.u16le(payload + 2)
            sample_rate = reader.u32le(payload + 4)
            byte_rate = reader.u32le(payload + 8)
            bits = reader.u16le(payload + 14)
            fmt = {
                "audio_format": audio_format, "channels": channels,
                "sample_rate": sample_rate, "byte_rate": byte_rate,
                "bits_per_sample": bits,
            }
        elif cid == "data":
            data_size = csize
        pos = payload + csize + (csize & 1)  # 字对齐

    out["container"]["chunks"] = chunks[:32]
    if fmt:
        out["codec"] = WAVE_FORMATS.get(fmt["audio_format"], "Unknown(0x%04x)" % fmt["audio_format"])
        out["sample_rate"] = fmt["sample_rate"]
        out["channels"] = fmt["channels"]
        out["container"]["bits_per_sample"] = fmt["bits_per_sample"]
        if data_size is not None and fmt["byte_rate"]:
            out["duration_ms"] = clamp_int(safe_div(float(data_size), float(fmt["byte_rate"])))
        info = {
            "index": 0, "kind": "audio", "codec": out["codec"],
            "codec_tag": "0x%04x" % fmt["audio_format"],
            "sample_rate": fmt["sample_rate"], "channels": fmt["channels"],
            "bit_depth": fmt["bits_per_sample"],
        }
        if out["duration_ms"] is not None:
            info["duration_ms"] = out["duration_ms"]
        out["streams"].append(info)
    else:
        out["findings"].append(("E032", "error", "缺少 fmt 块", ""))
    if data_size is None:
        out["findings"].append(("E033", "error", "缺少 data 块", ""))
    elif pos < reader.size and data_size + 8 + 12 > reader.size:
        out["findings"].append(("W034", "warn", "data 块可能被截断", ""))
    return out
