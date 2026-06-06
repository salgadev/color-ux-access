"""
Color-UX-Access — HF Space deployment.
========================================
Gradio app for colorblind accessibility testing, ready for hackathon submission.

Architecture:
  - User uploads a screenshot (OS/browser screenshot tool → Gradio File)
  - CVD simulation runs locally (pure Python, no browser needed)
  - VLM inference via deployed Modal app (https://narwall-tech--color-ux-access-ui.modal.run/)
  - Modal endpoint → upload_screenshot.remote() → vlm_inference_fn (A10G GPU) → HF Router → aya-vision-32b
  - WCAG 2.1 markdown report + CVD gallery displayed

Requirements:
  - Python 3.12 (HF Spaces requirement)
  - spaces (gradio==5.0.0 is SDK-forced — Gradio 5/6 compat via gr.__version__ at runtime)
  - torch with CUDA libs
  - openai, pillow, daltonlens, requests

Deploy:
  1. Push to GitHub
  2. Create HF Space (SDK: Gradio, hardware: T4/mega or A10G)
  3. Add MODAL_URL secret in Space settings
  4. Link to GitHub repo or upload this file directly

Note: HF_TOKEN in Space secrets is for Space management only.
Inference goes through the Modal endpoint — no HF_TOKEN needed here.
"""

import os
import io
import json
import base64
import re

import gradio as gr
from PIL import Image
import numpy as np
from daltonlens import simulate
import requests

# ── CVD Simulators ────────────────────────────────────────────────────────────

simulator = simulate.Simulator_Machado2009()
severe_simulator = simulate.Simulator_Vienot1999()
tritan_simulator = simulate.Simulator_Brettel1997()

deficiency_config = {
    'protanopia':       {'simulator': simulator,       'severity': 0.8, 'deficiency': simulate.Deficiency.PROTAN},
    'severe_protanopia':{'simulator': severe_simulator,'severity': 1.0, 'deficiency': simulate.Deficiency.PROTAN},
    'deuteranopia':     {'simulator': simulator,       'severity': 0.8, 'deficiency': simulate.Deficiency.DEUTAN},
    'severe_deuteranopia':{'simulator': severe_simulator,'severity': 1.0,'deficiency': simulate.Deficiency.DEUTAN},
    'tritanopia':       {'simulator': tritan_simulator,'severity': 0.8, 'deficiency': simulate.Deficiency.TRITAN},
    'protanomaly':      {'simulator': simulator,       'severity': 0.4, 'deficiency': simulate.Deficiency.PROTAN},
    'deuteranomaly':    {'simulator': simulator,       'severity': 0.4, 'deficiency': simulate.Deficiency.DEUTAN},
    'tritanomaly':      {'simulator': tritan_simulator,'severity': 0.4, 'deficiency': simulate.Deficiency.TRITAN},
    # Achromatopsia/Achromatomaly handled via grayscale
}

# ── Swappable VLM Model Registry ───────────────────────────────────────────────
# Enables one-line model swap for different sponsor prize eligibility:
#   - aya-vision-32b  → CohereLabs/aya-vision-32b (default, Cohere prize)
#   - minicpm-v-4.6   → openbmb/mini-cpm-v-4_6 (OpenBMB $5K prize)
#   - nemotron-15b    → nvidia/Nemotron-4-15B-base (NVIDIA prize, if required)
MODELS = {
    "aya-vision-32b": {
        "provider": "cohere",
        "model_id": "CohereLabs/aya-vision-32b",
        "description": "Default — 32B vision model via HF Router",
    },
    "minicpm-v-4.6": {
        "provider": "openbmb",
        "model_id": "openbmb/mini-cpm-v-4_6",
        "description": "OpenBMB prize — MiniCPM-V 4.6 (~4B params, under 32B cap)",
    },
    "nemotron-15b": {
        "provider": "nvidia",
        "model_id": "nvidia/Nemotron-4-15B-base",
        "description": "NVIDIA prize — confirm Nemotron requirement with organizers",
    },
}


def simulate_cvd(image: Image.Image, sim, deficiency, severity) -> Image.Image:
    """Apply CVD simulation to a PIL Image."""
    arr = np.asarray(image.convert('RGB'))
    cvd = sim.simulate_cvd(arr, deficiency, severity)
    return Image.fromarray(cvd)


def simulate_achromatopsia(image: Image.Image, severity: float) -> Image.Image:
    """Simulate achromatopsia (rod monochromacy) via grayscale blend."""
    gray = image.convert('L')
    gray_rgb = Image.merge('RGB', (gray, gray, gray))
    if severity < 1.0:
        return Image.blend(image.convert('RGB'), gray_rgb, severity)
    return gray_rgb


def generate_cvd_gallery(original: Image.Image) -> list[tuple[Image.Image, str]]:
    """Generate all 10 CVD simulation variants for the gallery."""
    results = []
    for name, cfg in deficiency_config.items():
        img = simulate_cvd(
            original, cfg['simulator'], cfg['deficiency'], cfg['severity']
        )
        label = name.replace('_', ' ').title()
        results.append((img, label))

    # Grayscale-based simulations
    results.append((simulate_achromatopsia(original, 1.0), 'Achromatopsia'))
    results.append((simulate_achromatopsia(original, 0.5), 'Achromatomaly'))

    return results


def format_wcag_report(vlm_result: dict) -> str:
    """Convert VLM JSON output into a formatted markdown report."""
    if 'error' in vlm_result:
        return f"⚠️ **Error:** {vlm_result['error']}"

    findings = vlm_result.get('findings', [])
    if not findings:
        if vlm_result.get('passes', False):
            return "✅ Pass — No accessibility issues detected."
        return "✅ **No accessibility issues detected.**"

    report = "## WCAG Accessibility Report\n\n"
    report += f"**Overall:** {'✅ Pass' if vlm_result.get('passes', False) else '❌ Fail'}\n\n"

    severity_icons = {'critical': '🔴', 'serious': '🟠', 'moderate': '🟡'}
    wcag_links = {
        '1.1.1': 'https://www.w3.org/WAI/WCAG21/Understanding/non-text-content',
        '1.4.1': 'https://www.w3.org/WAI/WCAG21/Understanding/use-of-color',
        '1.4.3': 'https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum',
        '1.4.11': 'https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast',
    }

    for i, f in enumerate(findings, 1):
        icon = severity_icons.get(f.get('severity', 'moderate'), '⚪')
        wcag = f.get('wcag_criterion', 'N/A')
        link = wcag_links.get(wcag, '#')
        report += f"### {icon} Issue {i}: {f.get('type', 'Unknown')}\n\n"
        report += f"- **WCAG:** [{wcag}]({link})\n"
        report += f"- **Severity:** {f.get('severity', 'N/A').capitalize()}\n"
        report += f"- **Description:** {f.get('description', 'N/A')}\n"
        report += f"- **Location:** {f.get('location', 'N/A')}\n\n"

    if vlm_result.get('summary'):
        report += f"**Summary:** {vlm_result['summary']}\n"

    return report


# ── Modal Endpoint Helper ──────────────────────────────────────────────────────
# Inference runs via the deployed Modal app, not HF Router directly.
# The Modal app (color_ux_access/modal_app.py) handles GPU/VLM internally.
# Space secrets only need MODAL_URL — HF_TOKEN is for Space management only.

_MODAL_URL = os.environ.get('MODAL_URL', 'https://narwall-tech--color-ux-access-ui.modal.run')


def _call_modal_analyze(image_bytes: bytes, timeout: int = 120) -> dict:
    """
    Call the Modal Gradio endpoint's /analyze_screenshot API.
    Upload image → POST predict → poll SSE for result.

    Args:
        image_bytes: PNG/JPEG bytes of the screenshot.
        timeout: Max seconds to wait for VLM inference result.

    Returns:
        WCAG JSON dict with keys: findings, passes, summary.

    Raises:
        RuntimeError: If upload, predict, or polling fails.
    """
    gradio_api = f"{_MODAL_URL}/gradio_api"

    # Step 1: upload file → get server file path
    upload_resp = requests.post(
        f"{gradio_api}/upload",
        files={'files': ('screenshot.png', image_bytes, 'image/png')},
        timeout=30,
    )
    if upload_resp.status_code != 200:
        raise RuntimeError(f"Modal file upload failed: {upload_resp.status_code} {upload_resp.text[:100]}")

    file_paths = upload_resp.json()
    if not file_paths or len(file_paths) == 0:
        raise RuntimeError(f"Modal file upload returned no paths: {upload_resp.text[:100]}")

    file_path = file_paths[0]  # e.g. "/tmp/gradio/.../test.png"

    # Step 2: POST predict call → get event_id
    predict_resp = requests.post(
        f"{gradio_api}/call/analyze_screenshot",
        json={'data': [{'path': file_path, 'meta': {'_type': 'gradio.FileData'}}]},
        timeout=10,
    )
    if predict_resp.status_code != 200:
        raise RuntimeError(f"Modal predict call failed: {predict_resp.status_code} {predict_resp.text[:100]}")

    event_id = predict_resp.json().get('event_id')
    if not event_id:
        raise RuntimeError(f"Modal predict returned no event_id: {predict_resp.text[:100]}")

    # Step 3: poll SSE endpoint until result is ready
    poll_url = f"{gradio_api}/call/analyze_screenshot/{event_id}"
    with requests.get(poll_url, timeout=timeout, stream=True) as poll_resp:
        if poll_resp.status_code != 200:
            raise RuntimeError(f"Modal poll failed: {poll_resp.status_code}")

        full_data = ''
        for line in poll_resp.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith('data: '):
                    full_data = decoded[6:]  # strip 'data: ' prefix

        if not full_data:
            raise RuntimeError("Modal poll returned no data")

        result = json.loads(full_data)
        # Gradio API wraps the result in a JSON array: [dict]
        if isinstance(result, list):
            result = result[0]
        return result


# ── VLM Inference (via Modal) ──────────────────────────────────────────────────

def analyze_with_vlm(image_bytes: bytes, model: str = "aya-vision-32b") -> dict:
    """
    Analyze a screenshot for WCAG color-accessibility issues via Modal endpoint.

    Args:
        image_bytes: PNG/JPEG bytes of the screenshot.
        model: Model backend key from MODELS dict (aya-vision-32b, minicpm-v-4.6, nemotron-15b).
               Note: only aya-vision-32b is deployed on Modal; other options are for future use.

    Returns:
        WCAG JSON dict with keys: findings (list), passes (bool), summary (str).
        On error, returns {'error': str, 'findings': [], 'passes': False}.
    """
    try:
        return _call_modal_analyze(image_bytes)
    except Exception as e:
        return {'error': str(e), 'findings': [], 'passes': False}


# ── Gradio App ────────────────────────────────────────────────────────────────

# Theme + CSS — Gradio 6 moves these to launch(), but HF Spaces SDK installs Gradio 5.
# Use a try/except so the code works with both versions.
_theme_css = """
:root { --color-primary: #1E88E5; }
.gradio-container { font-family: 'Inter', Arial, sans-serif; }
"""

# Gradio version detection: SDK installs 5.0.0, local dev uses 6.x.
# Theme/css go to Blocks constructor (Gradio 5) or launch() (Gradio 6).
_gradio_version = tuple(int(x) for x in gr.__version__.split('.')[:2])
_is_gradio6 = _gradio_version >= (6, 0)

if _is_gradio6:
    # Gradio 6 — theme/css go to launch(), not Blocks constructor.
    _launch_theme = None
    _launch_css = None
else:
    # Gradio 5 — use Blocks constructor for theme and CSS.
    _launch_theme = gr.themes.Base(primary_hue='blue', secondary_hue='gray', neutral_hue='gray')
    _launch_css = _theme_css

with gr.Blocks(
    title='Color-UX-Access',
    # Gradio 5: theme/css go in constructor. Gradio 6: use launch() instead.
    **({"theme": _launch_theme, "css": _launch_css}
       if not _is_gradio6 else {}),
) as demo:

    gr.Markdown('# Color-UX-Access')
    gr.Markdown(
        '**Test any webpage for colorblind accessibility issues.**\n\n'
        '1. Capture your screen (OS/Browser screenshot tool)\n'
        '2. Upload the screenshot below\n'
        '3. Get CVD simulations + WCAG 2.1 accessibility report\n\n'
        '⚠️ First analysis takes ~60–90s (model loads once, then stays cached).'
    )

    with gr.Row():
        file_input = gr.File(
            label='Screenshot',
            file_types=['.png', '.jpg', '.jpeg', '.webp'],
            type='binary',
            height=80,
        )
        model_select = gr.Dropdown(
            choices=list(MODELS.keys()),
            value="aya-vision-32b",
            label='VLM Model',
            info='Switch models for different sponsor prize eligibility',
        )
        submit_btn = gr.Button('Analyze', variant='primary', scale=0)

    # Output row: original + CVD gallery
    with gr.Row():
        with gr.Column(scale=1):
            original_output = gr.Image(label='Original', type='pil')
        with gr.Column(scale=2):
            cvd_output = gr.Gallery(
                label='CVD Simulations (10 types)',
                columns=4,
                rows=3,
                object_fit='contain',
                height='auto',
            )

    report_output = gr.Markdown(label='Accessibility Report')

    # ── Event ──────────────────────────────────────────────────────────────────
    def run_analysis(file_obj, model: str = "aya-vision-32b"):
        """
        Two-stage pipeline:
          1. CVD simulation (CPU, instant) → gallery
          2. VLM inference (GPU, ~90s first call) → WCAG report
        Both run in the same function — GPU decorator wraps the whole thing.

        Args:
            file_obj: Uploaded file bytes or file-like object.
            model: VLM backend key from MODELS dict. Defaults to "aya-vision-32b".
        """
        if file_obj is None:
            return None, [], '⚠️ Please upload a screenshot first.'

        image_bytes = file_obj if isinstance(file_obj, bytes) else file_obj.read()

        # Stage 1: CVD simulations (CPU)
        try:
            original = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        except Exception as e:
            return None, [], f'⚠️ Could not open image: {e}'

        cvd_gallery = generate_cvd_gallery(original)

        # Stage 2: VLM inference (GPU via @spaces.GPU in Space context)
        # On HF Spaces, spaces.GPU is injected automatically.
        # Locally (no Space context), call analyze_with_vlm directly.
        try:
            vlm_result = analyze_with_vlm(image_bytes, model=model)
        except ValueError as e:
            return None, [], f'⚠️ {e}'
        except Exception as e:
            vlm_result = {'error': str(e), 'findings': [], 'passes': False}

        report_md = format_wcag_report(vlm_result)
        return original, cvd_gallery, report_md

    submit_btn.click(
        fn=run_analysis,
        inputs=[file_input, model_select],
        outputs=[original_output, cvd_output, report_output],
    )

    # ── Examples ───────────────────────────────────────────────────────────────
    gr.Markdown('---')
    gr.Markdown('### Example Screenshots')

    # TODO: Add real example screenshot URLs or embed small test images
    # These work only when the user uploads — no URL input on Space
    gr.Markdown('*Use the examples above to test locally, or upload your own screenshot.*')

    # Example: a minimal placeholder that demonstrates the UI
    gr.Examples(
        examples=[],  # Populate with example file paths or (filepath, label) tuples
        inputs=file_input,
        outputs=[original_output, cvd_output, report_output],
        fn=run_analysis,
        cache_examples=False,
    )


if __name__ == '__main__':
    # Gradio 6: theme/css go to launch(). Gradio 5: already in Blocks constructor.
    if _is_gradio6:
        demo.launch(
            server_name='0.0.0.0',
            server_port=7860,
            theme=gr.themes.Base(
                primary_hue='blue',
                secondary_hue='gray',
                neutral_hue='gray',
            ),
            css=_theme_css,
        )
    else:
        demo.launch(server_name='0.0.0.0', server_port=7860)