<div align="center">

# 🎬 MediaProbe

**零依赖 · 离线优先 · 确定性的媒体容器元数据探查与审计引擎**

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-green.svg)](https://www.python.org/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0-orange.svg)](pyproject.toml)

[简体中文](README.md) · [繁體中文](README.zh-TW.md) · [English](README.en.md)

</div>

---

## 🎉 介绍

你是否有过这样的时刻：手上有一个视频文件，想知道它的分辨率、时长、编码格式，却不想下载一个几百兆的转码工具包，也不想让文件联网上传？

**MediaProbe** 就是为此而生。它是一个**只读**的媒体元数据结构化探查器——直接解析容器二进制结构，输出一份可复现的 JSON 清单。它不调用 `ffmpeg`，不访问网络，不修改源文件，也不需要安装任何第三方库。

它和 Trending 上那些「本地视频编辑 Skill」的思路一致——**本地优先、机器可读、无需云端**。但它刻意做了差异化：

| 维度 | 常见本地视频 Skill | MediaProbe |
| --- | --- | --- |
| 定位 | 编辑器（改文件） | 探针（只读） |
| 外部依赖 | 依赖 ffmpeg 二进制 | **零依赖，纯标准库** |
| 输出 | 转码后的媒体 | **确定性 JSON 清单 + 审计发现** |
| 可复现性 | 受编码器版本影响 | **同字节 → 同清单** |
| 集成 | 需安装工具链 | `pip install` 或直接 `python -m` |

一句话概括：**它是媒体文件的 `file` 命令 + 结构化审计器，为 AI Agent 与自动化流水线设计。**

---

## ✨ 特性

- 🧩 **多格式支持** — MP4/MOV/M4A、Matroska/WebM、MP3（ID3v2/v1）、WAV、AVI、AIFF、FLAC，以及 PNG/JPEG/GIF/WebP 图片尺寸。
- 🧱 **纯标准库** — 仅用 `struct`、`hashlib`、`argparse` 等，运行时依赖数为 **0**。
- 🔒 **只读安全** — 不执行外部进程、不联网、不写源文件；适合处理不可信输入的自动化场景。
- 🎯 **确定性输出** — 键排序、字段固定、时长精确到毫秒；相同输入字节产生字节一致的 JSON。
- 🔍 **结构审计** — 检出 `moov` 非 faststart、RIFF 声明长度不符、ID3v1/v2 标签冲突、文件截断等 10+ 类问题，并给出可操作建议。
- 🤖 **Agent 友好** — 内置机器可读的 [工具契约](schemas/tool-contract.json) 与 [JSON Schema](schemas/manifest.schema.json)，即插即用。
- 🪶 **低内存** — 基于随机访问读取，不把整个媒体文件载入内存；SHA-256 流式计算。
- 🧪 **测试完备** — 23 个单元测试覆盖全部格式、确定性与 CLI 端到端，fixture 由代码合成，无需外部媒体文件。
- 🌍 **三语文档** — 简中 / 繁中 / English 母语级表达。

---

## 🚀 快速开始

### 安装

```bash
# 方式一：从源码安装（无需联网装依赖）
pip install .

# 方式二：直接运行，零安装
python -m mediaprobe --version

# 方式三：使用 zipapp 单文件包
python dist/mediaprobe-1.0.0.pyz inspect video.mp4
```

要求：Python 3.8 或更高版本。**没有 requirements.txt，因为真的没有依赖。**

### 30 秒上手

```bash
# 探查单个文件
python -m mediaprobe inspect video.mp4

# 美化输出
python -m mediaprobe inspect video.mp4 --pretty

# 只取某个字段
python -m mediaprobe inspect video.mp4 --field width
```

输出示例：

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

## 📖 使用指南

### CLI 命令

| 命令 | 作用 | 示例 |
| --- | --- | --- |
| `inspect` | 探查单个文件 | `mediaprobe inspect a.mp4 --pretty` |
| `batch` | 批量探查目录，输出 JSONL | `mediaprobe batch ./media --pattern "*.mp4" --recursive` |
| `audit` | 按级别过滤审计发现 | `mediaprobe audit a.mp4 --severity error` |
| `diff` | 对比两份清单 JSON | `mediaprobe diff a.json b.json` |
| `schema` | 输出 Manifest JSON Schema | `mediaprobe schema --pretty` |
| `contract` | 输出机器可读工具契约 | `mediaprobe contract` |

### 作为 Python 库集成

```python
from mediaprobe import probe_file, probe_bytes

# 探查磁盘文件
m = probe_file("video.mp4")
print(m.width, m.height, m.duration_ms, m.codec)

# 探查内存字节（适合 API / Agent 调用）
m = probe_bytes(open("video.mp4", "rb").read())
print(m.to_dict())          # 转成确定性字典
print(m.findings)           # 审计发现列表

# 跳过哈希以处理超大文件
m = probe_file("huge.mkv", compute_hash=False)
```

### Agent 集成示例

`contract` 命令输出的 JSON 描述了所有命令及参数，可直接作为工具声明注册到 Agent 框架：

```bash
mediaprobe contract > tool-contract.json
```

配合 `schemas/manifest.schema.json` 可对返回值做自动校验。`safety` 字段明确声明：`read_only: true`、`network_access: false`、`external_processes: false`。

### 审计级别

| 级别 | 含义 | 退出码 |
| --- | --- | --- |
| `error` | 文件结构性问题（缺少必要 box / 块） | `1` |
| `warn` | 可优化项（非 faststart、标签冲突、疑似截断） | `0` |
| `info` | 提示信息 | `0` |

`audit` 命令在发现 `error` 时返回退出码 `1`，方便在 CI 中做质量门禁。

### 支持格式明细

| 格式 | 解析内容 |
| --- | --- |
| MP4/MOV/M4A | ftyp 品牌、moov/mvhd 时长、trak/tkhd 宽高、mdhd、hdlr、stsd 编码 |
| MKV/WebM | DocType、TimecodeScale、Duration、视频/音频轨编码、采样率、声道 |
| MP3 | ID3v2.2/2.3/2.4 文本帧、ID3v1、MPEG 帧头码率/采样率/声道 |
| WAV | fmt 块、data 块、PCM/浮点/扩展格式 |
| AVI | avih 主头、帧数、宽高、时长 |
| AIFF/AIFC | COMM 块、80 位扩展精度采样率 |
| FLAC | STREAMINFO、采样率/声道/位深/总采样数 |
| 图片 | PNG IHDR、JPEG SOF、GIF 逻辑屏、WebP VP8X/VP8/VP8L |

---

## 💡 设计迭代

### 为什么自研而不是搬运

Trending 上的本地视频项目大多走「Skill 集合 + MCP Server + 调用 ffmpeg」路线，功能强但依赖重。账号中已有的工具箱也集中在文本/协议/取证方向，**媒体容器解析是一块空白**。

因此本项目选择了三点差异化：

1. **只读探针，而非编辑器** — 不做转码、不做剪辑，只回答「这个文件是什么」。
2. **零依赖，纯标准库** — 直接读二进制结构，摆脱 ffmpeg 版本差异与安装负担。
3. **确定性与可审计** — 输出可哈希比对，附带结构审计，适配 CI 与 Agent 流水线。

### 迭代记录

| 版本 | 变更 |
| --- | --- |
| v1.0.0 | 初始版本：8 类容器/图片解析、10+ 审计规则、6 个 CLI 子命令、三语文档、23 项测试 |

### 设计取舍

- **不解析全部 box/element** — 只提取对元数据有用的关键结构，速度优先，避免为无关字段引入复杂度。
- **MP3 时长为 CBR 估算** — 基于首个 MPEG 帧头的码率与音频数据字节数推算；VBR 文件会有偏差，故在 `container.mpeg` 中保留原始参数供调用方判断。
- **越界即报错** — `BinaryReader` 对任何越界读取抛 `ValueError`，宁可明确失败，也不产出静默错误的元数据。
- **无时间戳字段** — 清单中不含 `generated_at` 之类字段，确保可复现；文件时间信息应由调用方从文件系统获取。

---

## 📦 打包部署

### 一键打包

```bash
bash scripts/build.sh
```

产物位于 `dist/`：

- `mediaprobe-1.0.0-source.tar.gz` — 源码归档
- `mediaprobe-1.0.0.pyz` — zipapp 单文件可执行包（需 Python 3）
- `SHA256SUMS.txt` — 校验和清单

### 校验完整性

```bash
cd dist
sha256sum -c SHA256SUMS.txt
```

### 跨平台说明

纯 Python 实现，Windows / macOS / Linux 均可运行：

```bash
# Windows PowerShell
python -m mediaprobe inspect video.mp4

# macOS / Linux
python3 -m mediaprobe inspect video.mp4
```

### 发布

Release `v1.0.0` 附带上述全部产物与校验和。库形式使用时无需 Release，`pip install .` 即可。

---

## 🤝 贡献

欢迎提交 Issue 与 Pull Request。请先阅读 [贡献指南](CONTRIBUTING.md)。

- 🐛 报告缺陷：请附 Python 版本、复现步骤与 `inspect --pretty` 输出。
- ✨ 新增格式：需同步更新探测器、解析器、Schema 与三语 README，并补合成 fixture 测试。
- ⚖️ 提交信息遵循 Angular 规范：`feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `build:` / `chore:`。

---

## 📄 协议

本项目采用 [MIT License](LICENSE) 开源。

> 本项目仅解析文件结构，不解码、不转码、不分发任何媒体内容。使用者应自行确保对所处理文件拥有合法权利。
