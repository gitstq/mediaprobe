"""ISO Base Media File Format (MP4 / MOV / M4A) 解析。

仅解析 we need 的 box：ftyp / moov / mvhd / trak / tkhd / mdhd / hdlr / stsd。
支持 32 位与 64 位 box 长度、size==0，含深度与数量上限防止恶意文件导致卡死。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..utils import BinaryReader, clamp_int, iter_boxes, safe_div

# stsd sample entry 四字符码 → (kind, 友好名)
SAMPLE_ENTRY = {
    "avc1": ("video", "H.264/AVC"),
    "avc3": ("video", "H.264/AVC"),
    "hev1": ("video", "H.265/HEVC"),
    "hvc1": ("video", "H.265/HEVC"),
    "av01": ("video", "AV1"),
    "vp09": ("video", "VP9"),
    "vp8 ": ("video", "VP8"),
    "mp4v": ("video", "MPEG-4 Visual"),
    "jpeg": ("video", "MJPEG"),
    "png ": ("video", "PNG"),
    "hdlr": ("video", "QuickTime Animation"),
    "mp4a": ("audio", "AAC"),
    "ac-3": ("audio", "AC-3"),
    "ec-3": ("audio", "E-AC-3"),
    "alac": ("audio", "ALAC"),
    "Opus": ("audio", "Opus"),
    "flac": ("audio", "FLAC"),
    "sowt": ("audio", "PCM LE"),
    "twos": ("audio", "PCM BE"),
    "tx3g": ("subtitle", "3GPP Timed Text"),
    "wvtt": ("subtitle", "WebVTT"),
    "stpp": ("subtitle", "TTML"),
}

MAX_TRACKS = 256


def _find_box(reader: BinaryReader, start: int, end: int, target: str):
    """在指定区间内按深度优先查找首个目标 box。"""

    for box_type, payload, box_end, _ in iter_boxes(reader, start, end):
        if box_type == target:
            return payload, box_end
        if box_type in ("moov", "trak", "mdia", "minf", "stbl", "edts", "udta", "meta"):
            found = _find_box(reader, payload, box_end, target)
            if found:
                return found
    return None


def _parse_mvhd(reader: BinaryReader, start: int, end: int) -> Dict[str, Any]:
    """解析 movie header：timescale + duration。"""

    result: Dict[str, Any] = {}
    if end - start < 4:
        return result
    version = reader.u8(start)
    try:
        if version == 1 and end - start >= 32:
            timescale = reader.u32be(start + 20)
            duration = reader.u64be(start + 24)
        elif end - start >= 20:
            timescale = reader.u32be(start + 12)
            duration = reader.u32be(start + 16)
        else:
            return result
    except ValueError:
        return result
    if timescale:
        result["timescale"] = timescale
        result["duration_ms"] = clamp_int(safe_div(duration, timescale))
        result["raw_duration"] = duration
    return result


def _parse_tkhd(reader: BinaryReader, start: int, end: int) -> Dict[str, Any]:
    """解析 track header：16.16 定点宽高。"""

    result: Dict[str, Any] = {}
    if end - start < 4:
        return result
    version = reader.u8(start)
    width_off = start + (88 if version == 1 else 76)
    height_off = width_off + 4
    try:
        if height_off + 4 <= end:
            width = reader.u32be(width_off) / 65536.0
            height = reader.u32be(height_off) / 65536.0
            if width > 0 and height > 0:
                result["width"] = int(round(width))
                result["height"] = int(round(height))
    except ValueError:
        pass
    return result


def _parse_mdhd(reader: BinaryReader, start: int, end: int) -> Dict[str, Any]:
    """解析 media header：track timescale + duration。"""

    result: Dict[str, Any] = {}
    if end - start < 4:
        return result
    version = reader.u8(start)
    try:
        if version == 1 and end - start >= 28:
            timescale = reader.u32be(start + 20)
            duration = reader.u64be(start + 24)
        elif end - start >= 20:
            timescale = reader.u32be(start + 12)
            duration = reader.u32be(start + 16)
        else:
            return result
    except ValueError:
        return result
    if timescale:
        result["timescale"] = timescale
        result["duration_ms"] = clamp_int(safe_div(duration, timescale))
    return result


def _parse_hdlr(reader: BinaryReader, start: int, end: int) -> str:
    """解析 handler type（vide/soun/subt）。"""

    if end - start < 12:
        return ""
    try:
        return reader.fourcc(start + 8)
    except ValueError:
        return ""


def _parse_stsd(reader: BinaryReader, start: int, end: int) -> List[Dict[str, str]]:
    """解析 sample description 中的编码 FourCC。"""

    entries: List[Dict[str, str]] = []
    if end - start < 8:
        return entries
    try:
        count = reader.u32be(start + 4)
    except ValueError:
        return entries
    pos = start + 8
    for _ in range(min(count, 32)):
        if pos + 8 > end:
            break
        try:
            size = reader.u32be(pos)
            tag = reader.fourcc(pos + 4)
        except ValueError:
            break
        if size < 8:
            break
        entries.append({"tag": tag})
        pos += size
    return entries


def parse(reader: BinaryReader) -> Dict[str, Any]:
    """解析 ISO BMFF 文件，返回统一字段字典。"""

    out: Dict[str, Any] = {
        "streams": [],
        "container": {},
        "duration_ms": None,
        "width": None,
        "height": None,
        "codec": "",
        "tags": {},
        "findings": [],
    }
    top = list(iter_boxes(reader, 0, reader.size))
    types = [b[0] for b in top]

    ftyp = _find_box(reader, 0, reader.size, "ftyp")
    if ftyp:
        out["container"]["major_brand"] = reader.fourcc(ftyp[0])
        out["container"]["compatible_brands"] = [
            reader.fourcc(ftyp[0] + i) for i in range(8, ftyp[1] - ftyp[0] - 3, 4)
            if i + 4 <= ftyp[1] - ftyp[0]
        ]

    moov = next((b for b in top if b[0] == "moov"), None)
    mdat = next((b for b in top if b[0] == "mdat"), None)
    if moov:
        out["container"]["moov_offset"] = moov[1] - 8
        if mdat and moov[1] > mdat[1]:
            out["findings"].append(
                ("W010", "warn", "moov 位于 mdat 之后，非 faststart 布局",
                 "使用 -movflags +faststart 优化在线播放")
            )
    else:
        out["findings"].append(
            ("E011", "error", "缺少 moov box，文件结构不完整", "")
        )

    if moov:
        mvhd = _find_box(reader, moov[1], moov[2], "mvhd")
        if mvhd:
            header = _parse_mvhd(reader, mvhd[0], mvhd[1])
            out["duration_ms"] = header.get("duration_ms")
            if "timescale" in header:
                out["container"]["timescale"] = header["timescale"]

        stream_index = 0
        for box_type, payload, box_end, _ in iter_boxes(reader, moov[1], moov[2]):
            if box_type != "trak":
                continue
            if stream_index >= MAX_TRACKS:
                break
            handler = ""
            hdlr = _find_box(reader, payload, box_end, "hdlr")
            if hdlr:
                handler = _parse_hdlr(reader, hdlr[0], hdlr[1])
            tkhd = _find_box(reader, payload, box_end, "tkhd")
            mdhd = _find_box(reader, payload, box_end, "mdhd")
            stsd = _find_box(reader, payload, box_end, "stsd")
            entries = _parse_stsd(reader, stsd[0], stsd[1]) if stsd else []

            kind = {"vide": "video", "soun": "audio", "subt": "subtitle",
                    "text": "subtitle"}.get(handler, "unknown")
            codec_tag = entries[0]["tag"] if entries else ""
            codec_name = SAMPLE_ENTRY.get(codec_tag, (None, codec_tag.strip()))[1] if codec_tag else ""

            info: Dict[str, Any] = {
                "index": stream_index,
                "kind": kind,
                "codec": codec_name,
                "codec_tag": codec_tag,
            }
            if tkhd:
                dims = _parse_tkhd(reader, tkhd[0], tkhd[1])
                if dims:
                    info.update(dims)
                    if kind == "video" and out["width"] is None:
                        out["width"] = dims.get("width")
                        out["height"] = dims.get("height")
            if mdhd:
                media = _parse_mdhd(reader, mdhd[0], mdhd[1])
                if media.get("duration_ms") is not None:
                    info["duration_ms"] = media["duration_ms"]
                    if out["duration_ms"] is None:
                        out["duration_ms"] = media["duration_ms"]
            out["streams"].append(info)
            stream_index += 1

    if out["streams"]:
        primary = next((s for s in out["streams"] if s["kind"] != "audio"), out["streams"][0])
        out["codec"] = primary.get("codec", "")

    if out["duration_ms"]:
        bitrate = safe_div(reader.size * 8 * 1000, float(out["duration_ms"]))
        if bitrate:
            out["bitrate_bps"] = int(bitrate)

    out["container"]["box_count"] = len(types)
    out["container"]["top_level_boxes"] = types[:32]
    return out
