"""
CVD simulation using DaltonLens.
Wraps the DaltonLens Machado2009 model with our standard interface.
"""
import numpy as np
from PIL import Image
from daltonlens import simulate

# All supported CVD variants for the audit
CVD_VARIANTS = [
    'deuteranopia',   # Red-green (green deficient) — most common
    'protanopia',     # Red-green (red deficient)
    'tritanopia',     # Blue-yellow
    'achromatopsia',  # Complete grayscale
    # Anomalous trichromacy (less severe forms)
    'deuteranomaly',
    'protanomaly',
    'tritanomaly',
]

# Map variant names to DaltonLens Deficiency enum
_DEFFICIENCY_MAP = {
    'deuteranopia': simulate.Deficiency.DEUTAN,
    'protanopia': simulate.Deficiency.PROTAN,
    'tritanopia': simulate.Deficiency.TRITAN,
    'deuteranomaly': simulate.Deficiency.DEUTAN,
    'protanomaly': simulate.Deficiency.PROTAN,
    'tritanomaly': simulate.Deficiency.TRITAN,
}

# Severity: dichromacy (1.0) vs anomalous trichromacy (0.5)
_SEVERITY_MAP = {
    'deuteranopia': 1.0,
    'protanopia': 1.0,
    'tritanopia': 1.0,
    'deuteranomaly': 0.6,
    'protanomaly': 0.6,
    'tritanomaly': 0.6,
}

# Singleton simulator — lazy init
_simulator = None


def _get_simulator():
    global _simulator
    if _simulator is None:
        _simulator = simulate.Simulator_Machado2009()
    return _simulator


def simulate_cvd(image, cvd_type='deuteranopia'):
    """
    Simulate how an image appears to someone with CVD.

    Args:
        image: PIL Image (RGB or RGBA)
        cvd_type: string from CVD_VARIANTS

    Returns:
        PIL Image (RGB) — simulated view
    """
    cvd_type = cvd_type.lower()

    if cvd_type == 'achromatopsia':
        return _grayscale(image)

    deficiency = _DEFFICIENCY_MAP.get(cvd_type, simulate.Deficiency.DEUTAN)
    severity = _SEVERITY_MAP.get(cvd_type, 1.0)

    sim = _get_simulator()

    # DaltonLens expects numpy uint8 array
    im_np = np.array(image, dtype=np.uint8)
    result_np = sim.simulate_cvd(im_np, deficiency, severity)
    return Image.fromarray(result_np)


def _grayscale(image):
    """Convert image to grayscale (achromatopsia simulation)."""
    im_np = np.array(image, dtype=np.float32)
    # Rec.709 luma coefficients
    gray = (0.2126 * im_np[:,:,0] +
            0.7152 * im_np[:,:,1] +
            0.0722 * im_np[:,:,2])
    gray = np.clip(gray, 0, 255).astype(np.uint8)
    # Expand to RGB
    result = np.stack([gray, gray, gray], axis=2)
    return Image.fromarray(result)