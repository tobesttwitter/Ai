# Model manifest

Official/current ComfyUI Wan2.2 Animate documentation lists these assets:

- Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors
- wan2.2_animate_14B_bf16.safetensors
- clip_vision_h.safetensors
- lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors
- wan_2.1_vae.safetensors
- umt5_xxl_fp8_e4m3fn_scaled.safetensors

Source: https://docs.comfy.org/tutorials/video/wan/wan2-2-animate

For a 16 GB T4, the official 18.4 GB FP8 Animate checkpoint cannot fit wholly in VRAM. A quantized GGUF is therefore the practical low-memory experiment.

Kijai's current GGUF repository contains a Q4_K_M Animate 14B file around 12.6 GB:
https://huggingface.co/Kijai/WanVideo_comfy_GGUF/tree/main/Wan22Animate

QuantStack also publishes Animate GGUF variants from about 6.46 GB (Q2_K) through 18.7 GB (Q8_0):
https://huggingface.co/QuantStack/Wan2.2-Animate-14B-GGUF

Use Q4_K_M first. If memory still fails, test Q3/Q2 only as a diagnostic; quality and speed may degrade.

Licensing:
- Wan2.2 official models: Apache-2.0 according to the upstream repository.
- Kijai WanVideo_comfy_GGUF: Apache-2.0 repository license.
- QuantStack Animate GGUF: Apache-2.0, with explicit notice that upstream licensing restrictions remain applicable.

Do not describe quantized third-party conversions as the official upstream checkpoint.
