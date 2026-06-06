"""
RED tests — verify known bugs before fixing.
Run: pytest tests/test_app_space.py -v
"""

import pytest
import sys
import io

# ── CVD Gallery ──────────────────────────────────────────────────────────────

def test_cvd_gallery_generates_10_types():
    """CVD gallery must produce exactly 10 variants."""
    from app_space import generate_cvd_gallery
    from PIL import Image
    import numpy as np

    img = Image.fromarray(np.random.randint(0, 255, (200, 100, 3), dtype=np.uint8))
    gallery = generate_cvd_gallery(img)

    assert isinstance(gallery, list), f"gallery must be list, got {type(gallery)}"
    assert len(gallery) == 10, f"Expected 10 CVD types, got {len(gallery)}"


def test_cvd_gallery_items_are_image_label_tuples():
    """Each gallery item must be a (PIL.Image, str) tuple."""
    from app_space import generate_cvd_gallery
    from PIL import Image
    import numpy as np

    img = Image.new('RGB', (50, 50), color='red')
    gallery = generate_cvd_gallery(img)

    for i, item in enumerate(gallery):
        assert isinstance(item, tuple), f"item[{i}] must be tuple, got {type(item)}"
        img_out, label = item
        assert isinstance(img_out, Image.Image), f"item[{i}][0] must be Image, got {type(img_out)}"
        assert isinstance(label, str), f"item[{i}][1] must be str, got {type(label)}"


# ── WCAG Report ──────────────────────────────────────────────────────────────

def test_format_wcag_report_passes_true():
    """Report renders correctly when page passes."""
    from app_space import format_wcag_report

    result = format_wcag_report({'passes': True, 'findings': [], 'summary': 'OK'})
    assert '✅ Pass' in result
    assert 'No accessibility issues detected' in result


def test_format_wcag_report_fails_with_findings():
    """Report renders correctly when page has findings."""
    from app_space import format_wcag_report

    result = format_wcag_report({
        'passes': False,
        'findings': [{
            'type': 'Low Contrast',
            'wcag_criterion': '1.4.3',
            'severity': 'serious',
            'description': 'Button text #777 on #CCC background',
            'location': 'Submit button, top-right',
        }],
        'summary': '1 serious issue found',
    })
    assert '❌ Fail' in result
    assert 'Issue 1' in result
    assert '1.4.3' in result
    assert 'Low Contrast' in result


def test_format_wcag_report_error_message():
    """Report shows error when VLM call fails."""
    from app_space import format_wcag_report

    result = format_wcag_report({'error': 'HF_TOKEN not set', 'findings': [], 'passes': False})
    assert '⚠️' in result
    assert 'HF_TOKEN not set' in result


# ── Run analysis — bytes vs file object ──────────────────────────────────────

def test_run_analysis_handles_bytes():
    """Gradio File(type='binary') passes bytes, not file object — must not crash."""
    from app_space import run_analysis
    from PIL import Image
    import io

    # Minimal valid PNG bytes
    png_buf = io.BytesIO()
    Image.new('RGB', (50, 50), color='blue').save(png_buf, format='PNG')
    png_bytes = png_buf.getvalue()

    # Pass bytes directly (Gradio binary type behavior)
    original, gallery, report = run_analysis(png_bytes)

    assert original is not None, "Original image must not be None"
    assert isinstance(gallery, list), "Gallery must be a list"


def test_run_analysis_handles_file_obj():
    """run_analysis also works with file-like objects (non-binary Gradio)."""
    from app_space import run_analysis
    from PIL import Image
    import io

    png_buf = io.BytesIO()
    Image.new('RGB', (50, 50), color='green').save(png_buf, format='PNG')
    png_buf.seek(0)

    original, gallery, report = run_analysis(png_buf)

    assert original is not None


def test_run_analysis_rejects_none():
    """run_analysis must return warning message when no file uploaded."""
    from app_space import run_analysis

    original, gallery, report = run_analysis(None)

    assert original is None
    assert gallery == []
    assert '⚠️' in report


# ── Gradio 6 theme — must be passed to launch(), not Blocks() ────────────────

def test_gradio_version_check():
    """Verify we're testing against Gradio 6+ (where theme moved to launch)."""
    import gradio as gr
    major = int(gr.__version__.split('.')[0])
    assert major >= 6, f"Expected Gradio 6+, got {gr.__version__}"


def test_blocks_theme_not_in_constructor():
    """
    In Gradio 6, theme/css are launch() params, not Blocks() params.
    app_space.py must NOT pass theme= or css= to gr.Blocks() constructor.
    """
    import ast
    from pathlib import Path

    app_space_path = Path(__file__).resolve().parents[1] / 'app_space.py'
    src = app_space_path.read_text(encoding='utf-8')

    tree = ast.parse(src)

    # Find the with gr.Blocks(...) as demo: block
    blocks_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            for item in node.items:
                if isinstance(item.context_expr, ast.Call):
                    func = item.context_expr.func
                    if isinstance(func, ast.Attribute) and func.attr == 'Blocks':
                        blocks_node = item.context_expr
                        break

    assert blocks_node is not None, "Could not find gr.Blocks() call"

    # Check that 'theme' and 'css' are NOT in Blocks() kwargs
    if blocks_node.keywords:
        for kw in blocks_node.keywords:
            assert kw.arg not in ('theme', 'css'), \
                f"Gradio 6: theme/css must NOT be in Blocks() constructor — move to launch()"


def test_demo_launch_has_theme_css():
    """launch() call must include theme= and css= kwargs for Gradio 6."""
    import ast
    from pathlib import Path

    app_space_path = Path(__file__).resolve().parents[1] / 'app_space.py'
    src = app_space_path.read_text(encoding='utf-8')

    tree = ast.parse(src)

    # Find demo.launch(...) call
    launch_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == 'launch' and isinstance(func.value, ast.Name) and func.value.id == 'demo':
                launch_node = node
                break

    assert launch_node is not None, "Could not find demo.launch() call"

    kw_names = {kw.arg for kw in launch_node.keywords}
    assert 'theme' in kw_names, "launch() must include theme= kwarg (Gradio 6)"
    assert 'css' in kw_names, "launch() must include css= kwarg (Gradio 6)"