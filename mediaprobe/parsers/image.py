"""静态图片头部解析：PNG / JPEG / GIF / WebP 尺寸。"""

from __future__ import annotations

from typing import Any, Dict

from ..utils import BinaryReader


def _empty() -> Dict[str, Any]:
    return {
        "streams": [], "container": {}, "duration_ms": None, "width": None,
        "height": None, "codec": "", "tags": {}, "findings": [],
    }


def parse_png(reader: BinaryReader) -> Dict[str, Any]:
    out = _empty()
    if reader.size < 24 or reader.at(0, 8) != b"\x89PNG\r\n\x1a\n":
        out["findings"].append(("E070", "error", "不是合法 PNG 文件", ""))
        return out
    if reader.at(12, 4) != b"IHDR":
        out["findings"].append(("E071", "error", "PNG 缺少 IHDR 块", ""))
        return out
    out["codec"] = "PNG"
    out["width"] = reader.u32be(16)
    out["height"] = reader.u32be(20)
    out["container"]["bit_depth"] = reader.u8(24)
    out["container"]["color_type"] = reader.u8(25)
    out["streams"].append({
        "index": 0, "kind": "video", "codec": "PNG", "codec_tag": "PNG",
        "width": out["width"], "height": out["height"],
    })
    return out


def parse_jpeg(reader: BinaryReader) -> Dict[str, Any]:
    out = _empty()
    if reader.size < 4 or reader.at(0, 3) != b"\xff\xd8\xff":
        out["findings"].append(("E072", "error", "不是合法 JPEG 文件", ""))
        return out
    sof_markers = {
        0xC0: "baseline", 0xC1: "extended", 0xC2: "progressive", 0xC3: "lossless",
        0xC5: "differential", 0xC6: "differential progressive", 0xC7: "differential lossless",
        0xC9: "arithmetic", 0xCA: "arithmetic progressive", 0xCB: "arithmetic lossless",
    }
    pos = 2
    window = min(reader.size, 2 << 20)  # 最多扫描 2MB
    while pos + 9 < window:
        if reader.at(pos, 1) != b"\xff":
            pos += 1
            continue
        marker = reader.u8(pos + 1)
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        if marker == 0xD9:
            break
        length = reader.u16be(pos + 2)
        if marker in sof_markers and length >= 6 and pos + 9 <= reader.size:
            out["codec"] = "JPEG/" + sof_markers[marker]
            out["height"] = reader.u16be(pos + 5)
            out["width"] = reader.u16be(pos + 7)
            out["container"]["components"] = reader.u8(pos + 9)
            out["container"]["progressive"] = marker in (0xC2, 0xCA)
            break
        pos += 2 + length
    if out["width"] is None:
        out["findings"].append(("E073", "error", "未找到 JPEG SOF 标记", ""))
    else:
        out["streams"].append({
            "index": 0, "kind": "video", "codec": out["codec"], "codec_tag": "JPEG",
            "width": out["width"], "height": out["height"],
        })
    return out


def parse_gif(reader: BinaryReader) -> Dict[str, Any]:
    out = _empty()
    if reader.size < 10 or reader.at(0, 6) not in (b"GIF87a", b"GIF89a"):
        out["findings"].append(("E074", "error", "不是合法 GIF 文件", ""))
        return out
    out["codec"] = "GIF"
    out["width"] = reader.u16le(6)
    out["height"] = reader.u16le(8)
    out["container"]["version"] = reader.at(0, 6).decode("ascii")
    out["container"]["global_color_table"] = bool(reader.u8(10) & 0x80)
    out["streams"].append({
        "index": 0, "kind": "video", "codec": "GIF", "codec_tag": "GIF",
        "width": out["width"], "height": out["height"],
    })
    return out


def parse_webp(reader: BinaryReader) -> Dict[str, Any]:
    out = _empty()
    if reader.size < 16 or reader.at(0, 4) != b"RIFF" or reader.at(8, 4) != b"WEBP":
        out["findings"].append(("E075", "error", "不是合法 RIFF/WebP 文件", ""))
        return out
    chunk = reader.fourcc(12)
    payload = 20
    if chunk == "VP8X" and payload + 10 <= reader.size:
        out["width"] = int.from_bytes(reader.at(payload + 4, 3), "little") + 1
        out["height"] = int.from_bytes(reader.at(payload + 7, 3), "little") + 1
        out["codec"] = "WebP/Extended"
        out["container"]["animation"] = bool(reader.u8(payload) & 0x02)
    elif chunk == "VP8 " and payload + 10 <= reader.size:
        out["width"] = reader.u16le(payload + 6) & 0x3FFF
        out["height"] = reader.u16le(payload + 8) & 0x3FFF
        out["codec"] = "WebP/Lossy"
    elif chunk == "VP8L" and payload + 5 <= reader.size:
        bits = int.from_bytes(reader.at(payload + 1, 4), "little")
        out["width"] = (bits & 0x3FFF) + 1
        out["height"] = ((bits >> 14) & 0x3FFF) + 1
        out["codec"] = "WebP/Lossless"
    else:
        out["findings"].append(("E076", "error", "未知 WebP 分块: " + chunk, ""))
        return out
    out["container"]["chunk"] = chunk.strip()
    out["streams"].append({
        "index": 0, "kind": "video", "codec": out["codec"], "codec_tag": chunk.strip(),
        "width": out["width"], "height": out["height"],
    })
    return out
