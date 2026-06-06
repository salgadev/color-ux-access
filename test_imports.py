#!/usr/bin/env python
"""
Simple test script to verify imports work correctly
"""
print("Testing imports...")

try:
    import gradio as gr
    print("✓ Gradio imported successfully")
except Exception as e:
    print(f"✗ Gradio import failed: {e}")

try:
    from playwright.sync_api import sync_playwright
    print("✓ Playwright imported successfully")
except Exception as e:
    print(f"✗ Playwright import failed: {e}")

try:
    from PIL import Image
    print("✓ PIL imported successfully")
except Exception as e:
    print(f"✗ PIL import failed: {e}")

try:
    import numpy as np
    print("✓ NumPy imported successfully")
except Exception as e:
    print(f"✗ NumPy import failed: {e}")

try:
    from daltonlens import simulate
    print("✓ DaltonLens imported successfully")
except Exception as e:
    print(f"✗ DaltonLens import failed: {e}")

try:
    import torch
    print(f"✓ Torch imported successfully (version: {torch.__version__})")
except Exception as e:
    print(f"✗ Torch import failed: {e}")

try:
    from transformers import AutoProcessor, AutoModelForVision2Seq
    print("✓ Transformers imported successfully")
except Exception as e:
    print(f"✗ Transformers import failed: {e}")

print("Test complete.")