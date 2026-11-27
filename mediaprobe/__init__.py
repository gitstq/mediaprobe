"""MediaProbe - 纯标准库媒体容器元数据探查与审计引擎。

Zero-dependency, offline-first, deterministic media container inspector.
仅依赖 Python 标准库；不调用 ffmpeg；只读；输出可复现的 JSON 清单。
"""

__version__ = "1.0.0"

from .models import AuditFinding, Manifest, StreamInfo
from .probe import probe_file, probe_bytes
__all__ = [
    "AuditFinding",
    "Manifest",
    "StreamInfo",
    "probe_file",
    "probe_bytes",
    "__version__",
]
