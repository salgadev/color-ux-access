"""
backend_api.py — Pure Python wrappers for CVD gallery + VLM pipeline.

All I/O is bytes + JSON only (no Gradio components).
Reuses core logic from app.py but adds 4:3 thumbnail resizing.
"""

from __future__ import annotations

import io
import base64
from typing import List, Tuple, Dict, Any

from PIL import Image
import numpy as np
from daltonlens import simulate

# Reuse simulators and config from app.py (read-only import)
from app import (
    deficiency_config,
    simulator as _machado_sim,
    severe_simulator as _vienot_sim,
    tritan_simulator as _brettel_sim,
    analyze_all_perspectives as _analyze_all_perspectives,
    format_wcag_report as _format_wcag_report,
    _call_minicpm_endpoint,
    _VLM_CVD_PROMPTS,
    _ACCESSIBILITY_SYSTEM_PROMPT,
)

# Map deficiency_config keys to simulator + deficiency enum
_CVD_LABEL_MAP: Dict[str, str] = {
    'protanopia': 'protanopia',
    'severe_protanopia': 'severe_protanopia',
    'deuteranopia': 'deuteranopia',
    'severe_deuteranopia': 'severe_deuteranopia',
    'tritanopia': 'tritanopia',
    'protanomaly': 'protanomaly',
    'deuteranomaly': 'deuteranomaly',
    'tritanomaly': 'tritanomaly',
}


def _get_simulator_and_deficiency(cvd_name: str):
    """Return (simulator, deficiency_enum) for a CVD type."""
    cfg = deficiency_config[cvd_name]
    return cfg['simulator'], cfg['deficiency'], cfg['severity']


def _cvd_name_to_label(cvd_name: str) -> str:
    """Human-readable label for a CVD deficiency name."""
    labels = {
        'protanopia': 'Protanopia (red-blind)',
        'severe_protanopia': 'Severe Protanopia (red-blind)',
        'deuteranopia': 'Deuteranopia (green-blind)',
        'severe_deuteranopia': 'Severe Deuteranopia (green-blind)',
        'tritanopia': 'Tritanopia (blue-blind)',
        'protanomaly': 'Protanomaly (red-weak)',
        'deuteranomaly': 'Deuteranomaly (green-weak)',
        'tritanomaly': 'Tritanomaly (blue-weak)',
    }
    return labels.get(cvd_name, cvd_name)


def _resize_to_4_3(img: Image.Image) -> Image.Image:
    """Resize image to 4:3 aspect ratio with center crop.

    Steps:
    1. Calculate target height for given width (4:3).
    2. If image is taller than target, crop top/bottom (center crop).
    3. If image is wider than target, resize height to match (letterbox-style fit).
    4. Final size is always (width, round(width * 3/4)) or proportional.
    """
    w, h = img.size
    target_ratio = 4 / 3
    current_ratio = w / h

    if current_ratio > target_ratio:
        # Image is wider than 4:3 — resize to target height, crop width
        target_h = h
        target_w = int(target_h * target_ratio)
        img = img.resize((target_w, target_h), Image.LANCZOS)
        # Center crop to exact 4:3
        left = (target_w - (target_w)) // 2  # already correct
        # Actually when current_ratio > target, img is resized to target_h
        # Then we center-crop to 4:3 width
        left = (target_w - int(target_h * target_ratio)) // 2
        right = left + int(target_h * target_ratio)
        img = img.crop((left, 0, right, target_h))
    else:
        # Image is taller/narrower than 4:3 — resize to target width
        target_w = w
        target_h = int(target_w / target_ratio)
        img = img.resize((target_w, target_h), Image.LANCZOS)

    return img


def _simulate_cvd_image(original: Image.Image, cvd_name: str) -> Image.Image:
    """Simulate a specific CVD type on a PIL Image and resize to 4:3."""
    sim, deficiency, severity = _get_simulator_and_deficiency(cvd_name)
    arr = np.asarray(original.convert('RGB'))
    cvd_arr = sim.simulate_cvd(arr, deficiency, severity)
    cvd_img = Image.fromarray(cvd_arr)
    return _resize_to_4_3(cvd_img)


# ── Public API ────────────────────────────────────────────────────────────────


def api_generate_gallery_from_bytes(image_bytes: bytes) -> List[Tuple[bytes, str]]:
    """
    Given raw screenshot bytes, return a list of (image_bytes, label) for all 8 CVD variants.

    Each simulated image is:
      - Processed through the correct CVD simulator (Machado/Vienot/Brettel)
      - Resized to 4:3 aspect ratio (center-cropped or letterboxed)
      - PNG-encoded and returned as bytes

    Returns:
        List of 8 (png_bytes, label_str) tuples.
    """
    try:
        original = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    except Exception as e:
        raise ValueError(f"Could not open image: {e}") from e

    gallery = []
    for cvd_name in deficiency_config:
        label = _cvd_name_to_label(cvd_name)
        simulated = _simulate_cvd_image(original, cvd_name)
        buf = io.BytesIO()
        simulated.save(buf, format='PNG')
        gallery.append((buf.getvalue(), label))

    return gallery


def api_analyze_cvd_grid_from_bytes(
    gallery: List[Tuple[bytes, str]]
) -> Dict[str, Any]:
    """
    Given a list of (image_bytes, label) tuples, reconstruct PIL images and run
    analyze_all_perspectives. Return the merged JSON result.

    Args:
        gallery: List of (png_bytes, label_str) as produced by api_generate_gallery_from_bytes.

    Returns:
        Dict with keys: 'findings', 'summary', 'passes' (same structure as VLM JSON).
    """
    # Reconstruct PIL images for analyze_all_perspectives
    cvd_grid = []
    for img_bytes, label in gallery:
        try:
            img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        except Exception:
            # If image bytes are corrupted, skip this item
            continue
        cvd_grid.append((img, label))

    if not cvd_grid:
        return {
            'error': 'No valid images in gallery',
            'findings': [],
            'passes': False,
        }

    return _analyze_all_perspectives(cvd_grid)


def api_report_from_json(vlm_result: Dict[str, Any]) -> str:
    """
    Return the markdown accessibility report using format_wcag_report.

    Args:
        vlm_result: Dict with 'findings', 'summary', 'passes' (and optionally 'error').

    Returns:
        Markdown string.
    """
    return _format_wcag_report(vlm_result)