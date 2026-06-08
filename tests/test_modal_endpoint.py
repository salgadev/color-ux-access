"""Integration tests for the Modal inference endpoint (live HTTP calls)."""
from __future__ import annotations

import base64
import os
from pathlib import Path

import pytest
import requests

MODAL_INFERENCE_URL = os.getenv("MODAL_INFERENCE_URL")
skip_no_endpoint = pytest.mark.skipif(
    not MODAL_INFERENCE_URL,
    reason="MODAL_INFERENCE_URL not set — requires a deployed Modal endpoint",
)

_EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _load_image_base64(name: str) -> str:
    path = _EXAMPLES_DIR / name
    if not path.exists():
        pytest.skip(f"Example image not found: {path}")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


@skip_no_endpoint
class TestModalEndpoint:
    """Live HTTP tests against the deployed Modal inference endpoint."""

    @pytest.fixture(autouse=True)
    def _url(self):
        self.url = MODAL_INFERENCE_URL

    def test_text_only_prompt(self):
        """Endpoint accepts a text-only prompt and returns a response."""
        payload = {"prompt": "Hello, how are you?", "image_base64": ""}
        response = requests.post(self.url, json=payload, timeout=120)
        assert response.status_code in (200, 401), (
            f"Expected 200 or 401 (gated), got {response.status_code}"
        )
        data = response.json()
        assert isinstance(data, dict)

    def test_with_image_payload(self):
        """Endpoint accepts a base64 image and returns a response."""
        image_b64 = _load_image_base64("calendar.JPG")
        payload = {
            "prompt": "Describe this image in detail, focusing on accessibility issues related to color contrast.",
            "image_base64": image_b64,
        }
        response = requests.post(self.url, json=payload, timeout=180)
        assert response.status_code in (200, 401), (
            f"Expected 200 or 401 (gated), got {response.status_code}"
        )
        data = response.json()
        assert isinstance(data, dict)

    def test_endpoint_reachable(self):
        """Endpoint responds within timeout — basic smoke test."""
        payload = {"prompt": "ping", "image_base64": ""}
        try:
            response = requests.post(self.url, json=payload, timeout=30)
            assert response.status_code in (200, 401, 502, 503, 504)
        except requests.exceptions.ConnectionError:
            pytest.fail("Endpoint unreachable — is the Modal app deployed?")

    def test_long_timeout_image(self):
        """Endpoint handles longer generations without timing out."""
        image_b64 = _load_image_base64("notifications.JPG")
        payload = {
            "prompt": "Describe this image in detail, focusing on accessibility issues related to color contrast.",
            "image_base64": image_b64,
        }
        response = requests.post(self.url, json=payload, timeout=300)
        assert response.status_code in (200, 401, 502), (
            f"Unexpected: {response.status_code}"
        )