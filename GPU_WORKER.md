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
