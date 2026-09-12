# Remote GPU worker

The application does not require a local GPU. Set MOCK_GENERATION=true for development. For real inference, run ComfyUI on a separate GPU machine and set MOCK_GENERATION=false and COMFYUI_URL.

No paid provider is required by this repository.

## Worker checklist

- Current ComfyUI installed.
- Current official Wan 2.2 Animate template imported.
- Required custom nodes installed.
- Wan checkpoint and auxiliary model weights downloaded from official sources.
- FFmpeg installed on the worker if the workflow needs it.
- API endpoint reachable from the application.
- Worker authentication/firewall configured appropriately.

Free GPU platforms are temporary infrastructure: sessions can expire, GPUs can be unavailable, storage can be ephemeral, and large model downloads can consume most of a session. Do not expose an unauthenticated ComfyUI endpoint to the public internet.

## First real test

Use workflows/comfyui/wan2.2-animate.ui.json, configure Move mode, export API format, point COMFYUI_WAN_WORKFLOW_API_PATH at it, then set COMFYUI_URL. Start with a 5-second reference clip and low resolution. Run the backend and submit a job from /web/.

The application will not manufacture a success when the worker is absent.


## Official Wan 2.2 Animate requirements

Current ComfyUI documentation describes Mix and Move modes; **Move** is the required mode for this project. It uses movement from the input video to animate the reference character. The documented complete workflow requires ComfyUI-KJNodes and ComfyUI-comfyui_controlnet_aux. It currently lists Animate-14B FP8/BF16, CLIP Vision H, LightX2V I2V LoRA, Wan 2.1 VAE, and UMT5 XXL FP8 assets. See the official documentation: https://docs.comfy.org/tutorials/video/wan/wan2-2-animate

Wan2.2's official repository states Apache 2.0 licensing for the models in that repository: https://github.com/Wan-Video/Wan2.2. Third-party converted weights and custom nodes retain their own licenses and must be reviewed separately.

The checked-in UI workflow is not silently treated as API JSON. On the exact worker, switch to Move mode and use ComfyUI's **Save (API Format)** to produce the graph used by the backend. Start with a short clip and conservative dimensions; ComfyUI recommends dimensions compatible with the WanAnimateToVideo constraints and notes VRAM considerations.
