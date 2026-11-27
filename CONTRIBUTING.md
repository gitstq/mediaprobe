# 贡献指南 / Contributing

感谢你考虑为 MediaProbe 做贡献。本项目保持**零运行时依赖**，请在贡献时遵守这一原则。

## 开发环境

```bash
git clone https://github.com/gitstq/mediaprobe.git
cd mediaprobe
python3 -m unittest discover -s tests -v
```

无需 `pip install` 任何运行时依赖；Python 3.8+ 即可。

## 提交规范（Angular Convention）

提交信息必须使用以下前缀之一：

| 前缀 | 用途 |
| --- | --- |
| `feat:` | 新功能 |
| `fix:` | 缺陷修复 |
| `docs:` | 文档变更 |
| `refactor:` | 重构（不改变行为） |
| `test:` | 测试相关 |
| `build:` | 构建/打包相关 |
| `chore:` | 其他杂项 |

示例：`feat: add Matroska chapter parsing`

## 代码要求

1. 所有新解析器必须提供合成二进制 fixture 的单元测试，禁止依赖外部媒体文件或 ffmpeg。
2. 所有读取必须经 `BinaryReader`，并对越界做防御性处理。
3. 输出字段顺序固定，保证相同输入产生字节一致的 JSON。
4. 禁止引入第三方运行时依赖。若确有必要，需先开 Issue 讨论。
5. 新增格式需在 `mediaprobe/detect.py`、`mediaprobe/parsers/__init__.py`、`schemas/manifest.schema.json` 与三份 README 中同步登记。

## 报告问题

请附：Python 版本、复现步骤、文件格式、`mediaprobe inspect --pretty` 输出。

## 行为准则

友善、尊重、就事论事。禁止提交任何可能侵犯版权或包含恶意代码的材料。
