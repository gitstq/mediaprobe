"""JSON Schema 与 Agent 工具契约（machine-readable contract）。

供 AI Agent / 自动化流程消费；与 Trending 上 "machine-readable contract" 理念一致，
但本项目为纯只读探查器，不执行任何转码或修改。
"""

from __future__ import annotations

from typing import Any, Dict

MANIFEST_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://github.com/gitstq/mediaprobe/blob/main/schemas/manifest.schema.json",
    "title": "MediaProbe Manifest",
    "description": "确定性媒体容器元数据清单",
    "type": "object",
    "required": ["path", "size_bytes", "sha256", "format"],
    "additionalProperties": False,
    "properties": {
        "path": {"type": "string"},
        "size_bytes": {"type": "integer", "minimum": 0},
        "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "format": {"type": "string"},
        "mime": {"type": "string"},
        "duration_ms": {"type": "integer", "minimum": 0},
        "width": {"type": "integer", "minimum": 0},
        "height": {"type": "integer", "minimum": 0},
        "bitrate_bps": {"type": "integer", "minimum": 0},
        "sample_rate": {"type": "integer", "minimum": 0},
        "channels": {"type": "integer", "minimum": 0},
        "codec": {"type": "string"},
        "tags": {"type": "object", "additionalProperties": {"type": "string"}},
        "streams": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["index", "kind", "codec", "codec_tag"],
                "properties": {
                    "index": {"type": "integer", "minimum": 0},
                    "kind": {"type": "string", "enum": ["video", "audio", "subtitle", "attachment", "unknown"]},
                    "codec": {"type": "string"},
                    "codec_tag": {"type": "string"},
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                    "sample_rate": {"type": "integer"},
                    "channels": {"type": "integer"},
                    "bit_depth": {"type": "integer"},
                    "language": {"type": "string"},
                    "duration_ms": {"type": "integer"},
                    "bitrate_bps": {"type": "integer"},
                    "extra": {"type": "object"},
                },
            },
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["code", "severity", "message"],
                "properties": {
                    "code": {"type": "string"},
                    "severity": {"type": "string", "enum": ["error", "warn", "info"]},
                    "message": {"type": "string"},
                    "hint": {"type": "string"},
                },
            },
        },
        "container": {"type": "object"},
        "tool": {"type": "object"},
    },
}

TOOL_CONTRACT: Dict[str, Any] = {
    "name": "mediaprobe",
    "version": "1.0.0",
    "description": "只读媒体容器元数据探查与审计；无网络、无外部依赖、不修改文件",
    "transport": "cli",
    "commands": [
        {
            "name": "inspect",
            "description": "探查单个媒体文件并返回 JSON 清单",
            "arguments": [
                {"name": "path", "type": "string", "required": True},
                {"name": "--pretty", "type": "boolean", "default": False},
                {"name": "--no-hash", "type": "boolean", "default": False},
            ],
        },
        {
            "name": "batch",
            "description": "批量探查目录，输出 JSONL",
            "arguments": [
                {"name": "directory", "type": "string", "required": True},
                {"name": "--pattern", "type": "string", "default": "*"},
                {"name": "--recursive", "type": "boolean", "default": False},
            ],
        },
        {
            "name": "audit",
            "description": "按严重级别过滤审计发现",
            "arguments": [
                {"name": "path", "type": "string", "required": True},
                {"name": "--severity", "type": "string", "enum": ["error", "warn", "info"], "default": "warn"},
            ],
        },
        {
            "name": "diff",
            "description": "对比两个清单的字段差异",
            "arguments": [
                {"name": "left", "type": "string", "required": True},
                {"name": "right", "type": "string", "required": True},
            ],
        },
        {
            "name": "schema",
            "description": "输出 Manifest JSON Schema",
            "arguments": [],
        },
        {
            "name": "contract",
            "description": "输出本工具契约",
            "arguments": [],
        },
    ],
    "safety": {
        "read_only": True,
        "network_access": False,
        "external_processes": False,
        "max_file_size_bytes": None,
    },
}


def get_manifest_schema() -> Dict[str, Any]:
    """返回 Manifest JSON Schema 的副本。"""

    import copy
    return copy.deepcopy(MANIFEST_SCHEMA)


def get_tool_contract() -> Dict[str, Any]:
    """返回工具契约的副本。"""

    import copy
    return copy.deepcopy(TOOL_CONTRACT)
