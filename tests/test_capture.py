"""
RED test — verify capture module exists and behaves correctly.
TDD: tests FAIL before capture.py is created, GREEN after.
"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_take_screenshot_function_exists():
    from color_ux_access.capture import take_screenshot
    assert callable(take_screenshot)