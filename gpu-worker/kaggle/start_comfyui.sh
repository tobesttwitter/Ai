#!/usr/bin/env bash
set -euo pipefail
ROOT="${KAGGLE_WORKING_DIR:-/kaggle/working}"
COMFY="${ROOT}/ComfyUI"
exec python "$COMFY/main.py" --listen 0.0.0.0 --port 8188
