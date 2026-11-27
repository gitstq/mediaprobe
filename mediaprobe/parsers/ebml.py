"""EBML / Matroska / WebM 解析（只读顶层必要元素，低内存）。

通过递归遍历 Master Element 提取 Info / Tracks，支持未知长度（all-ones vint）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..utils import BinaryReader, clamp_int, read_vint, safe_div

# EBML Element ID
ID_EBML = 0x1A45DFA3
ID_DOCTYPE = 0x4282
ID_SEGMENT = 0x18538067
ID_INFO = 0x1549A966
ID_DURATION = 0x4489
ID_TIMECODE_SCALE = 0x2AD7B1
ID_TRACKS = 0x1654AE6B
ID_TRACK_ENTRY = 0xAE
ID_TRACK_NUMBER = 0xD7
ID_TRACK_TYPE = 0x83
ID_CODEC_ID = 0x86
ID_CODEC_NAME = 0x536E
ID_LANGUAGE = 0x22B59C
ID_VIDEO = 0xE0
ID_PIXEL_WIDTH = 0xB0
ID_PIXEL_HEIGHT = 0xBA
ID_AUDIO = 0xE1
ID_SAMPLING_FREQ = 0xB5
ID_CHANNELS = 0x9F
ID_BIT_DEPTH = 0x6264

MASTERS = {ID_EBML, ID_SEGMENT, ID_INFO, ID_TRACKS, ID_TRACK_ENTRY, ID_VIDEO, ID_AUDIO}

CODEC_NAMES = {
    "V_VP8": "VP8", "V_VP9": "VP9", "V_AV1": "AV1",
    "V_MPEG4/ISO/AVC": "H.264/AVC", "V_MPEGH/ISO/HEVC": "H.265/HEVC",
    "V_MPEG4/ISO/SP": "MPEG-4 Visual", "V_MS/VFW/FOURCC": "VFW Compat",
    "A_OPUS": "Opus", "A_VORBIS": "Vorbis", "A_AAC": "AAC",
    "A_PCM/INT/LIT": "PCM LE", "A_PCM/INT/BIG": "PCM BE",
    "A_FLAC": "FLAC", "A_MPEG/L3": "MP3",
    "S_TEXT/UTF8": "SRT", "S_TEXT/WEBVTT": "WebVTT",
}

MAX_ELEMENTS = 20000


class _Walker:
    """EBML 元素遍历器，限制元素数量与递归深度。"""

    def __init__(self, reader: BinaryReader, start: int, end: int):
        self.reader = reader
        self.start = start
        self.end = end
        self.count = 0

    def walk(self, start: Optional[int] = None, end: Optional[int] = None, depth: int = 0):
        if depth > 16:
            return
        pos = self.start if start is None else start
        limit = self.end if end is None else end
        data_cache: Dict[int, bytes] = {}

        while pos + 2 <= limit and self.count < MAX_ELEMENTS:
            head = self.reader.at(pos, min(32, limit - pos))
            try:
                eid, id_len = read_vint(head, 0, keep_marker=True)
                size, size_len = read_vint(head, id_len)
            except ValueError:
                return
            if size is None:  # 未知长度：延伸到父容器末尾
                size = limit - pos - id_len - size_len
            payload = pos + id_len + size_len
            if payload > limit or payload + size > limit:
                return
            self.count += 1
            yield eid, payload, payload + size

            if eid in MASTERS:
                yield from self.walk(payload, payload + size, depth + 1)
            pos = payload + size


def _as_float(reader: BinaryReader, start: int, end: int) -> Optional[float]:
    length = end - start
    if length == 4:
        import struct
        return struct.unpack(">f", reader.at(start, 4))[0]
    if length == 8:
        import struct
        return struct.unpack(">d", reader.at(start, 8))[0]
    return None


def _as_text(reader: BinaryReader, start: int, end: int) -> str:
    try:
        return reader.at(start, min(end - start, 256)).decode("utf-8", "replace").strip("\x00 ")
    except ValueError:
        return ""


def parse(reader: BinaryReader) -> Dict[str, Any]:
    """解析 EBML 文件。"""

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
    walker = _Walker(reader, 0, reader.size)
    elements = list(walker.walk())

    # DocType 区分 MKV / WebM
    doc_type = ""
    for eid, start, end in elements:
        if eid == ID_DOCTYPE:
            doc_type = _as_text(reader, start, end)
            break
    out["container"]["doc_type"] = doc_type
    out["fmt_override"] = "webm" if doc_type == "webm" else ("mkv" if doc_type == "matroska" else None)

    timecode_scale = 1000000  # 默认 1ms
    duration = None
    for eid, start, end in elements:
        if eid == ID_TIMECODE_SCALE:
            try:
                raw = reader.at(start, min(8, end - start))
                timecode_scale = int.from_bytes(raw, "big")
            except ValueError:
                pass
        elif eid == ID_DURATION:
            duration = _as_float(reader, start, end)

    if duration is not None and timecode_scale:
        out["duration_ms"] = clamp_int(safe_div(duration * timecode_scale, 1000000000.0))

    # Tracks
    track_entries = [(s, e) for eid, s, e in elements if eid == ID_TRACK_ENTRY]
    for idx, (tstart, tend) in enumerate(track_entries[:64]):
        within = [(eid, s, e) for eid, s, e in elements if tstart < s < tend]
        track_type = 0
        codec_id = ""
        lang = ""
        for eid, s, e in within:
            if eid == ID_TRACK_TYPE and e - s <= 4:
                track_type = int.from_bytes(reader.at(s, e - s), "big")
            elif eid == ID_CODEC_ID:
                codec_id = _as_text(reader, s, e)
            elif eid == ID_LANGUAGE:
                lang = _as_text(reader, s, e)
        kind = {1: "video", 2: "audio", 17: "subtitle"}.get(track_type, "unknown")
        info: Dict[str, Any] = {
            "index": idx,
            "kind": kind,
            "codec": CODEC_NAMES.get(codec_id, codec_id),
            "codec_tag": codec_id,
            "language": lang,
        }
        # Video / Audio 子元素的范围
        for sub_id, dim_w, dim_h in ((ID_VIDEO, ID_PIXEL_WIDTH, ID_PIXEL_HEIGHT),
                                     (ID_AUDIO, ID_SAMPLING_FREQ, ID_CHANNELS)):
            for seid, ss, se in within:
                if seid != sub_id:
                    continue
                sub_children = [(eid, s, e) for eid, s, e in elements if ss < s < se]
                for ceid, cs, ce in sub_children:
                    if ceid == dim_w and ce - cs <= 8:
                        info["width"] = int.from_bytes(reader.at(cs, ce - cs), "big")
                        if kind == "video" and out["width"] is None:
                            out["width"] = info["width"]
                    elif ceid == dim_h and ce - cs <= 8:
                        info["height"] = int.from_bytes(reader.at(cs, ce - cs), "big")
                        if kind == "video" and out["height"] is None:
                            out["height"] = info["height"]
                    elif ceid == ID_SAMPLING_FREQ and ce - cs <= 8:
                        value = int.from_bytes(reader.at(cs, ce - cs), "big")
                        info["sample_rate"] = int(float(value))
                        if out["sample_rate"] is None:
                            out["sample_rate"] = info["sample_rate"]
                    elif ceid == ID_CHANNELS and ce - cs <= 4:
                        info["channels"] = int.from_bytes(reader.at(cs, ce - cs), "big")
                        if out["channels"] is None:
                            out["channels"] = info["channels"]
                    elif ceid == ID_BIT_DEPTH and ce - cs <= 4:
                        info["bit_depth"] = int.from_bytes(reader.at(cs, ce - cs), "big")
        out["streams"].append(info)

    if out["streams"]:
        primary = next((s for s in out["streams"] if s["kind"] != "audio"), out["streams"][0])
        out["codec"] = primary.get("codec", "")

    if out["duration_ms"]:
        bitrate = safe_div(reader.size * 8 * 1000, float(out["duration_ms"]))
        if bitrate:
            out["bitrate_bps"] = int(bitrate)

    out["container"]["element_count"] = walker.count
    return out
