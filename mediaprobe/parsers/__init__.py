"""各容器格式解析器。每个解析器只依赖 BinaryReader，输出统一字段字典。"""

from . import aiff, avi, bmff, ebml, flac, id3, image, wav

PARSERS = {
    "mp4": bmff.parse,
    "mov": bmff.parse,
    "m4a": bmff.parse,
    "mkv": ebml.parse,
    "webm": ebml.parse,
    "ebml": ebml.parse,
    "mp3": id3.parse,
    "wav": wav.parse,
    "avi": avi.parse,
    "aiff": aiff.parse,
    "flac": flac.parse,
    "png": image.parse_png,
    "jpeg": image.parse_jpeg,
    "gif": image.parse_gif,
    "webp": image.parse_webp,
}

__all__ = ["PARSERS"]
