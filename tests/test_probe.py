"""核心探查测试：覆盖全部支持格式。"""

from __future__ import annotations

import os
import tempfile
import unittest

from mediaprobe import probe_bytes, probe_file
from mediaprobe.detect import detect
from mediaprobe.utils import BinaryReader

from fixtures import (
    make_aiff, make_flac, make_gif, make_jpeg, make_mp3, make_mp4,
    make_png, make_wav, make_webp,
)


class TestDetection(unittest.TestCase):
    def test_detect_all(self):
        cases = [
            (make_mp4(), "mp4"),
            (make_png(), "png"),
            (make_jpeg(), "jpeg"),
            (make_gif(), "gif"),
            (make_webp(), "webp"),
            (make_flac(), "flac"),
            (make_wav(), "wav"),
            (make_aiff(), "aiff"),
            (make_mp3(), "mp3"),
            (b"\x00\x01\x02", "unknown"),
        ]
        for data, expected in cases:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(data)
                path = f.name
            try:
                with BinaryReader.from_path(path) as reader:
                    self.assertEqual(detect(reader), expected)
            finally:
                os.unlink(path)


class TestProbeFormats(unittest.TestCase):
    def _probe(self, data):
        return probe_bytes(data, "<test>")

    def test_mp4(self):
        m = self._probe(make_mp4(1920, 1080, 5000))
        self.assertEqual(m.fmt, "mp4")
        self.assertEqual(m.width, 1920)
        self.assertEqual(m.height, 1080)
        self.assertEqual(m.duration_ms, 5000)
        self.assertEqual(m.codec, "H.264/AVC")
        self.assertEqual(len(m.streams), 1)
        self.assertEqual(m.streams[0].kind, "video")
        self.assertEqual(m.mime, "video/mp4")

    def test_png(self):
        m = self._probe(make_png(800, 600))
        self.assertEqual(m.fmt, "png")
        self.assertEqual((m.width, m.height), (800, 600))
        self.assertEqual(m.codec, "PNG")

    def test_jpeg(self):
        m = self._probe(make_jpeg(640, 480))
        self.assertEqual(m.fmt, "jpeg")
        self.assertEqual((m.width, m.height), (640, 480))
        self.assertIn("JPEG", m.codec)

    def test_gif(self):
        m = self._probe(make_gif(320, 240))
        self.assertEqual(m.fmt, "gif")
        self.assertEqual((m.width, m.height), (320, 240))

    def test_webp(self):
        m = self._probe(make_webp(400, 300))
        self.assertEqual(m.fmt, "webp")
        self.assertEqual((m.width, m.height), (400, 300))

    def test_flac(self):
        m = self._probe(make_flac(44100, 2, 16, 441000))
        self.assertEqual(m.fmt, "flac")
        self.assertEqual(m.sample_rate, 44100)
        self.assertEqual(m.channels, 2)
        self.assertEqual(m.duration_ms, 10000)
        self.assertEqual(m.codec, "FLAC")

    def test_wav(self):
        m = self._probe(make_wav(44100, 2, 16, 2))
        self.assertEqual(m.fmt, "wav")
        self.assertEqual(m.sample_rate, 44100)
        self.assertEqual(m.channels, 2)
        self.assertEqual(m.duration_ms, 2000)
        self.assertEqual(m.codec, "PCM")

    def test_aiff(self):
        m = self._probe(make_aiff(44100.0, 2, 88200))
        self.assertEqual(m.fmt, "aiff")
        self.assertEqual(m.sample_rate, 44100)
        self.assertEqual(m.duration_ms, 2000)
        self.assertEqual(m.codec, "PCM")

    def test_mp3(self):
        m = self._probe(make_mp3(128, 44100))
        self.assertEqual(m.fmt, "mp3")
        self.assertEqual(m.sample_rate, 44100)
        self.assertEqual(m.channels, 2)
        self.assertEqual(m.tags.get("title"), "Test Title")
        self.assertEqual(m.tags.get("artist"), "Test Artist")
        self.assertEqual(m.codec, "MP3")

    def test_unknown(self):
        m = self._probe(b"just random bytes" * 10)
        self.assertEqual(m.fmt, "unknown")
        self.assertTrue(any(f.code == "W000" for f in m.findings))


class TestDeterminism(unittest.TestCase):
    def test_same_bytes_same_manifest(self):
        data = make_mp4()
        a = probe_bytes(data, "a.mp4").to_dict()
        b = probe_bytes(data, "b.mp4").to_dict()
        a.pop("path")
        b.pop("path")
        self.assertEqual(a, b)

    def test_sha256_stable(self):
        data = make_png()
        self.assertEqual(probe_bytes(data).sha256, probe_bytes(data).sha256)
        self.assertEqual(len(probe_bytes(data).sha256), 64)

    def test_no_hash(self):
        m = probe_file(__file__, compute_hash=False)
        self.assertEqual(m.sha256, "")


if __name__ == "__main__":
    unittest.main()
