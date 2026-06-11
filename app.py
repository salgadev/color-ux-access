"""
Color-UX-Access — Gradio application
=====================================
Single-file Gradio app for colorblind accessibility testing.
Only accepts user-uploaded screenshots (no URL capture / browser automation).

Architecture:
  Screenshot (file upload)
         |
         v
  Stage 1: CVD Simulation (CPU) -> 3-type comparison grid
         |
         v
  Stage 2: VLM Inference (GPU via Modal endpoint) -> WCAG 2.1 JSON
         |
         v
  Stage 3: Report (Markdown)

Requirements:
  - Python 3.12
  - gradio>=6.0, pillow, daltonlens, requests, python-dotenv

Local setup:
  uv sync --python 3.12
  cp .env.example .env  # set MODAL_INFERENCE_URL

HF Space deploy:
  1. Push to GitHub
  2. Create HF Space (SDK: Gradio, hardware: T4/mega or A10G)
  3. Add MODAL_INFERENCE_URL secret in Space settings
  4. Link to GitHub repo
"""

import os
import io
import json

import gradio as gr
from PIL import Image
import numpy as np
from daltonlens import simulate
import requests
import base64

from custom_theme import color_ux_access_theme

# -- Load .env if available ---------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# -- CVD Simulators -----------------------------------------------------------

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

SUPPORTED_MODEL = "minicpm-v-4.6"
_MODAL_INFERENCE_URL = os.environ.get('MODAL_INFERENCE_URL')


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

def generate_cvd_gallery(original: Image.Image) -> list[tuple[Image.Image, str]]:
    """Alias for generate_cvd_grid."""
    return generate_cvd_grid(original)

def generate_cvd_grid(original: Image.Image) -> list[tuple[Image.Image, str]]:
    """Generate the 2x2 CVD comparison grid.

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
        return f"Warning: {vlm_result['error']}"

    findings = vlm_result.get('findings', [])
    if not findings:
        if vlm_result.get('passes', False):
            return "Pass -- No accessibility issues detected."
        return "No accessibility issues detected."

    report = "## WCAG Accessibility Report\n\n"
    report += f"**Overall:** {'Pass' if vlm_result.get('passes', False) else 'Fail'}\n\n"

    severity_icons = {'critical': ':red_circle:', 'serious': ':orange_circle:', 'moderate': ':yellow_circle:'}
    wcag_links = {
        '1.1.1':  'https://www.w3.org/WAI/WCAG21/Understanding/non-text-content',
        '1.4.1':  'https://www.w3.org/WAI/WCAG21/Understanding/use-of-color',
        '1.4.3':  'https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum',
        '1.4.11': 'https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast',
    }

    for i, f in enumerate(findings, 1):
        icon = severity_icons.get(f.get('severity', 'moderate'))
        wcag = f.get('wcag_criterion', 'N/A')
        link = wcag_links.get(wcag, '#')
        cvd_perspective = f.get('cvd_perspective', '')
        report += f"### {icon} Issue {i}: {f.get('type', 'Unknown')}\n\n"
        report += f"- **WCAG:** [{wcag}]({link})\n"
        report += f"- **Severity:** {f.get('severity', 'N/A').capitalize()}\n"
        if cvd_perspective:
            report += f"- **CVD Perspective:** {cvd_perspective}\n"
        report += f"- **Description:** {f.get('description', 'N/A')}\n"
        report += f"- **Location:** {f.get('location', 'N/A')}\n\n"

    if vlm_result.get('summary'):
        report += f"**Summary:** {vlm_result['summary']}\n"

    return report


# -- VLM Inference ------------------------------------------------------------

_VLM_CVD_PROMPTS = {
    "Normal vision (original design)": (
        "You are an accessibility expert viewing this page with normal color vision. "
        "Analyze it for WCAG 2.1 compliance issues. "
        "Focus on contrast, color usage, and text readability as a fully sighted user."
    ),
    "Protanopia (red-blind)": (
        "You have protanopia (red-blind CVD). Analyze this page as it appears to you. "
        "Focus on WCAG 2.1 compliance issues that affect a protanope: "
        "red-green color confusion, information conveyed solely by red, "
        "and contrast problems specific to your condition."
    ),
    "Deuteranopia (green-blind)": (
        "You have deuteranopia (green-blind CVD). Analyze this page as it appears to you. "
        "Focus on WCAG 2.1 compliance issues that affect a deuteranope: "
        "green-red color confusion, information conveyed solely by green, "
        "and contrast problems specific to your condition."
    ),
    "Tritanopia (blue-blind)": (
        "You have tritanopia (blue-blind CVD). Analyze this page as it appears to you. "
        "Focus on WCAG 2.1 compliance issues that affect a tritanope: "
        "blue-yellow color confusion, information conveyed solely by blue, "
        "and contrast problems specific to your condition."
    ),
}

_ACCESSIBILITY_SYSTEM_PROMPT = (
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
    '  "summary": "Overall assessment from your perspective",\n'
    '  "passes": true/false\n'
    "}\n"
    "Return ONLY valid JSON -- no markdown fences, no commentary."
)


def _call_minicpm_endpoint(image_bytes: bytes, system_prompt: str) -> dict:
    """
    Call the MiniCPM vLLM endpoint on Modal directly.
    POST to MODAL_INFERENCE_URL with base64 image + accessibility prompt.
    """
    if not _MODAL_INFERENCE_URL:
        return {"error": "MODAL_INFERENCE_URL not set. Configure in .env or Space secrets.", "findings": [], "passes": False}

    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    payload = {"prompt": system_prompt, "image_base64": image_b64}

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


def _merge_cvd_results(results: dict[str, dict]) -> dict:
    """
    Merge VLM results from multiple CVD perspectives into a single report.

    Deduplicates findings by description (same issue flagged by multiple
    CVD types only appears once) and aggregates summaries.
    """
    all_findings = []
    summaries = []
    overall_passes = True

    for cvd_label, result in results.items():
        if "error" in result:
            summaries.append(f"{cvd_label}: {result['error']}")
            continue
        if not result.get("passes", False):
            overall_passes = False
        for finding in result.get("findings", []):
            finding["cvd_perspective"] = cvd_label
            all_findings.append(finding)
        if result.get("summary"):
            summaries.append(f"{cvd_label}: {result['summary']}")

    # Deduplicate by description hash
    seen = set()
    unique = []
    for f in all_findings:
        key = f.get("description", "")[:80]
        if key and key not in seen:
            seen.add(key)
            unique.append(f)

    return {
        "findings": unique,
        "summary": " | ".join(summaries) if summaries else "Multi-perspective analysis complete.",
        "passes": overall_passes,
    }


def analyze_all_perspectives(cvd_grid: list) -> dict:
    """
    Run VLM analysis on each CVD perspective sequentially.

    Each CVD variant gets a type-specific prompt so the model understands
    which color deficiency it's simulating. Results are merged into a
    single deduplicated report simulating a full panel of colorblind testers.
    """
    results = {}
    for img, label in cvd_grid:
        role_prompt = _VLM_CVD_PROMPTS.get(label, _VLM_CVD_PROMPTS["Normal vision (original design)"])
        full_prompt = f"{role_prompt}\n\n{_ACCESSIBILITY_SYSTEM_PROMPT}"
        img_bytes = image_to_bytes(img)
        result = _call_minicpm_endpoint(img_bytes, full_prompt)
        results[label] = result

    return _merge_cvd_results(results)


# -- Gradio App ---------------------------------------------------------------

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
        'The VLM analyzes **all four CVD perspectives** (Normal, Protanopia, Deuteranopia, '
        'Tritanopia) -- simulating a full panel of colorblind testers.\n\n'
        'Note: First analysis takes ~60-90s (MiniCPM cold-start on Modal GPU).'
    )

    with gr.Row():
        file_input = gr.File(
            label='Screenshot',
            file_types=['.png', '.jpg', '.jpeg', '.webp'],
            type='binary',
            height=80,
        )
        submit_btn = gr.Button('Analyze', variant='primary', scale=0)

    with gr.Row():
        cvd_grid = gr.Gallery(
            label='Color-Vision Comparison (2x2 grid)',
            columns=2,
            rows=2,
            object_fit='contain',
            height=600,
        )

    report_output = gr.Markdown(label='Accessibility Report')

    def run_analysis(file_obj):
        """File upload mode -- receives screenshot bytes, returns CVD grid + report."""
        if file_obj is None:
            return [], 'Please upload a screenshot first.'

        image_bytes = file_obj if isinstance(file_obj, bytes) else file_obj.read()

        try:
            original = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        except Exception as e:
            return [], f'Could not open image: {e}'

        grid = generate_cvd_grid(original)

        # Send ALL CVD perspectives to the VLM endpoint
        # Each variant gets a role-specific prompt (Normal, Protanopia, Deuteranopia, Tritanopia)
        try:
            vlm_result = analyze_all_perspectives(grid)
        except Exception as e:
            vlm_result = {'error': str(e), 'findings': [], 'passes': False}

        report_md = format_wcag_report(vlm_result)
        return grid, report_md

    submit_btn.click(
        fn=run_analysis,
        inputs=file_input,
        outputs=[cvd_grid, report_output],
    )


if __name__ == '__main__':
    if _is_gradio6:
        demo.launch(
            server_name='0.0.0.0',
            server_port=7860,
            theme=color_ux_access_theme,
            css=_theme_css,
        )
    else:
        demo.launch(server_name='0.0.0.0', server_port=7860)