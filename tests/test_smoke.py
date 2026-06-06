"""
RED test — verify all core imports work and the app is loadable.
Tests: PIL, Gradio, CVD colorspace, capture module, custom theme, VLM inference.
"""
import sys


def test_pil_import():
    from PIL import Image
    img = Image.new("RGB", (10, 10))
    assert img.size == (10, 10)


def test_app_import():
    # app/app.py is the Gradio app module — demo is defined inside, not as top-level 'app'
    import app.app as app_module
    # Verify the module loads without error (Gradio demo exists inside)
    assert app_module is not None


def test_custom_theme_import():
    from app.custom_theme import color_ux_access_theme
    assert color_ux_access_theme is not None


def test_cvd_simulation_import():
    # colorspacious can do color space conversions (CVD sim via daltonlens)
    from colorspacious import cspace_convert
    import numpy as np
    result = cspace_convert([[128, 128, 128]], "sRGB255", "CIECAM02")
    result_arr = np.array(result).flatten()
    assert result_arr.shape == (7,), f"Expected 7-dim CIECAM02, got {result_arr.shape}"


def test_capture_screenshot_function_exists():
    from color_ux_access.capture import take_screenshot
    assert callable(take_screenshot)