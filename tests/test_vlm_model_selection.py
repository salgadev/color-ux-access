"""
Tests for VLM model selection and Modal endpoint integration.

With the Modal deployment, inference goes through the deployed Modal app
(https://narwall-tech--color-ux-access-ui.modal.run/) not HF Router directly.

Run: pytest tests/test_vlm_model_selection.py -v
"""

import pytest
import sys
import io
from unittest.mock import patch, MagicMock
from PIL import Image
import numpy as np

import app_space as app_module


# ── MODELS dict must exist and be populated ───────────────────────────────────

def test_models_dict_exists():
    """MODELS dict must be defined in app_space module."""
    assert hasattr(app_module, 'MODELS'), \
        "app_space must define a MODELS dict for swappable VLM backends"


def test_models_dict_has_aya_vision():
    """MODELS must include aya-vision-32b (default Cohere model)."""
    models = getattr(app_module, 'MODELS', {})
    assert 'aya-vision-32b' in models, \
        "MODELS must include 'aya-vision-32b' as default"


def test_models_dict_has_minicpm_v4_6():
    """MODELS must include minicpm-v-4.6 for OpenBMB $5K prize eligibility."""
    models = getattr(app_module, 'MODELS', {})
    assert 'minicpm-v-4.6' in models, \
        "MODELS must include 'minicpm-v-4.6' for OpenBMB sponsor prize"


# ── Modal endpoint configuration ──────────────────────────────────────────────

def test_modal_url_configured():
    """_MODAL_URL must point to the deployed Modal app."""
    assert hasattr(app_module, '_MODAL_URL')
    assert 'narwall-tech--color-ux-access-ui' in app_module._MODAL_URL


# ── analyze_with_vlm must accept model parameter ───────────────────────────────

def test_analyze_with_vlm_accepts_model_parameter():
    """analyze_with_vlm must accept a model= kwarg to select VLM backend."""
    import inspect
    sig = inspect.signature(app_module.analyze_with_vlm)
    params = list(sig.parameters.keys())
    assert 'model' in params, \
        f"analyze_with_vlm must accept 'model' parameter, got params: {params}"


def test_analyze_with_vlm_calls_modal_endpoint():
    """analyze_with_vlm must call _call_modal_analyze (not HF Router)."""
    img = Image.fromarray(np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    image_bytes = buf.getvalue()

    fake_result = {'findings': [], 'passes': True, 'summary': 'ok'}
    with patch.object(app_module, '_call_modal_analyze', return_value=fake_result) as mock:
        result = app_module.analyze_with_vlm(image_bytes, model='aya-vision-32b')
        mock.assert_called_once_with(image_bytes)
        assert result == fake_result


def test_analyze_with_vlm_returns_wcag_dict():
    """analyze_with_vlm must return a WCAG dict with findings, passes, summary."""
    img = Image.fromarray(np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    image_bytes = buf.getvalue()

    fake_result = {
        'findings': [{'type': 'Low Contrast', 'wcag_criterion': '1.4.1',
                      'description': 'Test', 'severity': 'serious', 'location': 'Top'}],
        'passes': False,
        'summary': '1 issue found',
    }
    with patch.object(app_module, '_call_modal_analyze', return_value=fake_result):
        result = app_module.analyze_with_vlm(image_bytes, model='aya-vision-32b')
        assert 'findings' in result
        assert 'passes' in result
        assert 'summary' in result


def test_analyze_with_vlm_returns_error_dict_on_failure():
    """analyze_with_vlm must return error dict when Modal call fails gracefully."""
    img = Image.fromarray(np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    image_bytes = buf.getvalue()

    with patch.object(app_module, '_call_modal_analyze', side_effect=RuntimeError("Upload failed")):
        result = app_module.analyze_with_vlm(image_bytes)
        assert 'error' in result
        assert result['findings'] == []
        assert result['passes'] is False


# ── run_analysis must accept model parameter ───────────────────────────────────

def test_run_analysis_accepts_model_parameter():
    """run_analysis must accept model= kwarg to pass through to VLM backend."""
    import inspect
    sig = inspect.signature(app_module.run_analysis)
    params = list(sig.parameters.keys())
    has_model_param = any('model' in p for p in params)
    assert has_model_param, \
        f"run_analysis must accept a model selection parameter, got params: {params}"


def test_run_analysis_passes_model_to_vlm():
    """run_analysis should pass the model selection through to analyze_with_vlm."""
    buf = io.BytesIO()
    Image.new('RGB', (50, 50), color='blue').save(buf, format='PNG')
    png_bytes = buf.getvalue()

    with patch.object(app_module, 'analyze_with_vlm') as mock_vlm:
        mock_vlm.return_value = {'findings': [], 'passes': True, 'summary': 'ok'}
        app_module.run_analysis(png_bytes, model='minicpm-v-4.6')
        _, kwargs = mock_vlm.call_args
        assert kwargs.get('model') == 'minicpm-v-4.6', \
            f"run_analysis should pass model='minicpm-v-4.6' to analyze_with_vlm, got {kwargs}"


# ── Model choices in Gradio UI ─────────────────────────────────────────────────

def test_model_choices_in_blocks():
    """Gradio Blocks must include a model selection Dropdown with MODELS keys."""
    import ast
    from pathlib import Path

    app_space_path = Path(__file__).resolve().parents[1] / 'app_space.py'
    src = app_space_path.read_text(encoding='utf-8')

    tree = ast.parse(src)

    # Find gr.Dropdown calls with label containing "model" (case-insensitive)
    dropdowns_with_model_label = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == 'Dropdown':
                for kw in node.keywords:
                    if kw.arg == 'label' and isinstance(kw.value, ast.Constant):
                        if 'model' in kw.value.value.lower():
                            dropdowns_with_model_label.append(node)

    assert len(dropdowns_with_model_label) > 0, \
        "app_space.py must have a gr.Dropdown for model selection (label containing 'model')"