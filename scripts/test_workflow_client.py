import os
import sys
from pathlib import Path

from app.github_workflow_client import GitHubWorkflowClient


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: python scripts/test_workflow_client.py SOURCE_IMAGE TARGET_VIDEO AUDIO_FILE")
        return 2

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPO")
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 2
    if not repo:
        print("GITHUB_REPO is required", file=sys.stderr)
        return 2

    try:
        output = GitHubWorkflowClient(repo, "face-swap.yml", token).submit(
            Path(sys.argv[1]),
            Path(sys.argv[2]),
            Path(sys.argv[3]),
            Path("output"),
        )
        print(output)
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
