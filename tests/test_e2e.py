"""
End-to-End Tests — tests/test_e2e.py
=====================================
Tests the full local pipeline with real Modal/HF Router inference.

Prerequisites:
  - HF_TOKEN must be available (read from ~/.cache/huggingface/token)
  - If not available, tests skip gracefully with SKIP message

Run locally (requires token):
  pytest tests/test_e2e.py -v -s

Run with mocked inference (CI/unsafe token):
  HF_E2E_MOCK=1 pytest tests/test_e2e.py -v
"""
from __future__ import annotations

import os
import io
import sys
import json

import pytest
import numpy as np
from PIL import Image

# Ensure project root is on path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


# ── Token Fixture ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def hf_token():
    """
    Read HF_TOKEN from ~/.cache/huggingface/token.
    Skip all E2E tests if token is not available.
    """
    token_file = os.path.expanduser("~/.cache/huggingface/token")
    if not os.path.exists(token_file):
        pytest.skip("HF_TOKEN not found at ~/.cache/huggingface/token")
    with open(token_file) as f:
        token = f.read().strip()
    if not token or len(token) < 10:
        pytest.skip("HF_TOKEN file is empty or invalid")
    return token


@pytest.fixture(scope="module")
def env_with_token(hf_token):
    """Set HF_TOKEN in os.environ for the test module."""
    old = os.environ.get("HF_TOKEN")
    os.environ["HF_TOKEN"] = hf_token
    yield hf_token
    if old is not None:
        os.environ["HF_TOKEN"] = old
    else:
        os.environ.pop("HF_TOKEN", None)


# ── CVD Test Image Fixtures ────────────────────────────────────────────────────

@pytest.fixture
def red_green_button_panel():
    """
    Synthetic button panel — green Confirm button (left), red Cancel button (right).
    Real WCAG 1.4.1 failure: color is the ONLY means of distinguishing actions.
    Both buttons are #34C759 (green) and #CD5C5C (red) on a gray background.
    Under deuteranopia simulation, these two colors become nearly identical.
    """
    arr = np.zeros((120, 300, 3), dtype=np.uint8)
    arr[:, :] = [240, 240, 240]          # gray background (#F0F0F0)
    arr[20:100, 20:145] = [52, 199, 89]  # green confirm (#34C539)
    arr[20:100, 155:280] = [205, 92, 92] # red cancel (#CD5C5C)
    return Image.fromarray(arr)


@pytest.fixture
def low_contrast_text_panel():
    """
    Synthetic text panel — gray text on gray background.
    Real WCAG 1.4.3 failure: contrast ratio ~2.0:1, far below 4.5:1 AA minimum.
    """
    arr = np.full((100, 400, 3), [204, 204, 204], dtype=np.uint8)  # light gray bg
    # Draw "SUBMIT" text area in slightly darker gray (same color, indistinguishable)
    arr[35:65, 150:250] = [187, 187, 187]  # barely darker gray text
    return Image.fromarray(arr)


# ── E2E Tests ──────────────────────────────────────────────────────────────────

def test_cvd_simulation_makes_buttons_indistinguishable(env_with_token, red_green_button_panel):
    """
    Verify CVD simulation actually works — green and red buttons become
    visually similar under deuteranopia (real-world WCAG 1.4.1 failure scenario).

    This validates the CVD simulation pipeline (no VLM needed).
    """
    from color_ux_access.cvd_sim import simulate_cvd

    img = red_green_button_panel
    orig_arr = np.asarray(img.convert('RGB'), dtype=np.float32)

    # Deuteranopia simulation
    deut_img = simulate_cvd(img, 'deuteranopia')
    deut_arr = np.asarray(deut_img.convert('RGB'), dtype=np.float32)

    # Extract button pixel regions
    green_region = orig_arr[20:100, 20:145]
    red_region = orig_arr[20:100, 155:280]

    deut_green = deut_arr[20:100, 20:145]
    deut_red = deut_arr[20:100, 155:280]

    # Original: green and red should be clearly different
    orig_diff = np.abs(green_region.mean(axis=(0,1)) - red_region.mean(axis=(0,1)))
    assert orig_diff.sum() > 50, f"Original buttons should be clearly different, diff={orig_diff}"

    # Under deuteranopia: they should become much more similar
    deut_diff = np.abs(deut_green.mean(axis=(0,1)) - deut_red.mean(axis=(0,1)))
    similarity_ratio = deut_diff.sum() / (orig_diff.sum() + 1e-6)

    assert similarity_ratio < 0.4, (
        f"Under deuteranopia, buttons should become much more similar. "
        f"Orig diff={orig_diff.sum():.1f}, Deut diff={deut_diff.sum():.1f}, "
        f"ratio={similarity_ratio:.2f} (should be < 0.4)"
    )


def test_cvd_gallery_produces_10_variants(env_with_token, red_green_button_panel):
    """Verify the CVD gallery produces exactly 10 variants from real image."""
    from app_space import generate_cvd_gallery

    gallery = generate_cvd_gallery(red_green_button_panel)

    assert isinstance(gallery, list), f"gallery must be list, got {type(gallery)}"
    assert len(gallery) == 10, f"Expected 10 CVD variants, got {len(gallery)}"

    for i, (img, label) in enumerate(gallery):
        assert isinstance(img, Image.Image), f"item[{i}][0] must be Image"
        assert isinstance(label, str), f"item[{i}][1] must be str"
        assert img.size == red_green_button_panel.size, f"item[{i}] size mismatch"


def test_analyze_with_vlm_produces_wcag_json(env_with_token, red_green_button_panel):
    """
    E2E test: analyze_with_vlm() with a real synthetic image.
    Verifies:
      - HF_TOKEN is valid and HF Router API is reachable
      - VLM returns parseable JSON
      - JSON has expected WCAG structure (findings, passes, summary)
      - Findings include WCAG criterion references

    This is the core E2E test — it exercises the real Modal inference path
    via HF Router (the same path the deployed HF Space uses).
    """
    from app_space import analyze_with_vlm

    # Convert image to PNG bytes
    buf = io.BytesIO()
    red_green_button_panel.save(buf, format='PNG')
    image_bytes = buf.getvalue()

    # Call the real VLM inference (hits HF Router → Modal → aya-vision-32b)
    result = analyze_with_vlm(image_bytes, model="aya-vision-32b")

    # Must be a dict (not an error string or None)
    assert isinstance(result, dict), f"VLM result must be dict, got {type(result)}: {result}"

    # Must not be an error response
    if 'error' in result:
        pytest.fail(f"VLM returned error: {result['error']}")

    # Validate WCAG JSON structure
    assert 'findings' in result, f"WCAG JSON missing 'findings' key: {result}"
    assert 'passes' in result, f"WCAG JSON missing 'passes' key: {result}"
    assert 'summary' in result, f"WCAG JSON missing 'summary' key: {result}"

    assert isinstance(result['findings'], list), f"'findings' must be list, got {type(result['findings'])}"

    # If findings are present, each must have WCAG criterion and description
    for i, finding in enumerate(result['findings']):
        assert 'wcag_criterion' in finding, f"Finding {i} missing wcag_criterion: {finding}"
        assert 'description' in finding, f"Finding {i} missing description: {finding}"
        # WCAG criterion must be one of the known standards
        known_wcag = {'1.1.1', '1.4.1', '1.4.3', '1.4.11'}
        assert finding['wcag_criterion'] in known_wcag, (
            f"Finding {i} has unknown WCAG criterion '{finding['wcag_criterion']}'"
        )

    print(f"\nVLM E2E result: passes={result['passes']}, findings_count={len(result['findings'])}")
    print(f"Summary: {result['summary'][:120]}")
    if result['findings']:
        print(f"First finding: {result['findings'][0]['type']} ({result['findings'][0]['wcag_criterion']})")


def test_run_analysis_full_pipeline(env_with_token, red_green_button_panel):
    """
    E2E test: run_analysis() — the full Gradio pipeline function.
    Takes image bytes → CVD gallery + WCAG report.

    Verifies the complete pipeline that Gradio's submit_btn calls.
    """
    from app_space import run_analysis

    buf = io.BytesIO()
    red_green_button_panel.save(buf, format='PNG')
    image_bytes = buf.getvalue()

    original, gallery, report_md = run_analysis(image_bytes, model="aya-vision-32b")

    # Original image must be returned
    assert original is not None, "Original image must not be None"
    assert isinstance(original, Image.Image), f"Original must be PIL Image, got {type(original)}"

    # Gallery must have 10 items
    assert isinstance(gallery, list), f"Gallery must be list, got {type(gallery)}"
    assert len(gallery) == 10, f"Gallery must have 10 items, got {len(gallery)}"

    # Report must be non-empty markdown
    assert isinstance(report_md, str), f"Report must be str, got {type(report_md)}"
    assert len(report_md) > 20, f"Report too short: {report_md[:100]}"
    assert 'WCAG' in report_md or '✅' in report_md or '❌' in report_md, (
        f"Report should contain WCAG findings or pass/fail indicator: {report_md[:200]}"
    )


def test_run_analysis_rejects_empty_input(env_with_token):
    """run_analysis must return a warning when no image is provided."""
    from app_space import run_analysis

    original, gallery, report_md = run_analysis(None)

    assert original is None
    assert gallery == []
    assert '⚠️' in report_md


def test_wcag_report_format_error_case(env_with_token):
    """format_wcag_report must render error responses correctly."""
    from app_space import format_wcag_report

    result = format_wcag_report({
        'error': 'HF_TOKEN not set',
        'findings': [],
        'passes': False,
    })

    assert '⚠️' in result
    assert 'HF_TOKEN not set' in result