#!/usr/bin/env bash
set -euo pipefail

ROOT="${KAGGLE_WORKING_DIR:-/kaggle/working}"
COMFY="${ROOT}/ComfyUI"

if [ ! -d "$COMFY" ]; then
  git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git "$COMFY"
fi

python -m pip install --upgrade pip
python -m pip install --no-cache-dir -r "$COMFY/requirements.txt"

mkdir -p "$COMFY/custom_nodes"
cd "$COMFY/custom_nodes"

if [ ! -d ComfyUI-KJNodes ]; then
  git clone --depth 1 https://github.com/kijai/ComfyUI-KJNodes.git
fi
if [ ! -d ComfyUI-comfyui_controlnet_aux ]; then
  git clone --depth 1 https://github.com/Fannovel16/comfyui_controlnet_aux.git ComfyUI-comfyui_controlnet_aux
fi
if [ ! -d ComfyUI-GGUF ]; then
  git clone --depth 1 https://github.com/city96/ComfyUI-GGUF.git
fi

python -m pip install --no-cache-dir -r "$COMFY/custom_nodes/ComfyUI-KJNodes/requirements.txt" || true
python -m pip install --no-cache-dir -r "$COMFY/custom_nodes/ComfyUI-comfyui_controlnet_aux/requirements.txt" || true
python -m pip install --no-cache-dir -r "$COMFY/custom_nodes/ComfyUI-GGUF/requirements.txt" || true

mkdir -p "$COMFY/models/diffusion_models" "$COMFY/models/text_encoders" "$COMFY/models/clip_vision" "$COMFY/models/clip_visions" "$COMFY/models/loras" "$COMFY/models/vae"

echo "ComfyUI installed at $COMFY"
