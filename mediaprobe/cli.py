"""命令行界面：inspect / batch / audit / diff / schema / contract。"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from typing import Any, Dict, Iterable, List, Optional

from . import __version__, probe_file
from .audit import severity_counts
from .models import Manifest
from .schema import get_manifest_schema, get_tool_contract


def _dump(data: Any, pretty: bool = False) -> str:
    """确定性 JSON 序列化：键排序、固定缩进、保留中文。"""

    if pretty:
        return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2)
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _iter_files(directory: str, pattern: str, recursive: bool) -> Iterable[str]:
    """按 glob 模式迭代文件，输出按路径排序保证确定性。"""

    found: List[str] = []
    if recursive:
        for root, dirs, files in os.walk(directory):
            dirs.sort()
            for name in files:
                if fnmatch.fnmatch(name, pattern):
                    found.append(os.path.join(root, name))
    else:
        for name in sorted(os.listdir(directory)):
            path = os.path.join(directory, name)
            if os.path.isfile(path) and fnmatch.fnmatch(name, pattern):
                found.append(path)
    for path in sorted(found):
        yield path


def cmd_inspect(args: argparse.Namespace) -> int:
    """探查单个文件。"""

    try:
        manifest = probe_file(args.path, compute_hash=not args.no_hash)
    except (OSError, ValueError) as exc:
        print("错误: %s" % exc, file=sys.stderr)
        return 2
    if args.field:
        value: Any = manifest.to_dict()
        for key in args.field.split("."):
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                print("错误: 字段不存在: %s" % args.field, file=sys.stderr)
                return 2
        print(_dump(value, args.pretty))
    else:
        print(_dump(manifest.to_dict(), args.pretty))
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    """批量探查并输出 JSONL。"""

    if not os.path.isdir(args.directory):
        print("错误: 目录不存在: %s" % args.directory, file=sys.stderr)
        return 2
    handle = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        count = 0
        for path in _iter_files(args.directory, args.pattern, args.recursive):
            try:
                manifest = probe_file(path, compute_hash=not args.no_hash)
            except (OSError, ValueError):
                continue
            handle.write(_dump(manifest.to_dict()) + "\n")
            count += 1
        if args.output:
            print("已写入 %d 条记录: %s" % (count, args.output), file=sys.stderr)
    finally:
        if args.output:
            handle.close()
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    """审计: 只输出指定及以上级别的发现。"""

    rank = {"info": 0, "warn": 1, "error": 2}
    try:
        manifest = probe_file(args.path, compute_hash=False)
    except (OSError, ValueError) as exc:
        print("错误: %s" % exc, file=sys.stderr)
        return 2
    threshold = rank[args.severity]
    selected = [f for f in manifest.findings if rank.get(f.severity, 0) >= threshold]
    result = {
        "path": args.path,
        "format": manifest.fmt,
        "counts": severity_counts(manifest.findings),
        "threshold": args.severity,
        "findings": [f.to_dict() for f in selected],
    }
    print(_dump(result, args.pretty))
    return 1 if any(f.severity == "error" for f in manifest.findings) else 0


def cmd_diff(args: argparse.Namespace) -> int:
    """对比两个清单文件的字段差异。"""

    try:
        with open(args.left, "r", encoding="utf-8") as f:
            left: Dict[str, Any] = json.load(f)
        with open(args.right, "r", encoding="utf-8") as f:
            right: Dict[str, Any] = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print("错误: %s" % exc, file=sys.stderr)
        return 2
    keys = sorted(set(left) | set(right))
    changes = []
    for key in keys:
        if left.get(key) != right.get(key):
            changes.append({"field": key, "left": left.get(key), "right": right.get(key)})
    print(_dump({"changed_fields": len(changes), "changes": changes}, args.pretty))
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    """输出 Manifest JSON Schema。"""

    print(_dump(get_manifest_schema(), args.pretty))
    return 0


def cmd_contract(args: argparse.Namespace) -> int:
    """输出机器可读工具契约。"""

    print(_dump(get_tool_contract(), args.pretty))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """构建 argparse 解析器。"""

    parser = argparse.ArgumentParser(
        prog="mediaprobe",
        description="MediaProbe - 纯标准库媒体容器元数据探查与审计引擎",
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="探查单个文件")
    p_inspect.add_argument("path", help="媒体文件路径")
    p_inspect.add_argument("--pretty", action="store_true", help="美化输出")
    p_inspect.add_argument("--no-hash", action="store_true", help="跳过 SHA-256 计算")
    p_inspect.add_argument("--field", help="只输出指定字段（用 . 分隔层级）")
    p_inspect.set_defaults(func=cmd_inspect)

    p_batch = sub.add_parser("batch", help="批量探查目录")
    p_batch.add_argument("directory", help="目录路径")
    p_batch.add_argument("--pattern", default="*", help="文件名 glob 模式")
    p_batch.add_argument("--recursive", action="store_true", help="递归子目录")
    p_batch.add_argument("--output", help="输出 JSONL 文件路径")
    p_batch.add_argument("--no-hash", action="store_true", help="跳过 SHA-256 计算")
    p_batch.set_defaults(func=cmd_batch)

    p_audit = sub.add_parser("audit", help="审计并过滤发现")
    p_audit.add_argument("path", help="媒体文件路径")
    p_audit.add_argument("--severity", choices=["info", "warn", "error"], default="warn")
    p_audit.add_argument("--pretty", action="store_true")
    p_audit.set_defaults(func=cmd_audit)

    p_diff = sub.add_parser("diff", help="对比两个清单 JSON")
    p_diff.add_argument("left")
    p_diff.add_argument("right")
    p_diff.add_argument("--pretty", action="store_true")
    p_diff.set_defaults(func=cmd_diff)

    p_schema = sub.add_parser("schema", help="输出 Manifest JSON Schema")
    p_schema.add_argument("--pretty", action="store_true")
    p_schema.set_defaults(func=cmd_schema)

    p_contract = sub.add_parser("contract", help="输出机器可读工具契约")
    p_contract.add_argument("--pretty", action="store_true")
    p_contract.set_defaults(func=cmd_contract)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 主入口。"""

    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
