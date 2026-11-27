"""数据模型：清单（Manifest）、流信息（StreamInfo）、审计发现（AuditFinding）。

所有模型都提供 to_dict()，保证字段顺序固定，便于生成确定性 JSON。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AuditFinding:
    """一条审计发现。severity 取值：error / warn / info。"""

    code: str
    severity: str
    message: str
    hint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }
        if self.hint:
            result["hint"] = self.hint
        return result


@dataclass
class StreamInfo:
    """一条媒体流（视频/音频/字幕/附件）。"""

    index: int
    kind: str                       # video | audio | subtitle | attachment | unknown
    codec: str = ""                 # 归一化编码名，如 H.264 / Opus / PCM
    codec_tag: str = ""             # 容器原始标识，如 avc1 / V_VP9
    width: Optional[int] = None
    height: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    bit_depth: Optional[int] = None
    language: str = ""
    duration_ms: Optional[int] = None
    bitrate_bps: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "index": self.index,
            "kind": self.kind,
            "codec": self.codec,
            "codec_tag": self.codec_tag,
        }
        for key in ("width", "height", "sample_rate", "channels", "bit_depth"):
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        if self.language:
            data["language"] = self.language
        if self.duration_ms is not None:
            data["duration_ms"] = self.duration_ms
        if self.bitrate_bps is not None:
            data["bitrate_bps"] = self.bitrate_bps
        if self.extra:
            data["extra"] = dict(sorted(self.extra.items()))
        return data


@dataclass
class Manifest:
    """媒体文件的确定性元数据清单。"""

    path: str
    size_bytes: int
    sha256: str
    fmt: str                        # mp4/mov/mkv/webm/mp3/wav/avi/aiff/flac/png/jpeg/gif/webp/unknown
    mime: str = "application/octet-stream"
    duration_ms: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    bitrate_bps: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    codec: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    streams: List[StreamInfo] = field(default_factory=list)
    findings: List[AuditFinding] = field(default_factory=list)
    container: Dict[str, Any] = field(default_factory=dict)
    tool: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "format": self.fmt,
            "mime": self.mime,
        }
        for key in (
            "duration_ms",
            "width",
            "height",
            "bitrate_bps",
            "sample_rate",
            "channels",
        ):
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        if self.codec:
            data["codec"] = self.codec
        if self.tags:
            data["tags"] = dict(sorted(self.tags.items()))
        if self.streams:
            data["streams"] = [s.to_dict() for s in self.streams]
        if self.findings:
            data["findings"] = [f.to_dict() for f in self.findings]
        if self.container:
            data["container"] = dict(sorted(self.container.items()))
        if self.tool:
            data["tool"] = dict(sorted(self.tool.items()))
        return data
