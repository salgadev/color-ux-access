"""
RED tests — define expected behavior for swappable VLM model backend.
Tests verify model selection works: aya-vision-32b, MiniCPM-V 4.6, etc.

Run: pytest tests/test_vlm_model_selection.py -v

RED phase: these tests define what the implementation must do.
GREEN phase: implement the feature to make them pass.
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


# ── analyze_with_vlm must accept model parameter ───────────────────────────────

def test_analyze_with_vlm_accepts_model_parameter():
    """analyze_with_vlm must accept a model= kwarg to select VLM backend."""
    import inspect
    sig = inspect.signature(app_module.analyze_with_vlm)
    params = list(sig.parameters.keys())
    assert 'model' in params, \
        f"analyze_with_vlm must accept 'model' parameter, got params: {params}"


def test_analyze_with_vlm_default_model_is_aya_vision():
    """Default model should be aya-vision-32b when model= not specified."""
    import os
    os.environ['HF_TOKEN'] = 'fake-token-for-test'
    # Create minimal test image bytes
    img = Image.fromarray(np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    image_bytes = buf.getvalue()

    # Patch the OpenAI client to capture the model called
    with patch('app_space.OpenAI') as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"findings":[],"passes":true,"summary":"ok"}'
        mock_client.chat.completions.create.return_value = mock_response

        app_module.analyze_with_vlm(image_bytes)
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['model'] == 'CohereLabs/aya-vision-32b', \
            f"Default model should be CohereLabs/aya-vision-32b, got {call_kwargs.get('model')}"


def test_analyze_with_vlm_aya_vision_uses_cohere():
    """model='aya-vision-32b' should call CohereLabs/aya-vision-32b via HF Router."""
    import os
    os.environ['HF_TOKEN'] = 'fake-token-for-test'
    img = Image.fromarray(np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    image_bytes = buf.getvalue()

    with patch('app_space.OpenAI') as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"findings":[],"passes":true,"summary":"ok"}'
        mock_client.chat.completions.create.return_value = mock_response

        app_module.analyze_with_vlm(image_bytes, model='aya-vision-32b')
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['model'] == 'CohereLabs/aya-vision-32b'


def test_analyze_with_vlm_minicpm_uses_openbmb_model():
    """model='minicpm-v-4.6' should call openbmb/mini-cpm-v-4_6 for OpenBMB prize."""
    import os
    os.environ['HF_TOKEN'] = 'fake-token-for-test'
    img = Image.fromarray(np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    image_bytes = buf.getvalue()

    with patch('app_space.OpenAI') as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"findings":[],"passes":true,"summary":"ok"}'
        mock_client.chat.completions.create.return_value = mock_response

        app_module.analyze_with_vlm(image_bytes, model='minicpm-v-4.6')
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['model'] == 'openbmb/mini-cpm-v-4_6', \
            f"MiniCPM-V 4.6 should use openbmb/mini-cpm-v-4_6, got {call_kwargs.get('model')}"


def test_analyze_with_vlm_invalid_model_raises():
    """Invalid model name should raise ValueError with helpful message."""
    img = Image.fromarray(np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    image_bytes = buf.getvalue()

    with patch.dict(app_module.MODELS, {'aya-vision-32b': {'provider': 'cohere', 'model_id': 'CohereLabs/aya-vision-32b'}}, clear=False):
        with pytest.raises(ValueError) as exc_info:
            app_module.analyze_with_vlm(image_bytes, model='nonexistent-model')
        assert 'nonexistent-model' in str(exc_info.value)


# ── run_analysis must accept model parameter ───────────────────────────────────

def test_run_analysis_accepts_model_parameter():
    """run_analysis must accept model= kwarg to pass through to VLM backend."""
    import inspect
    sig = inspect.signature(app_module.run_analysis)
    params = list(sig.parameters.keys())
    # Accept either 'model' or 'model_name' as the param name
    has_model_param = any('model' in p for p in params)
    assert has_model_param, \
        f"run_analysis must accept a model selection parameter, got params: {params}"


def test_run_analysis_passes_model_to_vlm():
    """run_analysis should pass the model selection through to analyze_with_vlm."""
    # Create minimal PNG bytes
    buf = io.BytesIO()
    Image.new('RGB', (50, 50), color='blue').save(buf, format='PNG')
    png_bytes = buf.getvalue()

    with patch('app_space.analyze_with_vlm') as mock_vlm:
        mock_vlm.return_value = {'findings': [], 'passes': True}
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