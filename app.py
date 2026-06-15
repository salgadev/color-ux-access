"""Color-UX-Access: Gradio app for colorblind accessibility testing.

IMPORTANT:
This file must NOT modify its own source code at runtime.
Do not add any logic that reads/writes app.py and does text replacements.
All UI changes must be implemented via Gradio components and event handlers.
"""

import os
import io
import json
import threading
import concurrent.futures

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


def _resize_for_vlm(img: Image.Image, max_side: int = 1024) -> Image.Image:
    """Downscale image so the longest side is at most max_side pixels.

    Keeps aspect ratio. Reduces base64 payload size ~3× for typical 1920×1080
    screenshots without degrading VLM accessibility assessment quality.
    """
    w, h = img.size
    if w <= max_side and h <= max_side:
        return img
    if w >= h:
        new_w = max_side
        new_h = int(h * max_side / w)
    else:
        new_h = max_side
        new_w = int(w * max_side / h)
    return img.resize((new_w, new_h), Image.LANCZOS)


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

    perception_summary = (vlm_result.get('perception_summary') or '').strip()
    if perception_summary:
        report += f"> **👁️ VLM perception:** {perception_summary}\n\n"
    else:
        report += "\n"

    report += "### WCAG-style assessment\n\n"

    findings = vlm_result.get('findings', [])
    if not findings:
        status = 'Pass' if vlm_result.get('passes', False) else 'Fail'
        report += f"**Overall:** {status} — No accessibility issues detected.\n"
        return report

    report += f"**Overall:** {'Pass' if vlm_result.get('passes', False) else 'Fail'}\n\n"
    severity_icons = {'critical': '🔴', 'serious': '🟠', 'moderate': '🟡'}
    wcag_links = {
        '1.1.1':  'https://www.w3.org/WAI/WCAG21/Understanding/non-text-content',
        '1.4.1':  'https://www.w3.org/WAI/WCAG21/Understanding/use-of-color',
        '1.4.3':  'https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum',
        '1.4.11': 'https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast',
    }

    for i, f in enumerate(findings, 1):
        icon = severity_icons.get(f.get('severity', 'moderate'), '🟡')
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


def _format_cvd_perception_comparison_summary(
    original_vlm: dict | None,
    cvd_results: dict[str, dict],
) -> str:
    """Heuristic comparison of VLM perception summaries and pass states."""
    lines = ["## Color-vision comparison (heuristic)\n\n", "| Perspective | VLM perception | Pass |\n", "|-------------|----------------|------|\n"]

    entries: list[tuple[str, dict]] = []
    if original_vlm is not None:
        entries.append(("Original design", original_vlm))
    for label, result in cvd_results.items():
        entries.append((label, result))

    for label, result in entries:
        perception = (result.get("perception_summary", "") or "").strip()
        if not perception:
            perception = "—"
        passes = "✅ Pass" if result.get("passes", False) else "❌ Fail"
        lines.append(f"| {label} | {perception} | {passes} |\n")

    all_pass = all(result.get("passes", False) for _, result in entries)
    lines.append(f"\n**Overall:** {'Heuristic pass' if all_pass else 'Heuristic fail'} — not a substitute for full WCAG audit.")
    return "".join(lines)


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
    "You are an accessibility expert analyzing a webpage screenshot from the perspective "
    "of a colorblind user to infer likely WCAG-style issues for that vision type only. "
    "Respond with a single JSON object and nothing else (no markdown, no comments). "
    "JSON shape:\n"
    "{\n"
    '  "perception_summary": "One short sentence on how easy or hard it is to understand important information without relying on color from this CVD perspective.",\n'
    '  "findings": [\n'
    "    {\n"
    '      "type": "Low Contrast | Color Only Information | Missing Text Alternative | Insufficient Non-Text Contrast",\n'
    '      "wcag_criterion": "1.4.1 | 1.4.3 | 1.1.1 | 1.4.11",\n'
    '      "description": "...",\n'
    '      "severity": "critical | serious | moderate",\n'
    '      "location": "Top-left, center, etc."\n'
    "    }\n"
    "  ],\n"
    '  "summary": "1-2 sentence overall assessment from this CVD perspective.",\n'
    '  "passes": true/false\n'
    "}\n"
)


def _validate_vlm_result(result: dict) -> dict:
    """Enforce the expected VLM response schema.

    Raises ValueError if required fields are missing or have wrong types.
    """
    if "perception_summary" not in result:
        raise ValueError('missing field: "perception_summary"')
    if not isinstance(result["perception_summary"], str):
        raise ValueError('"perception_summary" must be a string')

    if "findings" not in result:
        raise ValueError('missing field: "findings"')
    if not isinstance(result["findings"], list):
        raise ValueError('"findings" must be an array')

    allowed_finding_fields = {"type", "wcag_criterion", "description", "severity", "location", "cvd_perspective"}
    for idx, finding in enumerate(result["findings"]):
        if not isinstance(finding, dict):
            raise ValueError(f'findings[{idx}] must be an object')
        for key in finding:
            if key not in allowed_finding_fields:
                raise ValueError(f'findings[{idx}] has unsupported field: {key}')

    if "summary" not in result:
        raise ValueError('missing field: "summary"')
    if not isinstance(result["summary"], str):
        raise ValueError('"summary" must be a string')

    if "passes" not in result:
        raise ValueError('missing field: "passes"')
    if not isinstance(result["passes"], bool):
        raise ValueError('"passes" must be a boolean')

    return result


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
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {"error": f"MiniCPM returned non-JSON: {raw[:500]}", "findings": [], "passes": False}

    normalized = {
        "perception_summary": result.get("perception_summary") or "",
        "findings": result.get("findings", []),
        "summary": result.get("summary", ""),
        "passes": result.get("passes", False),
    }
    try:
        return _validate_vlm_result(normalized)
    except ValueError as exc:
        return {"error": f"Invalid VLM JSON schema: {exc}", "findings": [], "passes": False}


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


# -- CVD Image Cache -----------------------------------------------------------
# Cache for CVD-transformed images, keyed by (original_image_hash, cvd_variant)
_cvd_image_cache: dict[tuple[str, str], Image.Image] = {}


def _get_cvd_cache_key(img: Image.Image, variant: str) -> tuple[str, str]:
    """Generate cache key for CVD-transformed image."""
    img_bytes = image_to_bytes(img)
    img_hash = hash(img_bytes)
    return (str(img_hash), variant)


def get_cvd_transformed(original: Image.Image, variant: str) -> Image.Image:
    """
    Get CVD-transformed image, using cache if available.

    Args:
        original: Original PIL Image
        variant: CVD variant key from deficiency_config

    Returns:
        CVD-simulated PIL Image
    """
    cache_key = _get_cvd_cache_key(original, variant)
    if cache_key in _cvd_image_cache:
        return _cvd_image_cache[cache_key]

    # Generate transformed image
    if variant == 'achromatopsia':
        # Not in deficiency_config, use simulate_achromatopsia
        transformed = simulate_achromatopsia(original, 1.0)
    else:
        cfg = deficiency_config[variant]
        transformed = simulate_cvd(original, cfg['simulator'], cfg['deficiency'], cfg['severity'])

    _cvd_image_cache[cache_key] = transformed
    return transformed


def _get_cache_key(img: Image.Image, label: str) -> tuple[str, str]:
    img_bytes = image_to_bytes(img)
    img_hash = hash(img_bytes)
    return (str(img_hash), label)


def _get_merged_cache_key(original_img: Image.Image) -> str:
    """Generate cache key for merged VLM results from original image."""
    img_bytes = image_to_bytes(original_img)
    return str(hash(img_bytes))


def analyze_single_perspective(img: Image.Image, label: str) -> dict:
    """Analyze a single CVD perspective via VLM with caching.

    Resizes images to 1024px max side before transmission
    to reduce latency without sacrificing assessment quality.
    """
    img = _resize_for_vlm(img)
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
    # Don't cache error results — next click should retry, not show stale error
    if 'error' not in result:
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

    # Check merged cache first — but skip if cached result has errors
    if merged_cache_key in _vlm_merged_cache:
        cached_merged = _vlm_merged_cache[merged_cache_key].copy()
        if 'error' not in cached_merged:
            if progress:
                progress(1.0, desc="Loaded cached results")
            return cached_merged
        # Stale error in cache — remove and retry
        del _vlm_merged_cache[merged_cache_key]

    # Not cached - run full analysis with parallel VLM calls
    results = {}

    # Check per-perspective cache to avoid redundant calls
    uncached: list[tuple] = []
    for img, label in cvd_grid:
        cache_key = _get_cache_key(img, label)
        if cache_key in _vlm_cache:
            cached = _vlm_cache[cache_key].copy()
            cached['cvd_label'] = label
            results[label] = cached
        else:
            uncached.append((img, label))

    if uncached:
        if progress:
            progress(0.1, desc=f"Analyzing {len(uncached)}/{len(cvd_grid)} perspectives in parallel...")

        progress_lock = threading.Lock()
        completed = [0]

        def _analyze_and_progress(img, label):
            result = analyze_single_perspective(img, label)
            with progress_lock:
                completed[0] += 1
                if progress:
                    pct = 0.1 + (0.7 * completed[0] / len(cvd_grid))
                    progress(pct, desc=f"Analyzed {label} ({completed[0]}/{len(cvd_grid)})")
            return label, result

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(uncached)) as pool:
            futures = [pool.submit(_analyze_and_progress, img, label) for img, label in uncached]
            for future in concurrent.futures.as_completed(futures):
                label, result = future.result()
                results[label] = result
    else:
        if progress:
            progress(0.8, desc="All perspectives loaded from cache")

    merged = _merge_cvd_results(results)
    # Don't cache merged results that contain errors — next click should retry
    if 'error' not in merged:
        _vlm_merged_cache[merged_cache_key] = merged

    if progress:
        progress(0.9, desc="Formatting WCAG report...")
        progress(1.0, desc="Analysis complete")

    return merged


# -- Gradio App ---------------------------------------------------------------

_theme_css = """
/* Comparison Grid: perspective cards layout */
.comparison-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    width: 100%;
    max-width: 100%;
    overflow-x: hidden;
    box-sizing: border-box;
}

.perspective-card {
    display: flex;
    flex-direction: column;
    min-width: 0;
    border: 1px solid var(--border-color-primary, #e0e0e0);
    border-radius: 12px;
    background: var(--background-fill-primary, #fff);
    overflow: hidden;
    box-sizing: border-box;
}

.perspective-card-header {
    padding: 0.75rem 1rem;
    background: var(--background-fill-secondary, #fafafa);
    border-bottom: 1px solid var(--border-color-primary, #e0e0e0);
    font-weight: 600;
    font-size: 0.875rem;
    color: var(--body-text-color, #1f1f1f);
    text-align: center;
    flex-shrink: 0;
    word-break: break-word;
    white-space: normal;
}

.perspective-card-image {
    flex: 1;
    min-height: 0;
    overflow: auto;
    background: var(--background-fill-secondary, #fafafa);
    display: flex;
    align-items: center;
    justify-content: center;
}

.perspective-card-image img {
    width: 100%;
    aspect-ratio: 4 / 3;
    object-fit: contain;
    display: block;
}

.perspective-card-report {
    padding: 1rem;
    min-height: 180px;
    max-height: 300px;
    overflow: auto;
    border-top: 1px solid var(--border-color-primary, #e0e0e0);
    font-size: 0.8rem;
    line-height: 1.5;
}

/* CVD Gallery: scoped selectors (replaces internal Gradio selectors) */
.cvd-gallery img {
    width: 100%;
    aspect-ratio: 4 / 3;
    object-fit: cover;
    object-position: center center;
}
.cvd-gallery .image-item,
.cvd-gallery .image-container {
    aspect-ratio: 4 / 3 !important;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
}
/* Caption labels: truncate long labels to 1 line */
.cvd-gallery .caption-label {
    font-size: 0.75rem;
    line-height: 1.2;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100%;
    text-align: center;
    display: block;
}

/* Responsive breakpoints for comparison grid */
@media (max-width: 1024px) {
    .comparison-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: 1rem;
    }
    .perspective-card-report {
        max-height: 220px;
    }
}

@media (max-width: 600px) {
    .comparison-grid {
        grid-template-columns: 1fr;
        gap: 0.75rem;
    }
    .perspective-card-report {
        max-height: 200px;
        padding: 0.75rem;
        font-size: 0.75rem;
    }
}

@media (max-width: 480px) {
    .comparison-grid {
        gap: 0.5rem;
    }
    .perspective-card-report {
        max-height: none;
        overflow: visible;
        padding: 0.5rem;
        font-size: 0.75rem;
    }
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

    # 1. Title/description wrapped in a top-level Group
    with gr.Group():
        gr.Markdown('# Color-UX-Access')
        gr.Markdown(
            '**Test any webpage for colorblind accessibility issues.**\n\n'
            '1. Capture your screen (OS/Browser screenshot tool)\n'
            '2. Upload the screenshot below\n'
            '3. The comparison grid shows all 9 perspectives simultaneously\n'
            '4. Each card has: label, CVD-simulated image, and WCAG results placeholder\n'
            '5. Click Analyze to run WCAG evaluation for all perspectives\n\n'
            'All perspectives render on upload — no tab switching required.'
        )

    # 2. Top controls row: file upload (scale=2), Analyze button (scale=1, min_width=120), status (scale=3)
    with gr.Row():
        file_input = gr.File(
            label='Screenshot',
            file_types=['.png', '.jpg', '.jpeg', '.webp'],
            type='binary',
            height=80,
            scale=2,
        )
        submit_btn = gr.Button('Analyze', variant='primary', scale=1, min_width=120)
        with gr.Column(scale=3):
            status_output = gr.Markdown(
                value='*Ready — upload a screenshot and click Analyze*',
                visible=True,
            )

    # 3. Comparison grid: Row with Column(scale=12) holding 9 perspective cards
    perspective_labels = [
        "Normal vision (original design)",
        "Protanopia (red-blind)",
        "Severe Protanopia (red-blind)",
        "Deuteranopia (green-blind)",
        "Severe Deuteranopia (green-blind)",
        "Tritanopia (blue-blind)",
        "Protanomaly (red-weak)",
        "Deuteranomaly (green-weak)",
        "Tritanomaly (blue-weak)",
    ]

    with gr.Row():
        with gr.Column(scale=12, elem_classes=['comparison-grid'], visible=False) as comparison_grid_container:
            perspective_images = []
            perspective_reports = []
            for label in perspective_labels:
                with gr.Group(elem_classes=['perspective-card']):
                    gr.Markdown(f'### {label}', elem_classes=['perspective-card-header'])
                    img_comp = gr.Image(
                        label=label,
                        type='pil',
                        show_label=False,
                        container=False,
                        elem_classes=['perspective-card-image'],
                    )
                    perspective_images.append(img_comp)
                    report_comp = gr.Markdown(
                        label=f'WCAG — {label}',
                        value=f'*{label} — WCAG results will appear after clicking Analyze*',
                        container=False,
                        elem_classes=['perspective-card-report'],
                    )
                    perspective_reports.append(report_comp)

    # 4. CVD Gallery (hidden, kept for backward compatibility) with elem_classes
    cvd_grid = gr.Gallery(
        label='Color-Vision Simulation Gallery (9 variants: original + 8 CVD)',
        columns=5,
        object_fit='cover',
        height=300,
        visible=False,
        elem_classes=['cvd-gallery'],
        elem_id='cvd-gallery',
    )

    # 5. WCAG comparison Markdown below the grid in its own Row/Column
    with gr.Row():
        with gr.Column():
            wcag_comparison_output = gr.Markdown(
                label='WCAG Comparison: Original vs CVD',
                value='*Run Analyze to see side-by-side criterion comparison.*',
            )

    # State
    current_cvd_grid = gr.State([])
    current_original = gr.State(None)
    # Store individual perspective VLM results for comparison panel
    current_original_vlm = gr.State(None)  # VLM result for original perspective
    current_cvd_results = gr.State({})     # Dict of CVD label -> VLM result

    def handle_file_upload(file_obj):
        """On file upload: generate gallery images and populate all perspective cards."""
        if file_obj is None:
            # Return empty states for all outputs
            empty_gallery = []
            empty_cvd_grid = []
            empty_values = [None] * 9 + [''] * 9
            empty_comparison = '*Run Analyze to see side-by-side criterion comparison.*'
            return [empty_gallery, empty_cvd_grid, gr.update(visible=True)] + empty_values + [empty_comparison]
        
        image_bytes = file_obj if isinstance(file_obj, bytes) else file_obj.read()
        try:
            original = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        except Exception as e:
            empty_gallery = []
            empty_cvd_grid = []
            error_msg = f'Could not open image: {e}'
            empty_values = [None] * 9 + [''] * 9
            return [empty_gallery, empty_cvd_grid, gr.update(visible=True)] + empty_values + [error_msg]
        
        gallery = generate_cvd_gallery(original)
        # gallery has 9 entries: original + 8 CVD variants
        # Return gallery for cvd_grid (hidden), state, grid container visible,
        # then 9 card images, 9 card reports, comparison output
        
        card_images = []
        card_reports = []
        for img, label in gallery:
            card_images.append(img)
            card_reports.append(f'*{label} — WCAG results will appear after clicking Analyze*')
        
        empty_comparison = '*Run Analyze to see side-by-side criterion comparison.*'
        return [gallery, gallery, gr.update(visible=True)] + card_images + card_reports + [empty_comparison]

    def run_vlm_analysis(cvd_grid_state, progress=gr.Progress()):
        """On Analyze click: run VLM on the pre-generated CVD grid with caching."""
        if not cvd_grid_state:
            empty_values = ['Please upload a screenshot first.', '*No images loaded*'] + [''] * 9 + [None, {}, '*Run Analyze to see side-by-side criterion comparison.*']
            return empty_values
        try:
            vlm_result = analyze_all_perspectives_with_cache(cvd_grid_state, progress=progress)
        except Exception as e:
            vlm_result = {'error': str(e), 'findings': [], 'passes': False}
        merged_report = format_wcag_report(vlm_result)

        # Extract individual perspective results from cache
        original_vlm = None
        cvd_results = {}
        for img, label in cvd_grid_state:
            cache_key = _get_cache_key(img, label)
            if cache_key in _vlm_cache:
                cached = _vlm_cache[cache_key]
                if label == "Normal vision (original design)":
                    original_vlm = cached
                else:
                    cvd_results[label] = cached

        # Generate WCAG reports for all 9 perspectives
        card_reports = []
        for img, label in cvd_grid_state:
            cache_key = _get_cache_key(img, label)
            if cache_key in _vlm_cache:
                cached = _vlm_cache[cache_key]
                card_reports.append(format_wcag_report(cached))
            else:
                card_reports.append(f'*{label} — Analysis pending*')

        comparison = '*Run Analyze to see side-by-side criterion comparison.*'
        if original_vlm is not None and cvd_results:
            comparison = _format_cvd_perception_comparison_summary(
                original_vlm=original_vlm,
                cvd_results=cvd_results,
            )

        # Return: status, card_reports (9), original_vlm, cvd_results, comparison
        return ["*Done — see reports above*"] + card_reports + [original_vlm, cvd_results, comparison]

    # File upload triggers gallery generation and card population immediately (no VLM)
    # Outputs: cvd_grid (hidden), current_cvd_grid, comparison_grid_container (visible),
    # then 9 perspective_images, 9 perspective_reports, wcag_comparison_output
    upload_outputs = [cvd_grid, current_cvd_grid, comparison_grid_container] + perspective_images + perspective_reports + [wcag_comparison_output]
    file_input.change(
        fn=handle_file_upload,
        inputs=file_input,
        outputs=upload_outputs,
    )

    # Analyze button triggers VLM on all perspectives with progress
    # Outputs: status_output, 9 perspective_reports, current_original_vlm, current_cvd_results, wcag_comparison_output
    analyze_outputs = [status_output] + perspective_reports + [current_original_vlm, current_cvd_results, wcag_comparison_output]
    submit_btn.click(
        fn=run_vlm_analysis,
        inputs=current_cvd_grid,
        outputs=analyze_outputs,
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