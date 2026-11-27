"""CLI 端到端测试。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

from fixtures import make_mp4, make_png

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cli(*args):
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "mediaprobe"] + list(args),
        capture_output=True, text=True, env=env, cwd=ROOT,
    )


class TestCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.mp4 = os.path.join(cls.tmpdir, "sample.mp4")
        with open(cls.mp4, "wb") as f:
            f.write(make_mp4())
        cls.png = os.path.join(cls.tmpdir, "sample.png")
        with open(cls.png, "wb") as f:
            f.write(make_png())

    def test_version(self):
        r = run_cli("--version")
        self.assertEqual(r.returncode, 0)
        self.assertIn("1.0.0", r.stdout)

    def test_inspect(self):
        r = run_cli("inspect", self.mp4)
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertEqual(data["format"], "mp4")
        self.assertEqual(data["width"], 1920)

    def test_inspect_field(self):
        r = run_cli("inspect", self.mp4, "--field", "width")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout), 1920)

    def test_inspect_missing_field(self):
        r = run_cli("inspect", self.mp4, "--field", "nope")
        self.assertEqual(r.returncode, 2)

    def test_batch_jsonl(self):
        out = os.path.join(self.tmpdir, "batch.jsonl")
        r = run_cli("batch", self.tmpdir, "--pattern", "*.mp4", "--output", out)
        self.assertEqual(r.returncode, 0)
        with open(out, encoding="utf-8") as f:
            lines = [line for line in f if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["format"], "mp4")

    def test_audit(self):
        r = run_cli("audit", self.mp4, "--severity", "info")
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertIn("counts", data)
        self.assertIn("findings", data)

    def test_schema(self):
        r = run_cli("schema")
        self.assertEqual(r.returncode, 0)
        schema = json.loads(r.stdout)
        self.assertEqual(schema["title"], "MediaProbe Manifest")
        self.assertIn("properties", schema)

    def test_contract(self):
        r = run_cli("contract")
        self.assertEqual(r.returncode, 0)
        contract = json.loads(r.stdout)
        self.assertEqual(contract["name"], "mediaprobe")
        self.assertTrue(contract["safety"]["read_only"])

    def test_diff(self):
        a = os.path.join(self.tmpdir, "a.json")
        b = os.path.join(self.tmpdir, "b.json")
        data = {"format": "mp4", "width": 1920}
        with open(a, "w") as f:
            json.dump(data, f)
        with open(b, "w") as f:
            json.dump({"format": "mp4", "width": 1280}, f)
        r = run_cli("diff", a, b)
        self.assertEqual(r.returncode, 0)
        result = json.loads(r.stdout)
        self.assertEqual(result["changed_fields"], 1)


if __name__ == "__main__":
    unittest.main()
