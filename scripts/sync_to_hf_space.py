#!/usr/bin/env python3
"""Sync local repository to HuggingFace Space."""

import os
import sys

try:
    from huggingface_hub import HfApi
except ImportError:
    print("Error: huggingface_hub not installed. Run: pip install huggingface_hub")
    sys.exit(1)

REPO_ID = "build-small-hackathon/color-ux-access"
REPO_TYPE = "space"


def main() -> None:
    token = os.environ.get("HF_SPACES_TOKEN") or os.environ.get("HF_TOKEN")
    if not token:
        print("Error: HF_SPACES_TOKEN or HF_TOKEN environment variable not set")
        sys.exit(1)

    api = HfApi(token=token)

    ignore_patterns = [
        ".git/**",
        ".github/**",
        ".venv/**",
        "__pycache__/**",
        "*.pyc",
        ".DS_Store",
        ".qodo/**",
        ".idea/**",
        ".pytest_cache/**",
        "uv.lock",
    ]

    sha = os.environ.get("GITHUB_SHA", "manual")[:8]
    commit_message = f"Sync from GitHub {sha}"

    api.upload_folder(
        folder_path=".",
        repo_id=REPO_ID,
        repo_type=REPO_TYPE,
        ignore_patterns=ignore_patterns,
        commit_message=commit_message,
    )
    print(f"✓ Synced {REPO_ID} to Space")


if __name__ == "__main__":
    main()
