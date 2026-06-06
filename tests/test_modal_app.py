"""
RED test — verify Modal app definition structure from source.
Tests: app is a modal.App, image uses debian_slim, GPU function has A10G + HF_TOKEN secret,
upload_screenshot exists, ui has asgi_app decorator.
"""
import pathlib

source_file = pathlib.Path(__file__).parent.parent / "color_ux_access" / "modal_app.py"
source = source_file.read_text()

def test_app_is_modal_app():
    assert 'modal.App("color-ux-access")' in source

def test_image_uses_debian_slim():
    assert 'debian_slim' in source

def test_gpu_function_has_a10g():
    assert 'gpu="A10G"' in source

def test_hf_token_secret_attached():
    assert 'hf-token-narwall' in source

def test_upload_screenshot_function_exists():
    assert 'def upload_screenshot' in source

def test_ui_has_asgi_app_decorator():
    # @modal.asgi_app() pattern (not @app.asgi_app)
    assert '@modal.asgi_app()' in source

def test_base_url_correct():
    # base_url should be router.huggingface.co/v1 (NOT /aya-vision-32b/v1)
    assert 'router.huggingface.co/v1' in source
    assert '/aya-vision-32b/v1' not in source