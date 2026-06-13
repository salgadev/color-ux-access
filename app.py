"""Color-UX-Access: Gradio app for colorblind accessibility testing.

IMPORTANT:
This file must NOT modify its own source code at runtime.
Do not add any logic that reads/writes app.py and does text replacements.
All UI changes must be implemented via Gradio components and event handlers.
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
    """Generate all 9 images: original + 8 CVD variant images from deficiency_config.
    
    First image is always the original (normal vision) for comparison.
    """
    gallery = [(original, "Normal vision (original design)")]
    for cvd_name, cfg in deficiency_config.items():
        sim = cfg['simulator']
        deficiency = cfg['deficiency']
        severity = cfg['severity']
        simulated = simulate_cvd(original, sim, deficiency, severity)
        # Format label: "Protanopia (red-blind)", "Deuteranomaly (green-weak)", etc.
        label = _cvd_name_to_label(cvd_name)
        gallery.append((simulated, label))
    return gallery


def _cvd_name_to_label(cvd_name: str) -> str:
    """Map deficiency_config key to human-readable label."""
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
    if 'error' in vlm_result:
        return f"**Error:** {vlm_result['error']}"

    cvd_label = vlm_result.get('cvd_label', '')
    if cvd_label:
        report = f"## WCAG Report: {cvd_label}\n\n"
    else:
        report = "## WCAG Accessibility Report\n\n"
    
    findings = vlm_result.get('findings', [])
    if not findings:
        if vlm_result.get('passes', False):
            return report + "Pass -- No accessibility issues detected."
        return report + "No accessibility issues detected."

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
        "Severe Protanopia (red-blind)": (
            "You have severe protanopia (complete red-blindness, severity 1.0). "
            "Analyze this page as it appears to you. "
            "Focus on WCAG 2.1 compliance issues for a protanope with no functional red cones: "
            "red-green color confusion, information conveyed solely by red, "
            "and contrast problems specific to your condition."
        ),
        "Severe Deuteranopia (green-blind)": (
            "You have severe deuteranopia (complete green-blindness, severity 1.0). "
            "Analyze this page as it appears to you. "
            "Focus on WCAG 2.1 compliance issues for a deuteranope with no functional green cones: "
            "green-red color confusion, information conveyed solely by green, "
            "and contrast problems specific to your condition."
        ),
        "Protanomaly (red-weak)": (
            "You have protanomaly (red-weak CVD, partial protanopia). "
            "Colors appear less bright and red/orange hues are shifted. "
            "Analyze this page as it appears to you. "
            "Focus on WCAG 2.1 compliance issues that affect someone with reduced red sensitivity: "
            "red-green color confusion (milder than protanopia), "
            "information conveyed solely by red, "
            "and contrast problems specific to your condition."
        ),
        "Deuteranomaly (green-weak)": (
            "You have deuteranomaly (green-weak CVD, the most common form of colorblindness). "
            "Colors appear less bright and green/yellow hues are shifted. "
            "Analyze this page as it appears to you. "
            "Focus on WCAG 2.1 compliance issues that affect someone with reduced green sensitivity: "
            "green-red color confusion (milder than deuteranopia), "
            "information conveyed solely by green, "
            "and contrast problems specific to your condition."
        ),
        "Tritanomaly (blue-weak)": (
            "You have tritanomaly (blue-weak CVD, partial tritanopia). "
            "Colors appear shifted and blue/violet hues are less distinct. "
            "Analyze this page as it appears to you. "
            "Focus on WCAG 2.1 compliance issues that affect someone with reduced blue sensitivity: "
            "blue-yellow color confusion (milder than tritanopia), "
            "information conveyed solely by blue, "
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


# -- VLM Caching ---------------------------------------------------------------

_vlm_cache: dict[tuple[str, str], dict] = {}
# Cache for merged VLM results, keyed by original image hash
_vlm_merged_cache: dict[str, dict] = {}


def _get_cache_key(img: Image.Image, label: str) -> tuple[str, str]:
    img_bytes = image_to_bytes(img)
    img_hash = hash(img_bytes)
    return (str(img_hash), label)


def _get_merged_cache_key(original_img: Image.Image) -> str:
    """Generate cache key for merged VLM results from original image."""
    img_bytes = image_to_bytes(original_img)
    return str(hash(img_bytes))


def analyze_single_perspective(img: Image.Image, label: str) -> dict:
    cache_key = _get_cache_key(img, label)
    if cache_key in _vlm_cache:
        cached = _vlm_cache[cache_key].copy()
        cached['cvd_label'] = label
        return cached
    
    role_prompt = _VLM_CVD_PROMPTS.get(label, _VLM_CVD_PROMPTS["Normal vision (original design)"])
    full_prompt = f"{role_prompt}\n\n{_ACCESSIBILITY_SYSTEM_PROMPT}"
    img_bytes = image_to_bytes(img)
    try:
        result = _call_minicpm_endpoint(img_bytes, full_prompt)
    except Exception as e:
        result = {"error": str(e), "findings": [], "passes": False}
    
    result['cvd_label'] = label
    _vlm_cache[cache_key] = result
    return result


def analyze_all_perspectives_with_cache(cvd_grid: list, progress=None) -> dict:
    """
    Run VLM analysis on each CVD perspective with per-perspective caching.
    Also caches the merged result keyed by the original image.
    """
    if progress:
        progress(0, desc="Preparing CVD simulation gallery...")
    
    # First image is always the original
    original_img = cvd_grid[0][0]
    merged_cache_key = _get_merged_cache_key(original_img)
    
    # Check merged cache first
    if merged_cache_key in _vlm_merged_cache:
        cached_merged = _vlm_merged_cache[merged_cache_key].copy()
        if progress:
            progress(1.0, desc="Loaded cached results")
        return cached_merged
    
    # Not cached - run full analysis with per-perspective caching
    results = {}
    for i, (img, label) in enumerate(cvd_grid):
        if progress:
            progress(0.1 + (0.7 * i / len(cvd_grid)), desc=f"Analyzing {label} ({i+1}/{len(cvd_grid)})...")
        # Use analyze_single_perspective which has its own cache
        result = analyze_single_perspective(img, label)
        results[label] = result
    
    merged = _merge_cvd_results(results)
    _vlm_merged_cache[merged_cache_key] = merged
    
    if progress:
        progress(0.9, desc="Formatting WCAG report...")
        progress(1.0, desc="Analysis complete")
    
    return merged


# -- Gradio App ---------------------------------------------------------------

_theme_css = """
:root { --color-primary: #1E88E5; }
.gradio-container { font-family: 'Inter', Arial, sans-serif; }
/* Gallery: fixed 4:3 aspect ratio per thumbnail, centered crop */
.gallery .grid-container .image-item,
.gallery .grid-container [data-testid="gallery"] .image-container {
    aspect-ratio: 4 / 3 !important;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
}
.gallery img {
    width: 100%;
    height: 100%;
    object-fit: cover !important;
    object-position: center center;
}
/* Caption labels: truncate long labels to 1 line */
.thumbnail-item .caption-label {
    font-size: 0.75rem;
    line-height: 1.2;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100%;
    text-align: center;
    display: block;
}
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
        '3. Click any image in the gallery to see its WCAG accessibility report\n\n'
        'The first image shows the original design. Clicking any image triggers VLM analysis '
        '(first click takes ~60-90s, subsequent clicks are instant from cache).\n\n'
        'Click each CVD variant to see how it appears to users with that type of colorblindness.'
    )

    with gr.Row():
        file_input = gr.File(
            label='Screenshot',
            file_types=['.png', '.jpg', '.jpeg', '.webp'],
            type='binary',
            height=80,
        )
        with gr.Column(scale=1):
            submit_btn = gr.Button('Analyze', variant='primary')
            status_output = gr.Markdown(
                value='*Ready — upload a screenshot and click Analyze*',
                visible=True,
            )

    with gr.Row():
            cvd_grid = gr.Gallery(
                label='Color-Vision Simulation Gallery (9 variants: original + 8 CVD)',
                columns=5,
                object_fit='cover',
                height=500,
            )
            report_output = gr.Markdown(
                label='Accessibility Report',
                value='*Upload a screenshot and click any image to see its WCAG report.*',
            )

            # State to hold the current CVD grid for VLM analysis
            current_cvd_grid = gr.State([])

            def handle_file_upload(file_obj):
                """On file upload: generate gallery images immediately (no VLM)."""
                if file_obj is None:
                    return [], gr.update()
                image_bytes = file_obj if isinstance(file_obj, bytes) else file_obj.read()
                try:
                    original = Image.open(io.BytesIO(image_bytes)).convert('RGB')
                except Exception as e:
                    return [], f'Could not open image: {e}'
                gallery = generate_cvd_gallery(original)
                return gallery, gallery

            def handle_gallery_select(evt, cvd_grid_state):
                """On gallery image click: run VLM on just that single perspective (cached)."""
                if not cvd_grid_state:
                    return "*No images loaded.*", ""
                
                index = evt.index if hasattr(evt, 'index') else 0
                if index >= len(cvd_grid_state):
                    return "*Invalid selection.*", ""
                
                img, label = cvd_grid_state[index]
                
                try:
                    vlm_result = analyze_single_perspective(img, label)
                except Exception as e:
                    vlm_result = {'error': str(e), 'findings': [], 'passes': False}
                
                return "", format_wcag_report(vlm_result)

            def run_vlm_analysis(cvd_grid_state, progress=gr.Progress()):
                """On Analyze click: run VLM on the pre-generated CVD grid with caching."""
                if not cvd_grid_state:
                    return 'Please upload a screenshot first.', '*No images loaded*'

                try:
                    vlm_result = analyze_all_perspectives_with_cache(cvd_grid_state, progress=progress)
                except Exception as e:
                    vlm_result = {'error': str(e), 'findings': [], 'passes': False}

                report = format_wcag_report(vlm_result)
                return report, "*Done — see report above*"

            # File upload triggers gallery generation immediately (no VLM)
            file_input.change(
                fn=handle_file_upload,
                inputs=file_input,
                outputs=[cvd_grid, current_cvd_grid],
            )

            # Gallery click triggers VLM on single image (cached after first call)
            cvd_grid.select(
                fn=handle_gallery_select,
                inputs=[current_cvd_grid],
                outputs=[report_output, report_output],
            )

            # Analyze button triggers VLM on all perspectives with progress
            # NOTE: This function and its click wiring are designed to keep
            # Gradio's loading spinner and/or progress UI working.
            submit_btn.click(
                fn=run_vlm_analysis,
                inputs=current_cvd_grid,
                outputs=[report_output, status_output],
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