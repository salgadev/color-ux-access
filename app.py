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
  Stage 1: CVD Simulation (CPU) → 10 variants
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
# One-line swap for different sponsor prize eligibility:
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
# Inference runs via the deployed Modal app, not HF Router directly.
# The Modal app (color_ux_access/modal_app.py) handles GPU/VLM internally.
# Space secrets only need MODAL_URL — HF_TOKEN is for Space management only.

_MODAL_URL = os.environ.get('MODAL_URL', 'https://narwall-tech--color-ux-access-ui.modal.run')

# Modal Inference Provider configuration
_MODAL_INFERENCE_BASE_URL = os.environ.get('MODAL_INFERENCE_BASE_URL', 'https://inference.modal.com/v1')
_MODAL_INFERENCE_API_KEY = os.environ.get('MODAL_INFERENCE_API_KEY')  # from modal secret modal-inference-key


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

    upload_resp = requests.post(
        f"{gradio_api}/upload",
        files={'files': ('screenshot.png', image_bytes, 'image/png')},
        timeout=30,
    )
    if upload_resp.status_code != 200:
        raise RuntimeError(f"Modal file upload failed: {upload_resp.status_code} {upload_resp.text[:100]}")

    file_paths = upload_resp.json()
    if not file_paths:
        raise RuntimeError(f"Modal file upload returned no paths: {upload_resp.text[:100]}")

    file_path = file_paths[0]

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

    poll_url = f"{gradio_api}/call/analyze_screenshot/{event_id}"
    with requests.get(poll_url, timeout=timeout, stream=True) as poll_resp:
        if poll_resp.status_code != 200:
            raise RuntimeError(f"Modal poll failed: {poll_resp.status_code}")

        full_data = ''
        for line in poll_resp.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith('data: '):
                    full_data = decoded[6:]

        if not full_data:
            raise RuntimeError("Modal poll returned no data")

        result = json.loads(full_data)
        if isinstance(result, list):
            result = result[0]
        return result


# ── VLM Inference (via Modal Inference Provider) ──────────────────────────────────────
def analyze_with_vlm(image_bytes: bytes, model: str = "aya-vision-32b") -> dict:
    """
    Analyze a screenshot for WCAG color-accessibility issues via Modal Inference Provider.
    """
    try:
        # Prepare OpenAI client pointing to Modal inference endpoint
        client = OpenAI(
            base_url=_MODAL_INFERENCE_BASE_URL,
            api_key=_MODAL_INFERENCE_API_KEY,
        )
        
        # Encode image to base64
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # System prompt from modal_app.py (adjusted)
        system_prompt = (
            "You are an accessibility expert specializing in colorblind user experience. "
            "Analyze screenshots for WCAG 2.1 compliance issues. "
            "For each finding, cite the specific success criterion (1.1.1, 1.4.1, 1.4.3, or 1.4.11). "
            "Output a JSON object with this structure:\n"
            "{\n"
            "  \"findings\": [\n"
            "    {\n"
            "      \"type\": \"Low Contrast | Color Only Information | Missing Text Alternative | Insufficient Non-Text Contrast\",\n"
            "      \"wcag_criterion\": \"1.4.1 | 1.4.3 | 1.1.1 | 1.4.11\",\n"
            "      \"description\": \"...\",\n"
            "      \"severity\": \"critical | serious | moderate\",\n"
            "      \"location\": \"Top-left, center, etc.\",\n"
            "    }\n"
            "  ],\n"
            "  \"summary\": \"Overall assessment\",\n"
            "  \"passes\": true/false\n"
            "}\n"
        )
        
        # Determine actual model ID from MODELS dict
        model_info = MODELS.get(model, {})
        model_id = model_info.get("model_id", model)  # fallback to model key
        
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": system_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                    ],
                }
            ],
            max_tokens=1024,
            temperature=0.1,
        )
        
        content = response.choices[0].message.content
        if content.startswith("```"):
            # Strip code fences if present
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])
        return json.loads(content)
    except Exception as e:
        return {"error": str(e), "findings": [], "passes": False}

# ── URL Mode Flag ──────────────────────────────────────────────────────────────
# Set --url on the command line to enable URL capture input.
# On HF Spaces, __file__ is set and --url is not passed, so URL mode stays off.

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
        '⚠️ First analysis takes ~60–90s (model loads once, then stays cached).'
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
            value="aya-vision-32b",
            label='VLM Model',
            info='Switch models for different sponsor prize eligibility',
        )

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

    # ── Event Handlers ─────────────────────────────────────────────────────────

    def run_analysis_from_file(file_obj, model: str = "aya-vision-32b"):
        """File upload mode — used on HF Spaces."""
        if file_obj is None:
            return None, [], '⚠️ Please upload a screenshot first.'

        image_bytes = file_obj if isinstance(file_obj, bytes) else file_obj.read()

        try:
            original = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        except Exception as e:
            return None, [], f'⚠️ Could not open image: {e}'

        cvd_gallery = generate_cvd_gallery(original)

        try:
            vlm_result = analyze_with_vlm(image_bytes, model=model)
        except Exception as e:
            vlm_result = {'error': str(e), 'findings': [], 'passes': False}

        report_md = format_wcag_report(vlm_result)
        return original, cvd_gallery, report_md

    def run_analysis_from_url(url: str, model: str = "aya-vision-32b"):
        """URL capture mode — Playwright local dev only."""
        if not url:
            return None, [], '⚠️ Please enter a URL first.'

        try:
            image_bytes = _capture_url(url)
        except Exception as e:
            return None, [], f'⚠️ Could not capture URL: {e}'

        try:
            original = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        except Exception as e:
            return None, [], f'⚠️ Could not open screenshot: {e}'

        cvd_gallery = generate_cvd_gallery(original)

        try:
            vlm_result = analyze_with_vlm(image_bytes, model=model)
        except Exception as e:
            vlm_result = {'error': str(e), 'findings': [], 'passes': False}

        report_md = format_wcag_report(vlm_result)
        return original, cvd_gallery, report_md

    if _url_mode:
        submit_btn.click(
            fn=run_analysis_from_url,
            inputs=[url_input, model_select],
            outputs=[original_output, cvd_output, report_output],
        )
        gr.Examples(
            examples=[
                ["https://www.google.com"],
                ["https://www.wikipedia.org"],
                ["https://www.apple.com"],
            ],
            inputs=url_input,
            outputs=[original_output, cvd_output, report_output],
            fn=run_analysis_from_url,
            cache_examples=False,
        )
    else:
        submit_btn.click(
            fn=run_analysis_from_file,
            inputs=[file_input, model_select],
            outputs=[original_output, cvd_output, report_output],
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