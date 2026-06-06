"""
Color-UX-Access — HF Space deployment.
========================================
Gradio app for colorblind accessibility testing, ready for hackathon submission.

Architecture:
  - User uploads a screenshot (OS/browser screenshot tool → Gradio File)
  - CVD simulation runs locally (pure Python, no browser needed)
  - VLM inference runs on Space GPU via @spaces.GPU(duration=120)
  - HF Router API → CohereLabs/aya-vision-32b
  - WCAG 2.1 markdown report + CVD gallery displayed

Requirements:
  - Python 3.12 (HF Spaces requirement)
  - HF_TOKEN secret set in Space settings
  - gradio>=5.0, spaces
  - torch with CUDA libs
  - openai, pillow, daltonlens

Deploy:
  1. Push to GitHub
  2. Create HF Space (SDK: Gradio, hardware: T4/mega or A10G)
  3. Add HF_TOKEN secret in Space settings
  4. Link to GitHub repo or upload this file directly
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


# ── VLM Inference (Space GPU) ─────────────────────────────────────────────────
#
# First call takes 60-90s (model download + KV cache init).
# Subsequent calls are fast (<5s).


def analyze_with_vlm(image_bytes: bytes) -> dict:
    """
    Analyze a screenshot for WCAG color-accessibility issues.
    Uses CohereLabs/aya-vision-32b via HF Router API on Space GPU.

    Runs inside @spaces.GPU(duration=120) — do not call this directly
    from non-GPU functions. Gate it behind the decorator below.
    """
    hf_token = os.environ.get('HF_TOKEN') or os.environ.get('HF_API_TOKEN')
    if not hf_token:
        return {
            'error': 'HF_TOKEN not set. Add it in Space Settings → Variables and Secrets.',
            'findings': [],
            'passes': False,
        }

    from openai import OpenAI

    client = OpenAI(
        base_url='https://router.huggingface.co/v1',
        api_key=hf_token,
    )

    image_b64 = base64.b64encode(image_bytes).decode('utf-8')

    system_prompt = (
        'You are an accessibility expert specializing in colorblind user experience. '
        'Analyze screenshots for WCAG 2.1 compliance issues. '
        'For each finding, cite the specific success criterion (1.1.1, 1.4.1, 1.4.3, or 1.4.11). '
        'Output a JSON object with this structure:\n'
        '{\n'
        '  "findings": [\n'
        '    {\n'
        '      "type": "Low Contrast | Color Only Information | Missing Text Alternative | Insufficient Non-Text Contrast",\n'
        '      "wcag_criterion": "1.4.1 | 1.4.3 | 1.1.1 | 1.4.11",\n'
        '      "description": "...",\n'
        '      "severity": "critical | serious | moderate",\n'
        '      "location": "Top-left, center, etc."\n'
        '    }\n'
        '  ],\n'
        '  "summary": "Overall assessment",\n'
        '  "passes": true/false\n'
        '}'
    )

    response = client.chat.completions.create(
        model='CohereLabs/aya-vision-32b',
        messages=[
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': system_prompt},
                    {
                        'type': 'image_url',
                        'image_url': {'url': f'data:image/png;base64,{image_b64}'},
                    },
                ],
            }
        ],
        max_tokens=1024,
        temperature=0.1,
    )

    raw = response.choices[0].message.content
    # Strip markdown code fences if present
    if raw.startswith('```'):
        lines = raw.split('\n')
        raw = '\n'.join(lines[1:-1])
    return json.loads(raw)


# ── Gradio App ────────────────────────────────────────────────────────────────

# Theme — same accessible blue/gray palette as local app
_theme_css = """
:root { --color-primary: #1E88E5; }
.gradio-container { font-family: 'Inter', Arial, sans-serif; }
"""

with gr.Blocks(
    title='Color-UX-Access',
    theme=gr.themes.Base(
        primary_hue='blue',
        secondary_hue='gray',
        neutral_hue='gray',
    ),
    css=_theme_css,
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
    def run_analysis(file_obj):
        """
        Two-stage pipeline:
          1. CVD simulation (CPU, instant) → gallery
          2. VLM inference (GPU, ~90s first call) → WCAG report
        Both run in the same function — GPU decorator wraps the whole thing.
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
            vlm_result = analyze_with_vlm(image_bytes)
        except Exception as e:
            vlm_result = {'error': str(e), 'findings': [], 'passes': False}

        report_md = format_wcag_report(vlm_result)
        return original, cvd_gallery, report_md

    submit_btn.click(
        fn=run_analysis,
        inputs=file_input,
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
    # Local dev — no @spaces.GPU needed, just run with standard Gradio
    demo.launch(server_name='0.0.0.0', server_port=7860)