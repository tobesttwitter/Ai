# AI Movie Studio

Open-source foundation for a mobile-controlled AI movie pipeline. The phone is the UI; heavy inference is designed for a replaceable remote GPU worker.

## Status

**Implemented:** FastAPI API, persistent job records, safe uploads, mobile-first web/PWA UI, real asynchronous mock worker, playable MP4 mock output via FFmpeg, provider interfaces, ComfyUI HTTP client, CI tests.

**Partially implemented:** ComfyUI connectivity check/client and workflow contract.

**Not yet validated:** Production Wan 2.2 Animate inference, MuseTalk 1.5 inference, production FFmpeg assembly, and a real remote GPU worker.

## Architecture

Android browser -> mobile web UI -> FastAPI -> asynchronous JobManager -> provider abstractions -> remote GPU/ComfyUI.

Pipeline boundary: MotionGenerationProvider (Wan 2.2 Animate via ComfyUI), LipSyncProvider (MuseTalk 1.5), VideoProcessor (FFmpeg).

## Run locally

Python 3.11+ and FFmpeg are required for the playable mock.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://<computer-ip>:8000/web/ on Android when both devices can reach the server. Select an image, reference video and audio, then press Generate.

Run `pytest` and `python -m compileall app`. CI installs FFmpeg and runs the end-to-end API test.

## Environment

MOCK_GENERATION=true, STORAGE_ROOT=./storage, MAX_UPLOAD_MB=100, FFMPEG_BINARY=ffmpeg, COMFYUI_URL, COMFYUI_TIMEOUT_SECONDS and COMFYUI_POLL_SECONDS. No model weights or generated media belong in Git.

## Storage

storage/uploads stores source assets; storage/jobs stores durable job metadata; storage/outputs stores final files; storage/temporary stores intermediates. Job records survive process restart, but an in-flight task does not survive a process crash. A durable external queue/worker is planned.

## ComfyUI / Wan 2.2 Animate

app/comfyui.py provides health, upload, prompt submission, history polling and output retrieval against a remote ComfyUI API. workflows/comfyui/wan2.2-animate.json is a workflow contract/template, not a falsely claimed universal executable workflow. A production workflow must be exported and tested against the exact Wan checkpoint and custom-node set installed on the GPU worker. Start with short, low-resolution clips; actual VRAM depends on checkpoint, precision, resolution, workflow and node implementation.

## MuseTalk 1.5

MuseTalk remains a separate lip-sync provider so an existing video can later be processed without regenerating motion. Pin its upstream version and review current code, model-weight and dependency licenses before distribution.

## FFmpeg

The mock uses FFmpeg to create a deterministic 2-second H.264/AAC MP4, proving the output path and browser-compatible artifact are real. Production processing will use application-generated argument arrays only; never interpolate user input into shell commands.

## $0 GPU model

The core software requires no paid API or paid GPU service. Intended deployment: Android -> web app -> API/job manager -> replaceable GPU worker -> ComfyUI/Wan + MuseTalk + FFmpeg. Free GPU environments can disappear or time out and may have limited VRAM, disk and bandwidth. Treat workers as temporary infrastructure and do not promise unlimited free compute.

## Licensing audit

No proprietary AI API dependency is included. Framework/runtime dependencies are open-source packages. AI model licensing is tracked separately because open weights are not automatically equivalent to open-source software. Before commercial movie use, verify the exact Wan checkpoint, MuseTalk weights, ComfyUI version/custom nodes and auxiliary models, and record their licenses and commercial-use terms.

## Security

Uploads are restricted by extension, magic bytes and configurable size; filenames are generated server-side. Secrets remain in backend configuration. Public deployment still needs authentication, rate limiting, worker authentication, quotas, stronger media probing and isolation.

## Roadmap

Foundation, mobile UI/API and playable mock are complete. Remote ComfyUI client/health is complete; production workflow is pending. Wan inference, MuseTalk inference, production FFmpeg assembly, durable worker/queue and free-GPU deployment remain pending. Projects, scenes, characters, voices, timeline and long-form assembly come later.