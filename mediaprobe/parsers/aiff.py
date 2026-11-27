"""AIFF / AIFC 解析器：COMM 块（80 位扩展精度采样率）。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..utils import BinaryReader, clamp_int, safe_div


def _extended80(raw: bytes) -> Optional[float]:
    """解码 IEEE 754 80 位扩展精度浮点数（AIFF 采样率）。"""

    if len(raw) < 10:
        return None
    exponent = int.from_bytes(raw[:2], "big") & 0x7FFF
    mantissa = int.from_bytes(raw[2:10], "big")
    if exponent == 0 or exponent == 0x7FFF:
        return None
    try:
        return (mantissa / float(1 << 63)) * (2 ** (exponent - 16383))
    except OverflowError:
        return None


def parse(reader: BinaryReader) -> Dict[str, Any]:
    """解析 AIFF 文件。"""

    out: Dict[str, Any] = {
        "streams": [], "container": {}, "duration_ms": None, "width": None,
        "height": None, "codec": "", "tags": {}, "findings": [],
    }
    if reader.size < 12 or reader.at(0, 4) != b"FORM" or reader.at(8, 4) not in (b"AIFF", b"AIFC"):
        out["findings"].append(("E050", "error", "不是合法 FORM/AIFF 文件", ""))
        return out

    is_aifc = reader.at(8, 4) == b"AIFC"
    out["container"]["form"] = "AIFC" if is_aifc else "AIFF"
    pos = 12
    while pos + 8 <= reader.size:
        try:
            cid = reader.fourcc(pos)
            csize = reader.u32be(pos + 4)
        except ValueError:
            break
        payload = pos + 8
        if cid == "COMM" and csize >= 18 and payload + 18 <= reader.size:
            channels = reader.u16be(payload)
            frames = reader.u32be(payload + 2)
            bits = reader.u16be(payload + 6)
            rate = _extended80(reader.at(payload + 8, 10))
            compression = ""
            if is_aifc and csize >= 22:
                compression = reader.fourcc(payload + 18)
            codec = "AIFC/" + compression.strip() if compression else ("PCM" if not is_aifc else "AIFC")
            out["codec"] = codec
            out["sample_rate"] = int(rate) if rate else None
            out["channels"] = channels
            out["container"]["bits_per_sample"] = bits
            out["container"]["sample_frames"] = frames
            if rate:
                out["duration_ms"] = clamp_int(safe_div(float(frames), rate))
            out["streams"].append({
                "index": 0, "kind": "audio", "codec": codec,
                "codec_tag": compression.strip() if compression else "NONE",
                "sample_rate": out["sample_rate"], "channels": channels,
                "bit_depth": bits,
            })
            break
        pos = payload + csize + (csize & 1)
    return out
