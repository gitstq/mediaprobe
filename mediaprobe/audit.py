"""通用审计规则：对清单与原始 reader 做一致性检查。

规则设计原则：只读、确定性、给出可操作 hint。
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .models import AuditFinding
from .utils import BinaryReader

# 规则严重级别排序
SEVERITY_ORDER = {"error": 0, "warn": 1, "info": 2}


def audit_manifest(reader: BinaryReader, parsed: Dict[str, Any]) -> List[AuditFinding]:
    """基于解析结果生成审计发现。"""

    findings: List[Tuple[str, str, str, str]] = list(parsed.get("findings", []))
    fmt = parsed.get("fmt_override") or parsed.get("fmt", "unknown")

    if reader.size < 32:
        findings.append(("W001", "warn", "文件过小（%d 字节），可能为占位或损坏" % reader.size, ""))

    if parsed.get("duration_ms") == 0:
        findings.append(("W002", "warn", "解析出的时长为 0，元数据可能不完整", ""))

    if fmt == "unknown":
        findings.append(("W000", "warn", "无法识别文件格式，仅提供基础信息",
                         "支持 MP4/MOV/MKV/WebM/MP3/WAV/AVI/AIFF/FLAC 及常见图片"))

    streams = parsed.get("streams", [])
    if streams and all(s.get("kind") == "unknown" for s in streams):
        findings.append(("W003", "warn", "所有流类型均无法识别", ""))

    # 图片尺寸合理性
    width, height = parsed.get("width"), parsed.get("height")
    if width is not None and height is not None and (width > 100000 or height > 100000):
        findings.append(("W004", "warn", "宽高数值异常：%dx%d" % (width, height), ""))

    # 去重（相同 code + message 只保留一条）
    seen = set()
    unique: List[AuditFinding] = []
    for code, severity, message, hint in findings:
        key = (code, message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(AuditFinding(code=code, severity=severity, message=message, hint=hint))
    unique.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.code, f.message))
    return unique


def severity_counts(findings: List[AuditFinding]) -> Dict[str, int]:
    """统计各级别发现数量。"""

    counts = {"error": 0, "warn": 0, "info": 0}
    for finding in findings:
        if finding.severity in counts:
            counts[finding.severity] += 1
    return counts
