# Deploying a controlled ZeroGPU Space

This repository cannot create or authenticate a Hugging Face Space on your behalf. The safest reproducible deployment is to duplicate the current upstream Wan Animate ZeroGPU Space from Hugging Face into an account you control.

Current upstream Space used for the adapter:

`alexnasa/Wan2.2-Animate-ZEROGPU`

## Steps

1. Duplicate the Space into your Hugging Face account.
2. Select ZeroGPU hardware in Space settings.
3. Keep the upstream Wan Animate application and model download logic intact.
4. Record the Space commit SHA used for validation.
5. Confirm the Space is running before configuring the AI API.
6. Set `MOTION_PROVIDER=zerogpu`.
7. Set `ZEROGPU_SPACE=<your-account>/<your-space>`.
8. Keep any HF token server-side as a Space/backend secret.

Do not expose the Space URL/token through the Android frontend.

## First real test

Use a 2-second reference video and a character image. The current public Space uses 2 seconds as its default and has a lower-duration fallback when quota is exhausted.

Run the test from the Space itself first. Only after a real MP4 is returned should the backend adapter be enabled.

## Important

ZeroGPU is an experimental free worker, not persistent infrastructure. Space sleep, quota exhaustion, queueing, model download time, and account limits are expected failure modes.
