#!/usr/bin/env bash
# MediaProbe 一键打包脚本（零外部依赖，仅用 Python 标准库）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERSION="1.0.0"
DIST="$ROOT/dist"
rm -rf "$DIST"
mkdir -p "$DIST"

echo "[1/4] 运行全量单元测试..."
PYTHONPATH="$ROOT" python3 -m unittest discover -s tests

echo "[2/4] 生成源码归档..."
tar --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='dist' \
    -czf "$DIST/mediaprobe-${VERSION}-source.tar.gz" \
    mediaprobe tests schemas scripts README.md README.zh-TW.md README.en.md \
    LICENSE CONTRIBUTING.md pyproject.toml .gitignore

echo "[3/4] 生成 zipapp 可执行包..."
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -r mediaprobe "$STAGE/mediaprobe"
find "$STAGE" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
cat > "$STAGE/__main__.py" <<'PYEOF'
from mediaprobe.cli import main
raise SystemExit(main())
PYEOF
python3 -m zipapp "$STAGE" \
    --python "/usr/bin/env python3" \
    --output "$DIST/mediaprobe-${VERSION}.pyz"

echo "[4/4] 生成校验和..."
cd "$DIST"
sha256sum * > SHA256SUMS.txt
cat SHA256SUMS.txt

echo "完成：产物位于 $DIST"
