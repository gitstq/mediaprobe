<div align="center">

# 🎬 MediaProbe

**零依賴 · 離線優先 · 確定性的媒體容器詮釋資料探查與稽核引擎**

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-green.svg)](https://www.python.org/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0-orange.svg)](pyproject.toml)

[简体中文](README.md) · [繁體中文](README.zh-TW.md) · [English](README.en.md)

</div>

---

## 🎉 介紹

有沒有過這樣的時刻：手上有一個影片檔，想知道它的解析度、時長、編碼格式，卻不想下載一個幾百 MB 的轉檔工具包，也不想讓檔案上傳到雲端？

**MediaProbe** 就是為此而生。它是一個**唯讀**的媒體詮釋資料結構化探查器——直接解析容器二進位結構，輸出一份可重現的 JSON 清單。它不呼叫 `ffmpeg`、不連網、不修改來源檔案，也不需要安裝任何第三方套件。

它與 Trending 上那些「本機影片編輯 Skill」的思路一致——**本機優先、機器可讀、無需雲端**。但它刻意做了差異化：

| 維度 | 常見本機影片 Skill | MediaProbe |
| --- | --- | --- |
| 定位 | 編輯器（改檔案） | 探針（唯讀） |
| 外部依賴 | 依賴 ffmpeg 執行檔 | **零依賴，純標準庫** |
| 輸出 | 轉檔後的媒體 | **確定性 JSON 清單 + 稽核發現** |
| 可重現性 | 受編碼器版本影響 | **同位元組 → 同清單** |
| 整合 | 需安裝工具鏈 | `pip install` 或直接 `python -m` |

一句話概括：**它是媒體檔案的 `file` 指令 + 結構化稽核器，專為 AI Agent 與自動化流程設計。**

---

## ✨ 特性

- 🧩 **多格式支援** — MP4/MOV/M4A、Matroska/WebM、MP3（ID3v2/v1）、WAV、AVI、AIFF、FLAC，以及 PNG/JPEG/GIF/WebP 圖片尺寸。
- 🧱 **純標準庫** — 僅用 `struct`、`hashlib`、`argparse` 等，執行期依賴數為 **0**。
- 🔒 **唯讀安全** — 不執行外部程式、不連網、不寫入來源檔；適合處理不可信輸入的自動化場景。
- 🎯 **確定性輸出** — 鍵排序、欄位固定、時長精確到毫秒；相同輸入位元組產生位元組一致的 JSON。
- 🔍 **結構稽核** — 偵測 `moov` 非 faststart、RIFF 宣告長度不符、ID3v1/v2 標籤衝突、檔案截斷等 10 多類問題，並給出可操作建議。
- 🤖 **Agent 友善** — 內建機器可讀的[工具契約](schemas/tool-contract.json)與 [JSON Schema](schemas/manifest.schema.json)，即插即用。
- 🪶 **低記憶體** — 基於隨機存取讀取，不將整個媒體載入記憶體；SHA-256 串流計算。
- 🧪 **測試完備** — 23 個單元測試涵蓋全部格式、確定性與 CLI 端到端，fixture 由程式合成，無需外部媒體檔。
- 🌍 **三語文件** — 簡中 / 繁中 / English 母語級表達。

---

## 🚀 快速開始

### 安裝

```bash
# 方式一：從原始碼安裝（無需連線裝依賴）
pip install .

# 方式二：直接執行，零安裝
python -m mediaprobe --version

# 方式三：使用 zipapp 單檔套件
python dist/mediaprobe-1.0.0.pyz inspect video.mp4
```

需求：Python 3.8 或以上。**沒有 requirements.txt，因為真的沒有依賴。**

### 30 秒上手

```bash
# 探查單一檔案
python -m mediaprobe inspect video.mp4

# 美化輸出
python -m mediaprobe inspect video.mp4 --pretty

# 只取某個欄位
python -m mediaprobe inspect video.mp4 --field width
```

輸出範例：

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

### CLI 指令

| 指令 | 作用 | 範例 |
| --- | --- | --- |
| `inspect` | 探查單一檔案 | `mediaprobe inspect a.mp4 --pretty` |
| `batch` | 批次探查目錄，輸出 JSONL | `mediaprobe batch ./media --pattern "*.mp4" --recursive` |
| `audit` | 依級別過濾稽核發現 | `mediaprobe audit a.mp4 --severity error` |
| `diff` | 比對兩份清單 JSON | `mediaprobe diff a.json b.json` |
| `schema` | 輸出 Manifest JSON Schema | `mediaprobe schema --pretty` |
| `contract` | 輸出機器可讀工具契約 | `mediaprobe contract` |

### 作為 Python 函式庫整合

```python
from mediaprobe import probe_file, probe_bytes

m = probe_file("video.mp4")
print(m.width, m.height, m.duration_ms, m.codec)

m = probe_bytes(open("video.mp4", "rb").read())   # 適用於 API / Agent
print(m.to_dict())
print(m.findings)

m = probe_file("huge.mkv", compute_hash=False)     # 跳過雜湊以處理超大檔
```

### Agent 整合範例

`contract` 指令輸出的 JSON 描述所有指令與參數，可直接作為工具宣告註冊到 Agent 框架：

```bash
mediaprobe contract > tool-contract.json
```

搭配 `schemas/manifest.schema.json` 可對回傳值做自動驗證。`safety` 欄位明確宣告：`read_only: true`、`network_access: false`、`external_processes: false`。

### 稽核級別

| 級別 | 含義 | 退出碼 |
| --- | --- | --- |
| `error` | 檔案結構性問題（缺少必要 box / chunk） | `1` |
| `warn` | 可優化項（非 faststart、標籤衝突、疑似截斷） | `0` |
| `info` | 提示資訊 | `0` |

`audit` 指令在發現 `error` 時回傳退出碼 `1`，方便在 CI 中做品質閘門。

### 支援格式明細

| 格式 | 解析內容 |
| --- | --- |
| MP4/MOV/M4A | ftyp 品牌、moov/mvhd 時長、trak/tkhd 寬高、mdhd、hdlr、stsd 編碼 |
| MKV/WebM | DocType、TimecodeScale、Duration、影像/音訊軌編碼、取樣率、聲道 |
| MP3 | ID3v2.2/2.3/2.4 文字訊框、ID3v1、MPEG 訊框頭碼率/取樣率/聲道 |
| WAV | fmt 區塊、data 區塊、PCM/浮點/擴充格式 |
| AVI | avih 主頭、幀數、寬高、時長 |
| AIFF/AIFC | COMM 區塊、80 位元延伸精度取樣率 |
| FLAC | STREAMINFO、取樣率/聲道/位深/總取樣數 |
| 圖片 | PNG IHDR、JPEG SOF、GIF 邏輯螢幕、WebP VP8X/VP8/VP8L |

---

## 💡 設計迭代

### 為什麼自研而不是搬運

Trending 上的本機影片專案大多走「Skill 集合 + MCP Server + 呼叫 ffmpeg」路線，功能強但依賴重。帳號中已有的工具箱也集中在文字/協定/取證方向，**媒體容器解析是一塊空白**。

因此本專案選擇三點差異化：

1. **唯讀探針，而非編輯器** — 不做轉檔、不做剪輯，只回答「這個檔案是什麼」。
2. **零依賴，純標準庫** — 直接讀二進位結構，擺脫 ffmpeg 版本差異與安裝負擔。
3. **確定性與可稽核** — 輸出可雜湊比對，附帶結構稽核，適合 CI 與 Agent 流程。

### 迭代紀錄

| 版本 | 變更 |
| --- | --- |
| v1.0.0 | 初始版本：8 類容器/圖片解析、10+ 稽核規則、6 個 CLI 子指令、三語文件、23 項測試 |

### 設計取捨

- **不解析全部 box/element** — 只提取對詮釋資料有用的關鍵結構，速度優先，避免為無關欄位引入複雜度。
- **MP3 時長為 CBR 估算** — 基於首個 MPEG 訊框頭的碼率與音訊資料位元組數推算；VBR 檔案會有偏差，故在 `container.mpeg` 保留原始參數供呼叫方判斷。
- **越界即報錯** — `BinaryReader` 對任何越界讀取拋出 `ValueError`，寧可明確失敗，也不產出靜默錯誤的詮釋資料。
- **無時間戳欄位** — 清單中不含 `generated_at` 之類欄位，確保可重現；檔案時間資訊應由呼叫方從檔案系統取得。

---

## 📦 打包部署

### 一鍵打包

```bash
bash scripts/build.sh
```

產物位於 `dist/`：

- `mediaprobe-1.0.0-source.tar.gz` — 原始碼封存
- `mediaprobe-1.0.0.pyz` — zipapp 單檔可執行套件（需 Python 3）
- `SHA256SUMS.txt` — 雜湊核對清單

### 驗證完整性

```bash
cd dist
sha256sum -c SHA256SUMS.txt
```

### 跨平台說明

純 Python 實作，Windows / macOS / Linux 皆可執行：

```bash
# Windows PowerShell
python -m mediaprobe inspect video.mp4

# macOS / Linux
python3 -m mediaprobe inspect video.mp4
```

### 發布

Release `v1.0.0` 附上上述全部產物與雜湊核對。以函式庫形式使用時無需 Release，`pip install .` 即可。

---

## 🤝 貢獻

歡迎提交 Issue 與 Pull Request。請先閱讀[貢獻指南](CONTRIBUTING.md)。

- 🐛 回報缺陷：請附 Python 版本、重現步驟與 `inspect --pretty` 輸出。
- ✨ 新增格式：需同步更新探測器、解析器、Schema 與三語 README，並補合成 fixture 測試。
- ⚖️ 提交訊息遵循 Angular 規範：`feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `build:` / `chore:`。

---

## 📄 授權

本專案採用 [MIT License](LICENSE) 開源。

> 本專案僅解析檔案結構，不解碼、不轉檔、不散播任何媒體內容。使用者應自行確保對所處理檔案擁有合法權利。
