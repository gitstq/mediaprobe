"""MP3 / ID3v2 / ID3v1 与 MPEG 音频帧头解析。"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ..utils import BinaryReader, clamp_int, safe_div, syncsafe

# ID3v2 文本帧 ID → 友好键
TEXT_FRAMES = {
    "TIT2": "title", "TPE1": "artist", "TALB": "album", "TPE2": "album_artist",
    "TDRC": "year", "TYER": "year", "TCON": "genre", "TRCK": "track",
    "TPOS": "disc", "TCOM": "composer", "TCOP": "copyright", "TENC": "encoder",
}

# MPEG Version/Layer → bitrate 表索引
BITRATES = {
    (3, 3): [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0],  # MPEG1 L3
    (3, 2): [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, 0],  # MPEG1 L2
    (3, 1): [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, 0],  # MPEG1 L1
    (2, 3): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],  # MPEG2 L3
    (2, 2): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],  # MPEG2 L2
}
SAMPLE_RATES = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}


def _decode_text(raw: bytes) -> str:
    """按 ID3v2 文本编码解析，支持 UTF-8 / UTF-16 / Latin-1。"""

    if not raw:
        return ""
    enc = raw[0]
    body = raw[1:]
    try:
        if enc == 0:
            return body.decode("latin-1").strip("\x00 ")
        if enc == 1:
            if body.startswith(b"\xff\xfe"):
                return body[2:].decode("utf-16-le", "replace").strip("\x00 ")
            if body.startswith(b"\xfe\xff"):
                return body[2:].decode("utf-16-be", "replace").strip("\x00 ")
            return body.decode("utf-16", "replace").strip("\x00 ")
        if enc == 2:
            return body.decode("utf-16-be", "replace").strip("\x00 ")
        if enc == 3:
            return body.decode("utf-8", "replace").strip("\x00 ")
    except UnicodeDecodeError:
        return ""
    return ""


def _parse_id3v2(reader: BinaryReader) -> Tuple[Dict[str, str], int, Dict[str, Any]]:
    """解析 ID3v2 标签，返回 (tags, 标签总字节数, 元信息)。"""

    tags: Dict[str, str] = {}
    meta: Dict[str, Any] = {}
    if reader.size < 10 or reader.at(0, 3) != b"ID3":
        return tags, 0, meta
    try:
        ver = reader.u8(3)
        flags = reader.u8(5)
        tag_size = syncsafe(reader, 6)
    except ValueError:
        return tags, 0, meta
    if tag_size <= 0 or tag_size > reader.size:
        return tags, 0, meta
    meta["id3v2_version"] = "2.%d.%d" % (ver, reader.u8(4))
    meta["id3v2_unsync"] = bool(flags & 0x80)
    meta["id3v2_extended"] = bool(flags & 0x40)
    meta["id3v2_footer"] = bool(flags & 0x10)

    pos = 10
    end = min(10 + tag_size, reader.size)
    if flags & 0x40:  # extended header: size 为 syncsafe
        try:
            ext_size = syncsafe(reader, pos)
            pos += ext_size + 4
        except ValueError:
            return tags, 10 + tag_size, meta

    while pos + 10 <= end:
        try:
            frame_id = reader.fourcc(pos)
            if frame_id.strip(".") == "" or frame_id[0] == "\x00":
                break
            if ver == 2:  # ID3v2.2: 3 字符 ID + 3 字节长度
                fid = frame_id[:3]
                frame_size = int.from_bytes(reader.at(pos + 3, 3), "big")
                header_len = 6
            else:
                fid = frame_id
                frame_size = syncsafe(reader, pos + 4) if ver == 4 else reader.u32be(pos + 4)
                header_len = 10
        except ValueError:
            break
        if frame_size <= 0 or pos + header_len + frame_size > end:
            break
        if fid.startswith("T") and fid != "XXX":
            try:
                content = _decode_text(reader.at(pos + header_len, frame_size))
                key = TEXT_FRAMES.get(fid, fid.lower())
                if content and key not in tags:
                    tags[key] = content
            except ValueError:
                pass
        pos += header_len + frame_size
    return tags, 10 + tag_size, meta


def _parse_id3v1(reader: BinaryReader) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """解析文件尾 128 字节 ID3v1 标签。"""

    tags: Dict[str, str] = {}
    meta: Dict[str, Any] = {}
    if reader.size < 128:
        return tags, meta
    try:
        tail = reader.at(reader.size - 128, 128)
    except ValueError:
        return tags, meta
    if tail[:3] != b"TAG":
        return tags, meta
    meta["id3v1"] = True
    fields = [
        ("title", tail[3:33]), ("artist", tail[33:63]),
        ("album", tail[63:93]), ("year", tail[93:97]),
    ]
    for key, raw in fields:
        value = raw.decode("latin-1", "replace").strip("\x00 ").strip()
        if value:
            tags[key] = value
    comment = tail[97:127]
    if comment[0:2] == b"\x00\x00":  # ID3v1.1
        meta["id3v1_track"] = comment[2]
        meta["id3v1_comment"] = comment[3:].decode("latin-1", "replace").strip("\x00 ")
    else:
        meta["id3v1_comment"] = comment.decode("latin-1", "replace").strip("\x00 ")
    return tags, meta


def _find_mpeg_frame(reader: BinaryReader, start: int, window: int = 262144) -> Optional[Dict[str, Any]]:
    """在前 window 字节内查找首个合法 MPEG 音频帧头。"""

    end = min(reader.size, start + window)
    if end - start < 4:
        return None
    data = reader.at(start, end - start)
    for i in range(len(data) - 3):
        b0, b1, b2, b3 = data[i], data[i + 1], data[i + 2], data[i + 3]
        if b0 != 0xFF or (b1 & 0xE0) != 0xE0:
            continue
        version_bits = (b1 >> 3) & 0x03
        layer_bits = (b1 >> 1) & 0x03
        if version_bits == 1 or layer_bits == 0:
            continue  # 保留值
        version = {3: 3, 2: 2, 0: 0}[version_bits]
        layer = 4 - layer_bits
        br_index = (b2 >> 4) & 0x0F
        sr_index = (b2 >> 2) & 0x03
        if br_index in (0, 15) or sr_index == 3:
            continue
        rates = BITRATES.get((version, layer))
        if not rates:
            continue
        bitrate_kbps = rates[br_index]
        sample_rate = SAMPLE_RATES.get(version, [0, 0, 0])[sr_index]
        if not bitrate_kbps or not sample_rate:
            continue
        channel_mode = (b3 >> 6) & 0x03
        channels = 1 if channel_mode == 3 else 2
        return {
            "mpeg_version": {3: "1", 2: "2", 0: "2.5"}[version],
            "layer": "L%d" % layer,
            "bitrate_kbps": bitrate_kbps,
            "sample_rate": sample_rate,
            "channels": channels,
            "channel_mode": ["stereo", "joint_stereo", "dual_channel", "mono"][channel_mode],
            "frame_offset": start + i,
        }
    return None


def parse(reader: BinaryReader) -> Dict[str, Any]:
    """解析 MP3 文件。"""

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
    tags, v2size, meta = _parse_id3v2(reader)
    v1tags, v1meta = _parse_id3v1(reader)
    for key, value in v1tags.items():
        if key not in tags:
            tags[key] = value
    if v2tags_conflicts := [k for k in tags if k in v1tags and tags[k] != v1tags[k]]:
        out["findings"].append((
            "W020", "warn", "ID3v2 与 ID3v1 标签内容冲突: " + ", ".join(sorted(v2tags_conflicts)),
            "播放器通常优先使用 ID3v2；建议统一两者",
        ))
    out["tags"] = tags
    out["container"].update(meta)
    out["container"].update(v1meta)
    out["container"]["id3v2_size"] = v2size

    frame = _find_mpeg_frame(reader, v2size)
    if frame:
        out["container"]["mpeg"] = {
            k: frame[k] for k in ("mpeg_version", "layer", "bitrate_kbps", "channel_mode")
        }
        out["codec"] = "MP3" if frame["layer"] == "L3" else "MPEG Layer " + frame["layer"][1:]
        out["sample_rate"] = frame["sample_rate"]
        out["channels"] = frame["channels"]
        audio_bytes = reader.size - v2size - (128 if v1meta.get("id3v1") else 0)
        if audio_bytes > 0:
            seconds = safe_div(audio_bytes * 8, frame["bitrate_kbps"] * 1000.0)
            out["duration_ms"] = clamp_int(seconds)
            out["bitrate_bps"] = frame["bitrate_kbps"] * 1000
        out["streams"].append({
            "index": 0, "kind": "audio", "codec": out["codec"], "codec_tag": frame["layer"],
            "sample_rate": frame["sample_rate"], "channels": frame["channels"],
            "bitrate_bps": frame["bitrate_kbps"] * 1000,
        })
    else:
        out["findings"].append((
            "E021", "error", "未找到合法 MPEG 音频帧头", "文件可能不是 MP3 或已损坏",
        ))
    return out
