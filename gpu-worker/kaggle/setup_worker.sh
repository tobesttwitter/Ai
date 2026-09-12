#!/usr/bin/env bash
set -euo pipefail

ROOT="${KAGGLE_WORKING_DIR:-/kaggle/working}"
COMFY="${ROOT}/ComfyUI"
export PIP_CONSTRAINT="${ROOT}/constraints.txt"

echo 'numpy<2.0' > "${ROOT}/constraints.txt"

if [ ! -d "$COMFY" ]; then
  git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git "$COMFY"
fi

python -m pip install --upgrade pip
python -m pip install --no-cache-dir -r "$COMFY/requirements.txt"

mkdir -p "$COMFY/custom_nodes"
cd "$COMFY/custom_nodes"

declare -A REPOS=(
  [ComfyUI-GGUF]=https://github.com/city96/ComfyUI-GGUF.git
  [ComfyUI-WanVideoWrapper]=https://github.com/kijai/ComfyUI-WanVideoWrapper.git
  [ComfyUI-KJNodes]=https://github.com/kijai/ComfyUI-KJNodes.git
  [comfyui_controlnet_aux]=https://github.com/Fannovel16/comfyui_controlnet_aux.git
  [ComfyUI-VideoHelperSuite]=https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
  [ComfyUI-segment-anything-2]=https://github.com/kijai/ComfyUI-segment-anything-2.git
  [ComfyUI-Advanced-ControlNet]=https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet.git
  [comfyui-tooling-nodes]=https://github.com/Acly/comfyui-tooling-nodes.git
  [ComfyUI_essentials]=https://github.com/cubiq/ComfyUI_essentials.git
  [ComfyUI-WanAnimatePreprocess]=https://github.com/kijai/ComfyUI-WanAnimatePreprocess.git
  [rgthree-comfy]=https://github.com/rgthree/rgthree-comfy.git
)

for name in "${!REPOS[@]}"; do
  if [ ! -d "$name" ]; then git clone --depth 1 "${REPOS[$name]}" "$name"; fi
  if [ -f "$name/requirements.txt" ]; then
    python -m pip install --no-cache-dir -r "$name/requirements.txt" || true
  fi
done

python -m pip install --no-cache-dir onnxruntime-gpu mediapipe huggingface_hub

mkdir -p "$COMFY/models/diffusion_models" "$COMFY/models/unet" "$COMFY/models/text_encoders" "$COMFY/models/clip_vision" "$COMFY/models/loras" "$COMFY/models/vae" "$COMFY/models/detection"

echo "ComfyUI worker prepared at $COMFY"
echo "Record exact git SHAs before the first successful inference:"
for repo in "$COMFY" "$COMFY"/custom_nodes/*; do
  if [ -d "$repo/.git" ]; then
    printf '%s ' "$repo"
    git -C "$repo" rev-parse HEAD
  fi
done
