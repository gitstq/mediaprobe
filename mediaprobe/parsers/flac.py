"""FLAC 解析器：STREAMINFO 元数据块。"""

from __future__ import annotations

from typing import Any, Dict

from ..utils import BinaryReader, clamp_int, safe_div


def parse(reader: BinaryReader) -> Dict[str, Any]:
    """解析 FLAC 文件的 STREAMINFO。"""

    out: Dict[str, Any] = {
        "streams": [], "container": {}, "duration_ms": None, "width": None,
        "height": None, "codec": "", "tags": {}, "findings": [],
    }
    if reader.size < 8 or reader.at(0, 4) != b"fLaC":
        out["findings"].append(("E060", "error", "不是合法 FLAC 文件", ""))
        return out

    pos = 4
    block_types = []
    while pos + 4 <= reader.size:
        header = reader.at(pos, 4)
        is_last = bool(header[0] & 0x80)
        btype = header[0] & 0x7F
        length = int.from_bytes(header[1:4], "big")
        block_types.append(btype)
        payload = pos + 4
        if btype == 0 and length >= 34 and payload + 34 <= reader.size:
            block = reader.at(payload, 34)
            min_block = int.from_bytes(block[0:2], "big")
            max_block = int.from_bytes(block[2:4], "big")
            min_frame = int.from_bytes(block[4:7], "big")
            max_frame = int.from_bytes(block[7:10], "big")
            packed = int.from_bytes(block[10:18], "big")
            sample_rate = (packed >> 44) & 0xFFFFF
            channels = ((packed >> 41) & 0x7) + 1
            bits = ((packed >> 36) & 0x1F) + 1
            total_samples = packed & ((1 << 36) - 1)
            out["codec"] = "FLAC"
            out["sample_rate"] = sample_rate or None
            out["channels"] = channels
            out["container"].update({
                "min_block_size": min_block, "max_block_size": max_block,
                "min_frame_size": min_frame, "max_frame_size": max_frame,
                "bits_per_sample": bits, "total_samples": total_samples,
                "md5": block[18:34].hex(),
            })
            if sample_rate and total_samples:
                out["duration_ms"] = clamp_int(safe_div(float(total_samples), sample_rate))
            out["streams"].append({
                "index": 0, "kind": "audio", "codec": "FLAC", "codec_tag": "FLAC",
                "sample_rate": sample_rate or None, "channels": channels, "bit_depth": bits,
            })
        pos = payload + length
        if is_last:
            break
    out["container"]["metadata_blocks"] = block_types[:32]
    return out
