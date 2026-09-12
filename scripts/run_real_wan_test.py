from __future__ import annotations

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


def probe(path: Path) -> None:
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "format=format_name,duration,size",
            "-show_entries", "stream=codec_name,width,height,nb_frames",
            "-of", "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    print(result.stdout)


def main() -> None:
    print(f"Space: {SPACE}")
    print("Mode: Video → Ref Image")
    print("Duration: 2 seconds")
    print("Downloading public Space examples...")
    download(IMAGE_URL, IMAGE)
    download(VIDEO_URL, VIDEO)
    probe(VIDEO)

    provider = ZeroGPUWanProvider(
        space=SPACE,
        duration_seconds=2,
        mode="Video → Ref Image",
        timeout_seconds=float(os.getenv("ZEROGPU_TIMEOUT_SECONDS", "900")),
        hf_token=os.getenv("HF_TOKEN"),
    )
    import asyncio
    asyncio.run(provider.generate(IMAGE, VIDEO, OUTPUT))

    if not OUTPUT.is_file() or OUTPUT.stat().st_size == 0:
        raise RuntimeError("Wan returned no output")
    probe(OUTPUT)

    if OUTPUT.stat().st_size <= 1000:
        raise RuntimeError("Suspiciously small output; refusing to call it a real result")

    print(f"REAL WAN OUTPUT: {OUTPUT}")


if __name__ == "__main__":
    main()
