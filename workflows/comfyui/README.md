# Wan 2.2 Animate worker workflow

The current official ComfyUI template is checked in as wan2.2-animate.ui.json. It is intentionally retained as the UI workflow because ComfyUI's API JSON is generated from the exact installed workflow/node versions.

## Produce the executable API workflow

1. Install a current ComfyUI release on the GPU worker.
2. Install the custom nodes named by the official template.
3. Open wan2.2-animate.ui.json in ComfyUI.
4. Configure the workflow for Move mode. The official template notes that Move mode transfers pose/motion and requires disconnecting the background-video and character-mask inputs from WanAnimateToVideo.
5. Set a short reference clip and low resolution for the first test.
6. Use ComfyUI's Save (API Format) operation and save the result as wan2.2-animate.api.json.
7. Set COMFYUI_WAN_WORKFLOW_API_PATH to that file.
8. Verify the node IDs/fields configured by COMFYUI_WAN_IMAGE_NODE, COMFYUI_WAN_IMAGE_FIELD, COMFYUI_WAN_VIDEO_NODE, and COMFYUI_WAN_VIDEO_FIELD.

The provider deliberately rejects a UI-format JSON file rather than silently sending it to /prompt.

## Worker resources

The official template identifies WanAnimateToVideo, LoadVideo, CreateVideo, SAM2 segmentation and pose/control preprocessing components. Exact model filenames and VRAM requirements depend on the current template and installed checkpoint/configuration. Do not copy model weights into this repository.

## API execution

The backend uploads the user's image and reference video to the ComfyUI input area, substitutes the configured input node values, submits the API-format graph to /prompt, polls /history/{prompt_id}, then downloads the first returned video from /view.

## First validation

Use a 5-second reference video and conservative resolution. A successful validation must produce a real video from the Wan workflow. The backend reports workflow rejection, missing nodes/models, worker disconnection, timeout, or missing output rather than claiming success.

## Licensing

The workflow configuration, model code, checkpoints, custom nodes and auxiliary weights have separate licensing terms. Review the exact versions installed on the worker before commercial use.
