"""Integration tests for Modal SDK direct invocation (live Modal calls)."""
from __future__ import annotations

import base64
import os
from pathlib import Path

import pytest

# These tests need Modal SDK installed and a valid Modal token configured
skip_no_modal = pytest.mark.skipif(
    not os.getenv("MODAL_TOKEN_ID") and not os.getenv("MODAL_TOKEN_SECRET"),
    reason="Modal credentials not configured — set MODAL_TOKEN_ID/MODAL_TOKEN_SECRET in .env",
)

_EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _load_image_base64(name: str) -> str:
    path = _EXAMPLES_DIR / name
    if not path.exists():
        pytest.skip(f"Example image not found: {path}")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


@skip_no_modal
class TestModalDirectInvocation:
    """Live tests calling the deployed MiniCPM-V model via Modal SDK."""

    def test_no_image(self):
        """Call model.generate with a text-only prompt."""
        import modal

        model = modal.Cls.from_name("minicpm-vllm", "MiniCPMVLLM")()
        result = model.generate.remote(
            prompt="Hello, how are you?", image_base64=None
        )
        assert result is not None
        assert isinstance(result, str)

    def test_with_image(self):
        """Call model.generate with a base64 image."""
        import modal

        image_b64 = _load_image_base64("calendar.JPG")
        model = modal.Cls.from_name("minicpm-vllm", "MiniCPMVLLM")()
        result = model.generate.remote(
            prompt="Describe this image in detail, focusing on accessibility issues related to color contrast.",
            image_base64=image_b64,
        )
        assert result is not None
        assert isinstance(result, str)

    def test_with_image_debug_output(self):
        """Call model.generate and verify base64 payload size."""
        import modal

        with open(_EXAMPLES_DIR / "calendar.JPG", "rb") as f:
            image_data = f.read()
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        # Sanity-check the base64 payload
        assert len(image_b64) > 100
        assert image_b64.startswith("/9j/")  # JPEG magic bytes (base64 of 0xFF 0xD8)

        model = modal.Cls.from_name("minicpm-vllm", "MiniCPMVLLM")()
        result = model.generate.remote(
            prompt="Describe this image in detail, focusing on accessibility issues related to color contrast.",
            image_base64=image_b64,
        )
        assert result is not None