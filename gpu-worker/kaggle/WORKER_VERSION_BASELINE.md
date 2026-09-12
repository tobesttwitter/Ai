# Worker version baseline

## Candidate baseline (not yet validated in this ChatGPT runtime)

A public Kaggle Wan2.2 Animate ComfyUI implementation reports this working baseline for constrained T4x2 experiments:

- Python 3.11.13
- CUDA 12.8
- PyTorch 2.9.0 + cu128
- NumPy < 2.0
- Kaggle 2 × T4, 16 GB VRAM each
- Q3_K_M Animate 14B GGUF for the low-VRAM ComfyUI path

Source implementation: https://github.com/kelvinweijun/wan-2.2-animate-comfyui-kaggle

This repository deliberately does not label that stack **validated by AI** until a real Kaggle run completes successfully. The setup script records the exact ComfyUI/custom-node SHAs from the actual worker so the first successful environment can be pinned here afterward.

## Why this matters

The official Wan Animate 14B checkpoint's memory footprint is too large for a single 16 GB T4. The community Kaggle implementation specifically uses a quantized Q3_K_M Animate checkpoint and reports T4x2 operation. That is a compatibility experiment, not a claim that the official FP8/BF16 checkpoint fits in one T4.

The official Wan Animate model card describes animation mode as generating a video of the reference character image that mimics motion from the input video. https://huggingface.co/Wan-AI/Wan2.2-Animate-14B

The model card currently lists the preprocessing checkpoint at about 4.17 GB and the SAM2 subdirectory at about 1.56 GB. https://huggingface.co/Wan-AI/Wan2.2-Animate-14B/tree/main/process_checkpoint
