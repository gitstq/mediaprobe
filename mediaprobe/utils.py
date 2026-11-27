"""底层二进制读取与确定性辅助函数（全部基于标准库）。"""

from __future__ import annotations

import hashlib
import os
from typing import BinaryIO, Iterator, Optional, Tuple


class BinaryReader:
    """带边界检查的随机访问读取器。

    所有 read_* 方法在越界时抛出 ValueError，避免静默产生错误元数据。
    """

    def __init__(self, stream: BinaryIO, size: int):
        self.stream = stream
        self.size = size

    @classmethod
    def from_path(cls, path: str) -> "BinaryReader":
        f = open(path, "rb")
        try:
            size = os.fstat(f.fileno()).st_size
        except Exception:
            f.close()
            raise
        return cls(f, size)

    def close(self) -> None:
        self.stream.close()

    def __enter__(self) -> "BinaryReader":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def at(self, offset: int, length: int) -> bytes:
        if offset < 0 or length < 0 or offset + length > self.size:
            raise ValueError(
                "越界读取: offset=%d length=%d size=%d" % (offset, length, self.size)
            )
        self.stream.seek(offset)
        data = self.stream.read(length)
        if len(data) != length:
            raise ValueError("读取不完整: 期望 %d 字节, 实际 %d 字节" % (length, len(data)))
        return data

    def u8(self, offset: int) -> int:
        return self.at(offset, 1)[0]

    def u16be(self, offset: int) -> int:
        return int.from_bytes(self.at(offset, 2), "big")

    def u24be(self, offset: int) -> int:
        return int.from_bytes(self.at(offset, 3), "big")

    def u32be(self, offset: int) -> int:
        return int.from_bytes(self.at(offset, 4), "big")

    def u64be(self, offset: int) -> int:
        return int.from_bytes(self.at(offset, 8), "big")

    def u16le(self, offset: int) -> int:
        return int.from_bytes(self.at(offset, 2), "little")

    def u32le(self, offset: int) -> int:
        return int.from_bytes(self.at(offset, 4), "little")

    def u64le(self, offset: int) -> int:
        return int.from_bytes(self.at(offset, 8), "little")

    def fourcc(self, offset: int) -> str:
        return decode_fourcc(self.at(offset, 4))


def decode_fourcc(raw: bytes) -> str:
    """把 4 字节 FourCC 解码为可打印 ASCII，不可打印字符替换为 '.'。"""

    return "".join(chr(b) if 32 <= b <= 126 else "." for b in raw)


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    """流式计算 SHA-256，常量内存占用。"""

    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def clamp_int(value: Optional[float]) -> Optional[int]:
    """把秒值转成毫秒整数并做安全裁剪。"""

    if value is None:
        return None
    if value != value or value in (float("inf"), float("-inf")):
        return None
    if value < 0:
        return 0
    return int(round(value * 1000))


def clamp_ms(value: Optional[float]) -> Optional[int]:
    """把毫秒值转成整数并做安全裁剪。"""

    if value is None:
        return None
    if value != value or value in (float("inf"), float("-inf")):
        return None
    if value < 0:
        return 0
    return int(round(value))


def safe_div(num: float, den: float) -> Optional[float]:
    """安全除法：分母非法时返回 None。"""

    if den is None or den == 0:
        return None
    try:
        result = num / den
    except (TypeError, ZeroDivisionError):
        return None
    if result != result or result in (float("inf"), float("-inf")):
        return None
    return result


def read_vint(data: bytes, pos: int, keep_marker: bool = False):
    """读取 EBML 可变长整数，返回 (value, consumed)。

    keep_marker=True 时保留首字节的标记位（用于 Element ID），
    False 时清除标记位（用于 Element Size）。全 1 值表示未知大小，返回 None。
    """

    if pos >= len(data):
        raise ValueError("EBML vint 越界")
    first = data[pos]
    if first == 0:
        raise ValueError("EBML vint 首字节为 0")
    length = 1
    mask = 0x80
    while not (first & mask):
        length += 1
        mask >>= 1
        if length > 8:
            raise ValueError("EBML vint 长度超过 8")
    if pos + length > len(data):
        raise ValueError("EBML vint 截断")
    raw = bytearray(data[pos : pos + length])
    raw[0] = first & (mask - 1) if not keep_marker else first
    value = int.from_bytes(bytes(raw), "big")
    if not keep_marker and value == (1 << (7 * length)) - 1:
        return None, length
    return value, length


def syncsafe(reader: "BinaryReader", offset: int) -> int:
    """ID3v2 syncsafe 整数：每字节只取低 7 位。"""

    b = reader.at(offset, 4)
    return (b[0] << 21) | (b[1] << 14) | (b[2] << 7) | b[3]


def iter_boxes(reader: "BinaryReader", start: int, end: int, depth: int = 0):
    """迭代 ISO BMFF 顶层/子层 box，返回 (type, payload_start, box_end, header_len)。

    支持 size==1（64 位 largesize）与 size==0（延伸到父容器末尾）。
    """

    if depth > 12:
        return
    pos = start
    while pos + 8 <= end:
        head = reader.at(pos, 8)
        size32 = int.from_bytes(head[:4], "big")
        box_type = decode_fourcc(head[4:8])
        header_len = 8
        if size32 == 1:
            if pos + 16 > end:
                return
            size = reader.u64be(pos + 8)
            header_len = 16
        elif size32 == 0:
            size = end - pos
        else:
            size = size32
        if size < header_len or pos + size > end:
            return
        yield box_type, pos + header_len, pos + size, header_len
        pos += size
