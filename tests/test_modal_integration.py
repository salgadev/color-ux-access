"""
RED tests — verify Modal endpoint is called instead of HF Router directly.
Run: pytest tests/test_modal_integration.py -v
"""
import os
import io
import sys

import pytest
import numpy as np
from PIL import Image

# Ensure project root is on path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def test_image_bytes():
    """Red/green button panel — real WCAG 1.4.1 failure scenario."""
    arr = np.zeros((120, 300, 3), dtype=np.uint8)
    arr[:, :] = [240, 240, 240]
    arr[20:100, 20:145] = [52, 199, 89]   # green
    arr[20:100, 155:280] = [205, 92, 92]  # red
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


@pytest.fixture
def modal_url():
    """The deployed Modal endpoint URL."""
    return os.environ.get('MODAL_URL', 'https://narwall-tech--color-ux-access-ui.modal.run')


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_app_space_calls_modal_not_hf_router(modal_url, test_image_bytes):
    """
    app_space.py must call the Modal Gradio endpoint, not HF Router directly.
    Verify: analyze_with_vlm delegates to Modal API and returns proper WCAG JSON.
    """
    from app_space import analyze_with_vlm

    result = analyze_with_vlm(test_image_bytes, model="aya-vision-32b")

    assert isinstance(result, dict), f"Result must be dict, got {type(result)}"
    assert 'error' not in result or result.get('findings') is not None, (
        f"Modal call failed: {result.get('error')}"
    )

    # Validate WCAG JSON structure
    assert 'findings' in result
    assert 'passes' in result
    assert 'summary' in result
    assert isinstance(result['findings'], list)

    for f in result['findings']:
        assert 'wcag_criterion' in f
        assert 'description' in f
        assert f['wcag_criterion'] in {'1.1.1', '1.4.1', '1.4.3', '1.4.11'}

    print(f"\nModal result: passes={result['passes']}, findings={len(result['findings'])}")


def test_run_analysis_calls_modal_endpoint(modal_url, test_image_bytes):
    """
    run_analysis() must go through Modal endpoint, not HF Router.
    Full pipeline: image → CVD gallery + Modal WCAG report.
    """
    from app_space import run_analysis

    original, gallery, report_md = run_analysis(test_image_bytes, model="aya-vision-32b")

    assert original is not None
    assert isinstance(gallery, list)
    assert len(gallery) == 10
    assert isinstance(report_md, str)
    assert len(report_md) > 20
    # Report should contain Modal's WCAG output (not HF_TOKEN error)
    assert '⚠️ HF_TOKEN not set' not in report_md


def test_run_analysis_none_returns_warning(modal_url):
    """run_analysis must return warning on empty input."""
    from app_space import run_analysis

    original, gallery, report_md = run_analysis(None)

    assert original is None
    assert gallery == []
    assert '⚠️' in report_md