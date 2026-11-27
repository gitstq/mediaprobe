"""合成测试样本生成器：不依赖任何外部媒体文件或 ffmpeg。"""

from __future__ import annotations

import math
import struct


def box(box_type: bytes, payload: bytes) -> bytes:
    """构造 ISO BMFF box。"""

    return struct.pack(">I", 8 + len(payload)) + box_type + payload


def make_mp4(width: int = 1920, height: int = 1080, duration_ms: int = 5000) -> bytes:
    """构造最小 MP4：ftyp + moov(mvhd, trak) + mdat。"""

    timescale = 1000
    duration = duration_ms

    def mvhd(version: int = 0) -> bytes:
        if version == 0:
            body = struct.pack(">IIII", 0, 0, timescale, duration) + b"\x00" * 80
        else:
            body = struct.pack(">QQIQ", 0, 0, timescale, duration) + b"\x00" * 80
        return box(b"mvhd", bytes([version]) + b"\x00\x00\x00" + body)

    def tkhd() -> bytes:
        # version 0: 4(ver/flags) + 4+4+4+4+4 + 8 + 2+2+2+2 + 36 + width + height
        body = b"\x00" * 4
        body += struct.pack(">IIIII", 0, 0, 1, 0, duration)
        body += b"\x00" * 8
        body += struct.pack(">hhhh", 0, 0, 0, 0)
        body += b"\x00" * 36
        body += struct.pack(">II", width << 16, height << 16)
        return box(b"tkhd", body)

    def mdhd() -> bytes:
        body = b"\x00" * 4 + struct.pack(">IIII", 0, 0, timescale, duration)
        return box(b"mdhd", body)

    def hdlr(handler: bytes) -> bytes:
        body = b"\x00" * 4 + b"\x00" * 4 + handler + b"\x00" * 12 + b"VideoHandler\x00"
        return box(b"hdlr", body)

    def stsd(tag: bytes) -> bytes:
        entry = box(tag, b"\x00" * 78)
        body = b"\x00" * 4 + struct.pack(">I", 1) + entry
        return box(b"stsd", body)

    minf = box(b"minf", stsd(tag=b"avc1"))
    mdia = box(b"mdia", mdhd() + hdlr(b"vide") + minf)
    trak = box(b"trak", tkhd() + mdia)
    moov = box(b"moov", mvhd() + trak)
    ftyp = box(b"ftyp", b"isom" + struct.pack(">I", 512) + b"isomiso2mp41")
    mdat = box(b"mdat", b"\x00" * 64)
    return ftyp + moov + mdat


def make_png(width: int = 800, height: int = 600) -> bytes:
    """构造最小 PNG（仅签名 + IHDR）。"""

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return sig + struct.pack(">I", 13) + b"IHDR" + ihdr + struct.pack(">I", 0)


def make_jpeg(width: int = 640, height: int = 480) -> bytes:
    """构造含 SOF0 的最小 JPEG 头。"""

    sof = struct.pack(">BHHB", 8, height, width, 3) + b"\x01\x11\x00\x02\x11\x01\x03\x11\x01"
    return b"\xff\xd8" + b"\xff\xc0" + struct.pack(">H", len(sof) + 2) + sof + b"\xff\xd9"


def make_gif(width: int = 320, height: int = 240) -> bytes:
    return b"GIF89a" + struct.pack("<HH", width, height) + b"\xf7\x00\x00" + b"\x00" * 12 + b"\x3b"


def make_webp(width: int = 400, height: int = 300) -> bytes:
    payload = b"\x00" + b"\x00\x00\x00" + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little") + b"\x00\x00\x00\x00"
    return b"RIFF" + struct.pack("<I", 4 + 8 + len(payload)) + b"WEBPVP8X" + struct.pack("<I", len(payload)) + payload


def make_flac(sample_rate: int = 44100, channels: int = 2, bits: int = 16, total: int = 441000) -> bytes:
    """构造含 STREAMINFO 的最小 FLAC 头。"""

    packed = (sample_rate << 44) | ((channels - 1) << 41) | ((bits - 1) << 36) | total
    streaminfo = struct.pack(">HH", 4096, 4096) + b"\x00" * 6 + packed.to_bytes(8, "big") + b"\x00" * 16
    header = bytes([0x80]) + len(streaminfo).to_bytes(3, "big")
    return b"fLaC" + header + streaminfo


def make_wav(sample_rate: int = 44100, channels: int = 2, bits: int = 16, seconds: int = 2) -> bytes:
    """构造最小 WAV。"""

    byte_rate = sample_rate * channels * bits // 8
    data_size = byte_rate * seconds
    fmt = struct.pack("<HHIIHH", 1, channels, sample_rate, byte_rate, channels * bits // 8, bits)
    riff_size = 4 + (8 + len(fmt)) + (8 + data_size)
    return (
        b"RIFF" + struct.pack("<I", riff_size) + b"WAVE"
        + b"fmt " + struct.pack("<I", len(fmt)) + fmt
        + b"data" + struct.pack("<I", data_size) + b"\x00" * min(data_size, 64)
    )


def make_aiff(sample_rate: float = 44100.0, channels: int = 2, frames: int = 88200) -> bytes:
    """构造最小 AIFF（COMM 块，80 位采样率）。"""

    def ext80(value: float) -> bytes:
        if value == 0:
            return b"\x00" * 10
        exp = 16383 + int(math.floor(math.log2(value)))
        mant = int(value / (2.0 ** (exp - 16383)) * (1 << 63))
        return struct.pack(">H", exp) + mant.to_bytes(8, "big")

    comm = struct.pack(">HIH", channels, frames, 16) + ext80(sample_rate)
    form_size = 4 + 8 + len(comm)
    return b"FORM" + struct.pack(">I", form_size) + b"AIFF" + b"COMM" + struct.pack(">I", len(comm)) + comm


def make_mp3(bitrate_kbps: int = 128, sample_rate: int = 44100) -> bytes:
    """构造含 ID3v2 标签与 MPEG1 Layer3 帧头的最小 MP3。"""

    # ID3v2.3 tag: title + artist
    def text_frame(fid: bytes, text: str) -> bytes:
        payload = b"\x00" + text.encode("latin-1")
        return fid + struct.pack(">I", len(payload)) + b"\x00\x00" + payload

    frames = text_frame(b"TIT2", "Test Title") + text_frame(b"TPE1", "Test Artist")
    tag_size = len(frames)
    syncsafe = bytes([
        (tag_size >> 21) & 0x7F, (tag_size >> 14) & 0x7F,
        (tag_size >> 7) & 0x7F, tag_size & 0x7F,
    ])
    id3 = b"ID3" + bytes([3, 0, 0]) + syncsafe + frames

    br_index = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0].index(bitrate_kbps)
    sr_index = [44100, 48000, 32000].index(sample_rate)
    frame_header = bytes([
        0xFF, 0xFB,
        (br_index << 4) | (sr_index << 2),
        0x00,
    ])
    return id3 + frame_header + b"\x00" * 2048
