"""
RED test — verify Gradio File with type="binary" passes bytes, not file objects.
Regression test for: "Bytes object has no attribute read" error when uploading JPEG.
Gradio's binary File type returns raw bytes, not a file-like object.
"""
import sys, os, pathlib

# Read modal_app.py source directly (can't import a Modal Stub in test env)
source_file = pathlib.Path(os.path.join(os.path.dirname(__file__), "..", "color_ux_access", "modal_app.py"))
source = source_file.read_text()
assert "isinstance(file_obj, bytes)" in source, \
    "analyze_screenshot should check isinstance(file_obj, bytes) before calling .read()"