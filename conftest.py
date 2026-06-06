"""
Shared pytest fixtures for color-ux-access.
=============================================
All tests should import from here rather than doing sys.path gymnastics.

Fixture hierarchy
-----------------
img_factory      — PIL Image, no CVD simulation
cvd_img_factory  — Image + callable(cv_type) -> simulated PIL Image
mock_vlm_factory — Returns deterministic WCAG JSON (no API call)
browser_page     — Chromium page for screenshot capture tests
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import numpy as np
from PIL import Image

# Ensure project root is on path
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


# ── Image Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def img_factory():
    """Factory: makes random RGB PIL Images of a given size."""
    def _make(width: int = 640, height: int = 480, seed: int | None = None) -> Image.Image:
        if seed is not None:
            rng = np.random.default_rng(seed)
            arr = rng.integers(0, 255, (height, width, 3), dtype=np.uint8)
        else:
            arr = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        return Image.fromarray(arr)
    return _make


@pytest.fixture
def cvd_img_factory(img_factory):
    """
    Factory: makes PIL Image AND a simulate() callable.

    Usage:
        img, simulate = cvd_img_factory(100, 100)
        deut_img = simulate(img, 'deuteranopia')
    """
    from color_ux_access.cvd_sim import simulate_cvd

    def _make(width: int = 640, height: int = 480, seed: int = 42) -> tuple[Image.Image, callable]:
        img = img_factory(width, height, seed=seed)
        return img, lambda cv_type: simulate_cvd(img, cv_type)

    return _make


@pytest.fixture
def sample_button_panel(img_factory) -> Image.Image:
    """
    Synthetic button panel — green Confirm button (left), red Cancel button (right).
    Tests that CVD simulation makes the two buttons indistinguishable.
    """
    arr = np.zeros((120, 300, 3), dtype=np.uint8)
    arr[:, :] = [240, 240, 240]          # gray background
    arr[20:100, 20:145] = [34, 139, 34]  # green confirm (left half)
    arr[20:100, 155:280] = [205, 92, 92] # red cancel (right half)
    return Image.fromarray(arr)


# ── VLM Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_vlm_factory():
    """
    Returns a deterministic WCAG JSON response for testing without API calls.
    Use as a patch target for analyze_with_vlm() in app_space.py.
    """
    def make_findings(count: int = 2) -> list[dict]:
        return [
            {
                "type": "Low Contrast",
                "wcag_criterion": "1.4.3",
                "description": "Button text contrast ratio is 2.8:1 — below the 4.5:1 AA minimum",
                "severity": "serious",
                "location": "Submit button, top-right",
            },
            {
                "type": "Color Only Information",
                "wcag_criterion": "1.4.1",
                "description": "Form validation relies on red/green borders with no secondary indicator",
                "severity": "critical",
                "location": "Form section, center-left",
            },
        ][:count]

    def mock_vlm_result(passes: bool = False, findings_count: int = 1) -> dict:
        findings = make_findings(findings_count) if not passes else []
        return {
            "findings": findings,
            "summary": f"{findings_count} critical issue(s) found" if findings else "No issues found",
            "passes": passes,
        }

    return mock_vlm_result


# ── CVD Gallery Fixture ───────────────────────────────────────────────────────

@pytest.fixture
def ten_type_gallery() -> list[str]:
    """
    The 10 canonical CVD type names the UI gallery must produce.
    """
    return [
        'deuteranopia',
        'protanopia',
        'tritanopia',
        'achromatopsia',
        'deuteranomaly',
        'protanomaly',
        'tritanomaly',
    ]


# ── Token Fixture ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def hf_token():
    """
    Read HF_TOKEN from environment or ~/.cache/huggingface/token.

    Order: HF_TOKEN env var → HF_API_TOKEN env var → token file.
    Skips all E2E tests if no token is available.
    Matches how color_ux_access.modal_app and vlm.vlm_inference resolve tokens.
    """
    token = os.environ.get("HF_TOKEN") or os.environ.get("HF_API_TOKEN")
    if token is None:
        token_file = os.path.expanduser("~/.cache/huggingface/token")
        if not os.path.exists(token_file):
            pytest.skip("HF_TOKEN not found (no env var and no ~/.cache/huggingface/token)")
        with open(token_file) as f:
            token = f.read().strip()
    if not token or len(token) < 10:
        pytest.skip("HF_TOKEN is empty or too short to be valid")
    return token


# Playwright fixtures removed — HF Space containers cannot run a browser.
# The capture module (color_ux_access.capture.take_screenshot) uses playwright
# locally for screenshots, but tests use source inspection only."