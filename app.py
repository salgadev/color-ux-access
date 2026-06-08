"""
Color-UX-Access — Gradio application
=====================================
Single-file Gradio app for colorblind accessibility testing.

Usage:
  # HF Spaces (file upload only — no Playwright needed):
  # app_file: app.py in Space settings → runs automatically

  # Local development (file upload OR URL capture):
  python app.py                      # file upload mode

Architecture:
  Screenshot (file upload)
         │
         ▼
  Stage 1: CVD Simulation (CPU) → 3-type comparison grid
         │
         ▼
  Stage 2: VLM Inference (GPU via Modal endpoint) → WCAG 2.1 JSON
         │
         ▼
  Stage 3: Report (Markdown)

Requirements:
  - Python 3.12
  - gradio>=6.0, spaces (for HF Space deployment)
  - torch with CUDA libs
  - openai, pillow, daltonlens, requests, python-dotenv
  - huggingface_hub==0.25.2 (HfFolder removed in 0.26)
  - playwright (optional, for URL capture mode — not needed on Space)

Local setup:
  uv sync --python 3.12
  playwright install chromium   # only for --url mode

HF Space deploy:
  1. Push to GitHub
  2. Create HF Space (SDK: Gradio, hardware: T4/mega or A10G)
  3. Add MODAL_URL secret in Space settings
  4. Link to GitHub repo

Note: HF_TOKEN in Space secrets is for Space management only.
Inference goes through the Modal endpoint — no HF_TOKEN needed here.

Two VLM modes:
  A) MiniCPM direct — MODAL_INFERENCE_URL (custom POST endpoint)
  B) Legacy        — MODAL_URL (Gradio API endpoint)
"""

import os
import io
import json
import sys

import gradio as gr
from PIL import Image
import numpy as np
from daltonlens import simulate
import requests
import base64
from openai import OpenAI

# ── Load .env if available ────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── CVD Simulators ────────────────────────────────────────────────────────────

simulator = simulate.Simulator_Machado2009()
severe_simulator = simulate.Simulator_Vienot1999()
tritan_simulator = simulate.Simulator_Brettel1997()

deficiency_config = {
    'protanopia':        {'simulator': simulator,        'severity': 0.8, 'deficiency': simulate.Deficiency.PROTAN},
    'severe_protanopia': {'simulator': severe_simulator, 'severity': 1.0, 'deficiency': simulate.Deficiency.PROTAN},
    'deuteranopia':      {'simulator': simulator,        'severity': 0.8, 'deficiency': simulate.Deficiency.DEUTAN},
    'severe_deuteranopia':{'simulator': severe_simulator,'severity': 1.0, 'deficiency': simulate.Deficiency.DEUTAN},
    'tritanopia':        {'simulator': tritan_simulator, 'severity': 0.8, 'deficiency': simulate.Deficiency.TRITAN},
    'protanomaly':       {'simulator': simulator,        'severity': 0.4, 'deficiency': simulate.Deficiency.PROTAN},
    'deuteranomaly':     {'simulator': simulator,        'severity': 0.4, 'deficiency': simulate.Deficiency.DEUTAN},
    'tritanomaly':       {'simulator': tritan_simulator, 'severity': 0.4, 'deficiency': simulate.Deficiency.TRITAN},
}

# ── Swappable VLM Model Registry ──────────────────────────────────────────────
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


def image_to_bytes(img: Image.Image, fmt: str = 'PNG') -> bytes:
    """Serialize a PIL Image to bytes for VLM transmission."""
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def generate_cvd_grid(original: Image.Image) -> list[tuple[Image.Image, str]]:
    """Generate the 2×2 CVD comparison grid.

    Fixed layout:
      Top-left:     Normal vision (original design)
      Top-right:    Protanopia (red-blind)
      Bottom-left:  Deuteranopia (green-blind)
      Bottom-right: Tritanopia (blue-blind)
    """
    protan = simulate_cvd(original, simulator, simulate.Deficiency.PROTAN, 0.8)
    deuter = simulate_cvd(original, simulator, simulate.Deficiency.DEUTAN, 0.8)
    tritan = simulate_cvd(original, tritan_simulator, simulate.Deficiency.TRITAN, 0.8)
    return [
        (original, "Normal vision (original design)"),
        (protan,   "Protanopia (red-blind)"),
        (deuter,   "Deuteranopia (green-blind)"),
        (tritan,   "Tritanopia (blue-blind)"),
    ]


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
        '1.1.1':  'https://www.w3.org/WAI/WCAG21/Understanding/non-text-content',
        '1.4.1':  'https://www.w3.org/WAI/WCAG21/Understanding/use-of-color',
        '1.4.3':  'https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum',
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


# ── URL Capture (optional — Playwright, local dev only) ───────────────────────

def _get_playwright():
    """Lazy-import Playwright only when URL mode is requested."""
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright not installed. Run: uv pip install playwright && playwright install chromium"
        )


def _capture_url(url: str) -> bytes:
    """Capture a screenshot of a URL using Playwright (headless Chromium)."""
    pw = _get_playwright()
    with pw() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox'],
        )
        page = browser.new_page(viewport={'width': 1280, 'height': 720})
        page.goto(url, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(3000)
        screenshot = page.screenshot(full_page=True, timeout=60000)
        browser.close()
    return screenshot


# ── Modal Endpoint Helper ──────────────────────────────────────────────────────

_MODAL_URL = os.environ.get('MODAL_URL', 'https://narwall-tech--color-ux-access-ui.modal.run')

# Direct MiniCPM vLLM endpoint (custom POST — not OpenAI-compatible)
_MODAL_INFERENCE_URL = os.environ.get('MODAL_INFERENCE_URL')

# ── Accessibility System Prompt ────────────────────────────────────────────────

_ACCESSIBILITY_PROMPT = (
    "You are an accessibility expert specializing in colorblind user experience. "
    "Analyze screenshots for WCAG 2.1 compliance issues. "
    "For each finding, cite the specific success criterion (1.1.1, 1.4.1, 1.4.3, or 1.4.11). "
    "Output a JSON object with this structure:\n"
    "{\n"
    '  "findings": [\n'
    "    {\n"
    '      "type": "Low Contrast | Color Only Information | Missing Text Alternative | Insufficient Non-Text Contrast",\n'
    '      "wcag_criterion": "1.4.1 | 1.4.3 | 1.1.1 | 1.4.11",\n'
    '      "description": "...",\n'
    '      "severity": "critical | serious | moderate",\n'
    '      "location": "Top-left, center, etc."\n'
    "    }\n"
    "  ],\n"
    '  "summary": "Overall assessment",\n'
    '  "passes": true/false\n'
    "}\n"
    "Return ONLY valid JSON — no markdown fences, no commentary."
)


# ── VLM Inference Functions ───────────────────────────────────────────────────


def _call_minicpm_endpoint(image_bytes: bytes) -> dict:
    """
    Call the MiniCPM vLLM endpoint on Modal directly.
    POST to MODAL_INFERENCE_URL with base64 image + accessibility prompt.
    Image bytes MUST be a CVD-simulated version (protanopia), not the original.
    """
    if not _MODAL_INFERENCE_URL:
        return {"error": "MODAL_INFERENCE_URL not set. Configure in .env or Space secrets.", "findings": [], "passes": False}

    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    payload = {"prompt": _ACCESSIBILITY_PROMPT, "image_base64": image_b64}

    try:
        resp = requests.post(_MODAL_INFERENCE_URL, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return {"error": "MiniCPM endpoint timed out (cold-start may need ~90s). Try again.", "findings": [], "passes": False}
    except Exception as e:
        return {"error": f"MiniCPM endpoint call failed: {e}", "findings": [], "passes": False}

    raw = data.get("response", "")
    if not raw:
        return {"error": "MiniCPM returned empty response", "findings": [], "passes": False}

    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1])

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": f"MiniCPM returned non-JSON: {raw[:500]}", "findings": [], "passes": False}


def analyze_with_vlm(image_bytes: bytes, model: str = "minicpm-v-4.6") -> dict:
    """
    Analyze a CVD-simulated screenshot for WCAG color-accessibility issues.

    Accepts CVD-simulated image bytes (protanopia by default) — the VLM sees
    the page the way a colorblind user would.
    """
    # Route: MiniCPM vLLM endpoint (custom POST, not OpenAI-compatible)
    if model == "minicpm-v-4.6" and _MODAL_INFERENCE_URL:
        return _call_minicpm_endpoint(image_bytes)

    return {"error": f"No endpoint available for model '{model}'", "findings": [], "passes": False}


# ── URL Mode Flag ──────────────────────────────────────────────────────────────

_url_mode = '--url' in sys.argv


# ── Gradio App ────────────────────────────────────────────────────────────────

_theme_css = """
:root { --color-primary: #1E88E5; }
.gradio-container { font-family: 'Inter', Arial, sans-serif; }
"""

_gradio_version = tuple(int(x) for x in gr.__version__.split('.')[:2])
_is_gradio6 = _gradio_version >= (6, 0)

if _is_gradio6:
    _launch_theme = None
    _launch_css = None
else:
    _launch_theme = gr.themes.Base(primary_hue='blue', secondary_hue='gray', neutral_hue='gray')
    _launch_css = _theme_css

with gr.Blocks(
    title='Color-UX-Access',
    **({"theme": _launch_theme, "css": _launch_css} if not _is_gradio6 else {}),
) as demo:

    gr.Markdown('# Color-UX-Access')
    gr.Markdown(
        '**Test any webpage for colorblind accessibility issues.**\n\n'
        '1. Capture your screen (OS/Browser screenshot tool)\n'
        '2. Upload the screenshot below\n'
        '3. Get CVD simulations + WCAG 2.1 accessibility report\n\n'
        '⚠️ First analysis takes ~60–90s (model loads once, then stays cached).\n\n'
        'The VLM analyzes a **Protanopia simulation** of your screenshot — it sees your design '
        'the way a red-blind user would, and flags WCAG issues from that perspective.'
    )

    with gr.Row():
        if _url_mode:
            url_input = gr.Textbox(label='Website URL', placeholder='https://example.com', scale=1)
            submit_btn = gr.Button('Capture & Analyze', variant='primary', scale=0)
        else:
            file_input = gr.File(
                label='Screenshot',
                file_types=['.png', '.jpg', '.jpeg', '.webp'],
                type='binary',
                height=80,
            )
            submit_btn = gr.Button('Analyze', variant='primary', scale=0)

        model_select = gr.Dropdown(
            choices=list(MODELS.keys()),
            value="minicpm-v-4.6",
            label='VLM Model',
            info='Switch models for different sponsor prize eligibility',
        )

    with gr.Row():
        cvd_grid = gr.Gallery(
            label='Color‑Vision Comparison (2×2 grid)',
            columns=2,
            rows=2,
            object_fit='contain',
            height=600,
        )

    report_output = gr.Markdown(label='Accessibility Report')

    # ── Event Handlers ─────────────────────────────────────────────────────────

    def run_analysis_from_file(file_obj, model: str = "minicpm-v-4.6"):
        """File upload mode — used on HF Spaces."""
        if file_obj is None:
            return [], '⚠️ Please upload a screenshot first.'

        image_bytes = file_obj if isinstance(file_obj, bytes) else file_obj.read()

        try:
            original = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        except Exception as e:
            return [], f'⚠️ Could not open image: {e}'

        # Generate the 2×2 CVD grid
        cvd_grid = generate_cvd_grid(original)

        # Send the PROTANOPIA simulation to the VLM endpoint
        # (row index 1 in the grid = protanopia)
        protan_img = cvd_grid[1][0]
        cvd_bytes = image_to_bytes(protan_img)

        try:
            vlm_result = analyze_with_vlm(cvd_bytes, model=model)
        except Exception as e:
            vlm_result = {'error': str(e), 'findings': [], 'passes': False}

        report_md = format_wcag_report(vlm_result)
        return cvd_grid, report_md

    def run_analysis_from_url(url: str, model: str = "minicpm-v-4.6"):
        """URL capture mode — Playwright local dev only."""
        if not url:
            return [], '⚠️ Please enter a URL first.'

        try:
            image_bytes = _capture_url(url)
        except Exception as e:
            return [], f'⚠️ Could not capture URL: {e}'

        try:
            original = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        except Exception as e:
            return [], f'⚠️ Could not open screenshot: {e}'

        cvd_grid = generate_cvd_grid(original)

        # Send the PROTANOPIA simulation to the VLM endpoint
        protan_img = cvd_grid[1][0]
        cvd_bytes = image_to_bytes(protan_img)

        try:
            vlm_result = analyze_with_vlm(cvd_bytes, model=model)
        except Exception as e:
            vlm_result = {'error': str(e), 'findings': [], 'passes': False}

        report_md = format_wcag_report(vlm_result)
        return cvd_grid, report_md

    if _url_mode:
        submit_btn.click(
            fn=run_analysis_from_url,
            inputs=[url_input, model_select],
            outputs=[cvd_grid, report_output],
        )
        gr.Examples(
            examples=[
                ["https://www.google.com"],
                ["https://www.wikipedia.org"],
                ["https://www.apple.com"],
            ],
            inputs=url_input,
            outputs=[cvd_grid, report_output],
            fn=run_analysis_from_url,
            cache_examples=False,
        )
    else:
        submit_btn.click(
            fn=run_analysis_from_file,
            inputs=[file_input, model_select],
            outputs=[cvd_grid, report_output],
        )
        gr.Markdown('---')
        gr.Markdown('*Upload a screenshot or use URL capture mode (`python app.py --url`).*')


if __name__ == '__main__':
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