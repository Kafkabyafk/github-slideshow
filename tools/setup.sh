#!/usr/bin/env bash
# setup.sh — install the engines the suite needs, and fetch the Kokoro model.
# Re-runnable. Tested on Ubuntu (Claude Code web container) and macOS.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "== system deps (tesseract OCR, ffmpeg) =="
if command -v apt-get >/dev/null; then
  sudo apt-get install -y tesseract-ocr ffmpeg || echo "  (apt failed; install tesseract+ffmpeg manually)"
elif command -v brew >/dev/null; then
  brew install tesseract ffmpeg
fi

echo "== python deps =="
pip install pymupdf kokoro-onnx soundfile num2words >/dev/null
pip install num2words --no-deps >/dev/null 2>&1 || true   # docopt build can fail; deps not needed

echo "== Kokoro model (from GitHub release — HuggingFace not required) =="
mkdir -p "$HERE/models"
base="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
[ -f "$HERE/models/kokoro.int8.onnx" ] || curl -sSL -o "$HERE/models/kokoro.int8.onnx" "$base/kokoro-v1.0.int8.onnx"
[ -f "$HERE/models/voices-v1.0.bin" ]  || curl -sSL -o "$HERE/models/voices-v1.0.bin"  "$base/voices-v1.0.bin"
echo "models:"; ls -la "$HERE/models"
echo "== done =="
