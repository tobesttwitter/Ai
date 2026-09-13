from __future__ import annotations

import asyncio
import json
import os
import subprocess
import urllib.request
from pathlib import Path

from app.zerogpu import ZeroGPUWanProvider

SPACE = os.getenv("ZEROGPU_SPACE", "alexnasa/Wan2.2-Animate-ZEROGPU")
IMAGE_URL = "https://huggingface.co/spaces/alexnasa/Wan2.2-Animate-ZEROGPU/resolve/main/examples/man.png?download=true"
VIDEO_URL = "https://huggingface.co/spaces/alexnasa/Wan2.2-Animate-ZEROGPU/resolve/main/examples/paul.mp4?download=true"
ROOT = Path("artifacts")
IMAGE = ROOT / "man.png"
VIDEO = ROOT / "paul.mp4"
OUTPUT = ROOT / "wan-real-test.mp4"


def download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, path)
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"download failed or empty: {url}")


def probe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries",
            "format=format_name,duration,size:stream=codec_name,width,height,nb_frames",
            "-of", "json", str(path),
        ],
        check=True, capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    if not streams:
        raise RuntimeError(f"ffprobe found no video stream in {path}")
    duration = float(data.get("format", {}).get("duration") or 0)
    if duration <= 0:
        raise RuntimeError(f"video has no positive duration: {path}")
    frames = streams[0].get("nb_frames")
    if frames is not None and int(frames) <= 0:
        raise RuntimeError(f"video has no frames: {path}")
    print(f"{path}: {json.dumps(data, sort_keys=True)}")
    return data


def main() -> None:
    hf_token = os.getenv("HF_TOKEN")
    mode = os.getenv("ZEROGPU_MODE", "Pose Retarget")
    resolution = os.getenv("ZEROGPU_RESOLUTION", "Low Res")
    print(f"Space: {SPACE}")
    print("API: /animate_scene")
    print(f"Mode: {mode}")
    print(f"Resolution: {resolution}")
    print("Duration: 2 seconds")
    print(f"HF_TOKEN present: {bool(hf_token)}")
    print("Downloading public Space examples...")
    download(IMAGE_URL, IMAGE)
    download(VIDEO_URL, VIDEO)
    probe(VIDEO)

    provider = ZeroGPUWanProvider(
        space=SPACE,
        duration_seconds=2,
        mode=mode,
        resolution=resolution,
        timeout_seconds=float(os.getenv("ZEROGPU_TIMEOUT_SECONDS", "900")),
        hf_token=hf_token,
    )
    asyncio.run(provider.generate(IMAGE, VIDEO, OUTPUT))

    if not OUTPUT.is_file() or OUTPUT.stat().st_size == 0:
        raise RuntimeError("Wan returned no output")

    output_probe = probe(OUTPUT)
    output_duration = float(output_probe.get("format", {}).get("duration") or 0)
    if not 1.0 <= output_duration <= 4.5:
        raise RuntimeError(
            f"unexpected output duration {output_duration:.3f}s for a 2-second test"
        )
    if OUTPUT.read_bytes() == VIDEO.read_bytes():
        raise RuntimeError(
            "returned video is byte-identical to the reference input; refusing to call it a generated result"
        )
    if OUTPUT.stat().st_size <= 1000:
        raise RuntimeError("suspiciously small output; refusing to call it a real result")
    print(f"REAL WAN OUTPUT: {OUTPUT}")


if __name__ == "__main__":
    main()
