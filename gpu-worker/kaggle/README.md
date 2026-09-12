# Kaggle free GPU worker — Wan 2.2 Animate

This is the primary $0 test target for the real Wan worker.

Kaggle currently documents free GPU notebook access with a weekly quota; current hardware guidance says T4x2 remains available, with two 16 GB T4 GPUs. GPU access requires account/phone verification, and availability/quota can vary.

Sources:
- https://www.kaggle.com/product-announcements/735239
- https://www.kaggle.com/docs/efficient-gpu-usage

## Why Kaggle

It is currently the strongest legitimate $0 candidate because it provides CUDA GPUs, internet-enabled notebooks, and enough aggregate GPU memory to attempt constrained Wan Animate configurations. Community work specifically demonstrates Wan 2.2 Animate on Kaggle T4/T4x2, including GGUF variants.

This repository does not claim that every T4 configuration can run the full official FP8/BF16 workflow. The first attempt uses a quantized Animate checkpoint when necessary and records the actual result.

## Start

1. Open the notebook in gpu-worker/kaggle/wan2.2-animate-comfyui.ipynb.
2. Enable Internet.
3. Select GPU T4 x2 if available.
4. Run cells top-to-bottom.
5. Wait for the readiness cell to print the ComfyUI endpoint.
6. Set COMFYUI_URL in the AI application's backend to that endpoint.
7. Export the exact Move workflow from this worker using ComfyUI's Save (API Format).
8. Put that API JSON into workflows/comfyui/wan2.2-animate.api.json or configure COMFYUI_WAN_WORKFLOW_API_PATH.
9. Run the repository's opt-in integration test.

A real generation must produce an actual Wan video; a worker failure is never treated as success.

## Model strategy

The official ComfyUI workflow lists the 14B Animate FP8/BF16 model plus CLIP Vision H, LightX2V LoRA, Wan VAE and UMT5:
https://docs.comfy.org/tutorials/video/wan/wan2-2-animate

For constrained T4 memory, a GGUF conversion is an optional compatibility optimization. Quantized files retain the upstream model's licensing restrictions.

No model weights are committed to this repository.

## Security

A temporary tunnel exposes the ComfyUI port. Treat the URL as sensitive and close the notebook when finished. Do not expose an unauthenticated long-lived ComfyUI server. The application should eventually add worker authentication before public deployment.
