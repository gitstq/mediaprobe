<div align="center">

# 🎬 MediaProbe

**Zero-dependency · Offline-first · Deterministic media container metadata inspector & auditor**

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-green.svg)](https://www.python.org/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0-orange.svg)](pyproject.toml)

[简体中文](README.md) · [繁體中文](README.zh-TW.md) · [English](README.en.md)

</div>

---

## 🎉 Introduction

Ever needed the resolution, duration, or codec of a video file — without downloading a 300 MB transcoding toolkit or uploading anything to the cloud?

**MediaProbe** is exactly that. It is a **read-only** structured metadata inspector: it parses container binary structures directly and emits a reproducible JSON manifest. No `ffmpeg`, no network, no writes to the source file, and no third-party libraries.

It shares the philosophy of the local-video tools trending right now — **local-first, machine-readable, cloud-free** — but it is deliberately different:

| Dimension | Typical local video skill | MediaProbe |
| --- | --- | --- |
| Purpose | Editor (mutates files) | Probe (read-only) |
| Dependencies | Requires ffmpeg binary | **Zero deps, stdlib only** |
| Output | Transcoded media | **Deterministic JSON manifest + audit findings** |
| Reproducibility | Depends on encoder version | **Same bytes → same manifest** |
| Integration | Needs a toolchain | `pip install` or plain `python -m` |

In one line: **it's the `file` command for media files, plus a structural auditor, built for AI agents and automation pipelines.**

---

## ✨ Features

- 🧩 **Broad format support** — MP4/MOV/M4A, Matroska/WebM, MP3 (ID3v2/v1), WAV, AVI, AIFF, FLAC, plus PNG/JPEG/GIF/WebP image dimensions.
- 🧱 **Pure standard library** — only `struct`, `hashlib`, `argparse`, and friends. Runtime dependency count: **0**.
- 🔒 **Safe and read-only** — no subprocess execution, no network, no writes to source files. Safe for untrusted input in automated contexts.
- 🎯 **Deterministic output** — sorted keys, fixed fields, millisecond precision; identical input bytes produce byte-identical JSON.
- 🔍 **Structural auditing** — detects non-faststart `moov`, RIFF size mismatches, ID3v1/v2 tag conflicts, truncated files, and 10+ other issues with actionable hints.
- 🤖 **Agent-ready** — ships a machine-readable [tool contract](schemas/tool-contract.json) and [JSON Schema](schemas/manifest.schema.json) for drop-in integration.
- 🪶 **Low memory** — random-access reads, never loads the whole media file; streaming SHA-256.
- 🧪 **Thoroughly tested** — 23 unit tests covering every format, determinism, and CLI end-to-end; fixtures are synthesized in code, no external media required.
- 🌍 **Three languages** — Simplified Chinese, Traditional Chinese, and English, written natively.

---

## 🚀 Quick Start

### Installation

```bash
# Option 1: install from source (no dependency download needed)
pip install .

# Option 2: run directly, zero install
python -m mediaprobe --version

# Option 3: single-file zipapp bundle
python dist/mediaprobe-1.0.0.pyz inspect video.mp4
```

Requires Python 3.8+. **There is no requirements.txt — because there are genuinely no dependencies.**

### 30-second tour

```bash
# Inspect a single file
python -m mediaprobe inspect video.mp4

# Pretty output
python -m mediaprobe inspect video.mp4 --pretty

# Extract one field
python -m mediaprobe inspect video.mp4 --field width
```

Sample output:

```json
{
  "bitrate_bps": 811,
  "codec": "H.264/AVC",
  "container": {"box_count": 3, "major_brand": "isom", "moov_offset": 28, "timescale": 1000},
  "duration_ms": 5000,
  "format": "mp4",
  "height": 1080,
  "mime": "video/mp4",
  "path": "video.mp4",
  "sha256": "c77b8b92...",
  "size_bytes": 507,
  "width": 1920
}
```

---

## 📖 Usage Guide

### CLI commands

| Command | Purpose | Example |
| --- | --- | --- |
| `inspect` | Inspect one file | `mediaprobe inspect a.mp4 --pretty` |
| `batch` | Inspect a directory into JSONL | `mediaprobe batch ./media --pattern "*.mp4" --recursive` |
| `audit` | Filter audit findings by severity | `mediaprobe audit a.mp4 --severity error` |
| `diff` | Compare two manifest JSON files | `mediaprobe diff a.json b.json` |
| `schema` | Print the Manifest JSON Schema | `mediaprobe schema --pretty` |
| `contract` | Print the machine-readable tool contract | `mediaprobe contract` |

### Library integration

```python
from mediaprobe import probe_file, probe_bytes

m = probe_file("video.mp4")
print(m.width, m.height, m.duration_ms, m.codec)

m = probe_bytes(open("video.mp4", "rb").read())   # ideal for APIs / agents
print(m.to_dict())
print(m.findings)

m = probe_file("huge.mkv", compute_hash=False)     # skip hashing for very large files
```

### Agent integration

The JSON emitted by `contract` describes every command and its arguments, so it can be registered directly as a tool declaration in an agent framework:

```bash
mediaprobe contract > tool-contract.json
```

Pair it with `schemas/manifest.schema.json` to validate return values automatically. The `safety` block states the guarantees explicitly: `read_only: true`, `network_access: false`, `external_processes: false`.

### Audit severities

| Severity | Meaning | Exit code |
| --- | --- | --- |
| `error` | Structural problem (required box/chunk missing) | `1` |
| `warn` | Improvement opportunity (non-faststart, tag conflict, suspected truncation) | `0` |
| `info` | Informational note | `0` |

`audit` exits with code `1` on any `error`, making it suitable as a CI quality gate.

### Supported formats

| Format | Parsed fields |
| --- | --- |
| MP4/MOV/M4A | ftyp brands, moov/mvhd duration, trak/tkhd dimensions, mdhd, hdlr, stsd codec |
| MKV/WebM | DocType, TimecodeScale, Duration, video/audio codecs, sample rate, channels |
| MP3 | ID3v2.2/2.3/2.4 text frames, ID3v1, MPEG frame header bitrate/sample rate/channels |
| WAV | fmt chunk, data chunk, PCM/float/extensible formats |
| AVI | avih main header, frame count, dimensions, duration |
| AIFF/AIFC | COMM chunk, 80-bit extended-precision sample rate |
| FLAC | STREAMINFO, sample rate/channels/bit depth/total samples |
| Images | PNG IHDR, JPEG SOF, GIF logical screen, WebP VP8X/VP8/VP8L |

---

## 💡 Design & Iteration

### Why build from scratch instead of copying

Trending local-video projects mostly follow a "skill bundle + MCP server + ffmpeg invocation" pattern — capable, but dependency-heavy. The existing toolbox on this account also clusters around text, protocols, and forensics; **media container parsing was a gap**.

So this project differentiates on three points:

1. **A read-only probe, not an editor** — no transcoding, no cutting; it only answers "what is this file?".
2. **Zero dependencies, stdlib only** — binary structures are parsed directly, avoiding ffmpeg version differences and installation overhead.
3. **Determinism and auditability** — output is hash-comparable and accompanied by structural findings, ready for CI and agent pipelines.

### Changelog

| Version | Changes |
| --- | --- |
| v1.0.0 | Initial release: 8 container/image parsers, 10+ audit rules, 6 CLI subcommands, three-language docs, 23 tests |

### Design trade-offs

- **Not every box/element is parsed** — only the structures useful for metadata; speed first, no complexity for irrelevant fields.
- **MP3 duration is a CBR estimate** — derived from the first MPEG frame header's bitrate and audio data byte count. VBR files will deviate, so raw parameters are retained in `container.mpeg` for callers to judge.
- **Out-of-bounds reads fail loudly** — `BinaryReader` raises `ValueError` rather than silently producing wrong metadata.
- **No timestamp fields** — the manifest contains no `generated_at`-style fields, ensuring reproducibility; file times should be obtained from the filesystem by the caller.

---

## 📦 Packaging & Deployment

### One-command build

```bash
bash scripts/build.sh
```

Artifacts land in `dist/`:

- `mediaprobe-1.0.0-source.tar.gz` — source archive
- `mediaprobe-1.0.0.pyz` — zipapp single-file bundle (needs Python 3)
- `SHA256SUMS.txt` — checksum manifest

### Verify integrity

```bash
cd dist
sha256sum -c SHA256SUMS.txt
```

### Cross-platform

Pure Python runs on Windows, macOS, and Linux:

```bash
# Windows PowerShell
python -m mediaprobe inspect video.mp4

# macOS / Linux
python3 -m mediaprobe inspect video.mp4
```

### Releases

Release `v1.0.0` includes all artifacts above plus checksums. For library use no release is needed — just `pip install .`.

---

## 🤝 Contributing

Issues and pull requests are welcome. Please read the [contribution guide](CONTRIBUTING.md) first.

- 🐛 Bug reports: include Python version, reproduction steps, and `inspect --pretty` output.
- ✨ New formats: update the detector, parser, schema, and all three READMEs, and add synthesized fixture tests.
- ⚖️ Commit messages follow the Angular convention: `feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `build:` / `chore:`.

---

## 📄 License

Released under the [MIT License](LICENSE).

> This project only parses file structures. It does not decode, transcode, or distribute any media content. Users are responsible for ensuring they have legitimate rights to the files they process.
