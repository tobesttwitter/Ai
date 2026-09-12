# ZeroGPU Wan 2.2 Animate worker

This is the $0 experimental worker path for Wan 2.2 Animate.

## Current worker target

The repository can call the public Hugging Face Space:

`alexnasa/Wan2.2-Animate-ZEROGPU`

That Space is currently running on Hugging Face ZeroGPU and exposes the Wan Animate operation through Gradio. Its current implementation loads the official `Wan-AI/Wan2.2-Animate-14B` model, performs video preprocessing, calls the Wan Animate generator, and returns a real MP4. See the project source and current Space before relying on it for production.

This adapter deliberately does **not** duplicate the model, job manager, or storage system.

## API contract used by the backend

The Space's current `animate_scene` operation accepts:

1. input video
2. max duration (2–10 seconds)
3. reference image
4. mode

The provider uses:

`/animate_scene`

and defaults to Move/animation mode:

`Video → Ref Image`

The Space's own code maps this mode to pose-retargeting/animation behavior. The opposite `Video ← Ref Image` mode is character replacement.

## Configure

Install the optional dependency:

`pip install -e '.[test,zerogpu]'`

Then:

```
MOTION_PROVIDER=zerogpu
ZEROGPU_SPACE=alexnasa/Wan2.2-Animate-ZEROGPU
ZEROGPU_DURATION_SECONDS=2
ZEROGPU_TIMEOUT_SECONDS=900
```

An HF token is optional for a public Space. If one is required later, provide it only as a server-side secret through `HF_TOKEN`; never put it in frontend code or Git.

## $0 limitations

ZeroGPU is shared infrastructure. Free accounts currently receive 5 GPU-minutes/day, and the default `large` allocation is half an RTX PRO 6000 Blackwell (48 GB VRAM); `xlarge` is a full 96 GB allocation but has higher quota cost. Hosting your own ZeroGPU Space is also subject to Hugging Face account requirements.

The public Animate Space currently estimates roughly 120 seconds of GPU allocation for a 2-second request and 180 seconds for a 3–4 second request. Those are the worker's own estimates, not a guarantee. The free daily quota therefore makes short tests practical but not unlimited.

## Reproducible Space

The preferred route is to duplicate/fork the current public Wan Animate ZeroGPU Space into an account you control rather than copying an old implementation. Preserve its upstream Wan/model licenses and pin a known-good commit when possible.

The application provider remains independent of which Space is selected.

## Verification

A real test must prove all of the following:

- ZeroGPU allocates a GPU.
- Wan Animate model loads.
- the requested image and video are processed.
- the returned file is an MP4 with a video stream and non-zero duration.
- the output is not the original reference video.

The repository must never mark a ZeroGPU job successful merely because the Gradio request was accepted.
