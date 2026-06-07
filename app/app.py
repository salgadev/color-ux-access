import os
import gradio as gr
from playwright.sync_api import sync_playwright
from PIL import Image
import numpy as np
from daltonlens import simulate
import json
import base64
from io import BytesIO
from app.custom_theme import color_ux_access_theme

# ── VLM Analysis ───────────────────────────────────────────────────────────────

def analyze_image_with_vlm(image, hf_token=None):
    """
    Analyze screenshot for WCAG color-accessibility issues via HF Router API.
    Falls back to mock if HF_TOKEN not set.

    Uses CohereLabs/aya-vision-32b via HF Router (OpenAI-compatible).
    Prompt instructs structured audit methodology covering all 10 CVD-relevant
    element types and WCAG 1.4.1 / 1.4.3 / 1.4.11 criteria.
    """
    from openai import OpenAI

    if not hf_token:
        hf_token = os.environ.get('HF_TOKEN') or os.environ.get('HF_API_TOKEN')

    if not hf_token:
        return _mock_vlm_response()

    # Convert PIL image to base64
    buf = BytesIO()
    image.save(buf, format='PNG')
    image_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    client = OpenAI(
        base_url='https://router.huggingface.co/v1',
        api_key=hf_token,
    )

    system_prompt = (
        'You are an accessibility expert specializing in color vision deficiency (CVD) and WCAG 2.1 compliance. '
        'Analyze this screenshot as if you are auditing it for a user with color blindness.\n\n'
        '## Audit Methodology\n'
        'For each UI element where color carries meaning, check:\n'
        '1. Is color the ONLY visual signal? (if yes, it fails SC 1.4.1)\n'
        '2. Is there a redundant cue — text label, icon, pattern, underline, shape?\n'
        '3. Would the element be understandable in grayscale?\n\n'
        '## Specific Elements to Check\n'
        '- Form validation: error/success states (red/green borders without text or icon)\n'
        '- Required field indicators (red asterisk without legend)\n'
        '- Links within body text (color-only differentiation, no underline)\n'
        '- Data visualizations (color-coded charts without pattern/text labels)\n'
        '- Status indicators (colored dots/badges: online, active, pending)\n'
        '- Color swatches (product variants without text labels)\n'
        '- Button states (primary vs secondary distinguished only by color)\n'
        '- Alert messages (success/error/warning in color-only)\n'
        '- Text contrast (WCAG 1.4.3: 4.5:1 normal, 3:1 large text)\n'
        '- UI component contrast (WCAG 1.4.11: 3:1 for buttons, form fields)\n\n'
        '## Severity Classification\n'
        '- critical: User cannot complete a core task (form submission, navigation, purchase)\n'
        '- serious: User can complete task but with significant confusion or delay\n'
        '- moderate: Cosmetic or minor confusion, workaround exists\n\n'
        '## Output Format\n'
        'Output a JSON object:\n'
        '{\n'
        '  "findings": [\n'
        '    {\n'
        '      "type": "Color-Only Error State | Color-Only Status Indicator | Low Contrast Text | Color-Only Link | Color-Only Chart | Insufficient UI Contrast | Color-Only Required Field | Color-Only Button State | Color-Only Alert",\n'
        '      "wcag_criterion": "1.4.1 | 1.4.3 | 1.4.11",\n'
        '      "description": "Specific description of what is wrong and which UI element is affected",\n'
        '      "severity": "critical | serious | moderate",\n'
        '      "location": "Top-left, center, form area, navigation bar, etc.",\n'
        '      "remediation": "Specific fix: add text label, add icon, add underline, increase contrast to X:1, add pattern to chart"\n'
        '    }\n'
        '  ],\n'
        '  "summary": "Overall assessment for colorblind users",\n'
        '  "passes": true/false\n'
        '}\n\n'
        'Be specific. Name the exact UI element. Give actionable remediation.'
    )

    response = client.chat.completions.create(
        model='CohereLabs/aya-vision-32b',
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': system_prompt},
                {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{image_b64}'}},
            ],
        }],
        max_tokens=1024,
        temperature=0.1,
    )

    raw = response.choices[0].message.content
    if raw.startswith('```'):
        lines = raw.split('\n')
        raw = '\n'.join(lines[1:-1])
    return json.loads(raw)


def _mock_vlm_response():
    """Return mock VLM response for local testing without HF_TOKEN."""
    return {
        'findings': [
            {
                'type': 'Color-Only Error State',
                'wcag_criterion': '1.4.1',
                'description': 'Form error indicated only by red border — no error icon or text message visible',
                'serious': 'serious',
                'location': 'Form area, email field',
                'remediation': 'Add inline error text ("Invalid email format") and an exclamation icon alongside the red border',
            },
            {
                'type': 'Low Contrast Text',
                'wcag_criterion': '1.4.3',
                'description': 'Body text contrast ratio appears below 4.5:1 against background',
                'severity': 'moderate',
                'location': 'Main content area',
                'remediation': 'Darken text color or lighten background to achieve at least 4.5:1 contrast ratio',
            },
        ],
        'summary': 'This page has color-only error indication and potential contrast issues that would affect colorblind users.',
        'passes': False,
    }

# CVD simulators
simulator = simulate.Simulator_Machado2009()
severe_simulator = simulate.Simulator_Vienot1999()
tritan_simulator = simulate.Simulator_Brettel1997()

deficiency_config = {
    'protanopia': {'simulator': simulator, 'severity': 0.8, 'deficiency': simulate.Deficiency.PROTAN},
    'severe_protanopia': {'simulator': severe_simulator, 'severity': 1, 'deficiency': simulate.Deficiency.PROTAN},
    'deuteranopia': {'simulator': simulator, 'severity': 0.8, 'deficiency': simulate.Deficiency.DEUTAN},
    'severe_deuteranopia': {'simulator': severe_simulator, 'severity': 1, 'deficiency': simulate.Deficiency.DEUTAN},
    'tritanopia': {'simulator': tritan_simulator, 'severity': 0.8, 'deficiency': simulate.Deficiency.TRITAN},
    'protanomaly': {'simulator': simulator, 'severity': 0.4, 'deficiency': simulate.Deficiency.PROTAN},
    'deuteranomaly': {'simulator': simulator, 'severity': 0.4, 'deficiency': simulate.Deficiency.DEUTAN},
    'tritanomaly': {'simulator': tritan_simulator, 'severity': 0.4, 'deficiency': simulate.Deficiency.TRITAN},
    # Achromatopsia and Achromatomaly will be handled separately via grayscale conversion
}

def take_screenshot(page, url):
    """Take a screenshot of the full page."""
    page.goto(url, wait_until="networkidle", timeout=60000)
    # Wait a bit for any dynamic content
    page.wait_for_timeout(5000)
    # Get full page screenshot
    screenshot = page.screenshot(full_page=True, timeout=60000)
    image = Image.open(BytesIO(screenshot))
    return image

def simulate_cvd(image, simulator, deficiency, severity):
    """Apply CVD simulation to an image."""
    image_array = np.asarray(image.convert('RGB'))
    cvd_im = simulator.simulate_cvd(image_array, deficiency, severity)
    return Image.fromarray(cvd_im)

def simulate_achromatopsia(image, severity):
    """Simulate achromatopsia by converting to grayscale."""
    # Convert to grayscale then back to RGB
    gray = image.convert('L')
    gray_rgb = Image.merge('RGB', (gray, gray, gray))
    # Blend with original based on severity for achromatomaly
    if severity < 1.0:
        # Blend
        blended = Image.blend(image.convert('RGB'), gray_rgb, severity)
        return blended
    else:
        return gray_rgb

def create_accessibility_report(url):
    """Main function: URL → screenshot → CVD gallery → VLM audit → WCAG report."""
    if not url:
        return None, None, "Please enter a URL"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            page = browser.new_page(viewport={'width': 1280, 'height': 720})

            original_image = take_screenshot(page, url)

            # Generate all 10 CVD simulations
            cvd_images = {}
            for name, config in deficiency_config.items():
                cvd_img = simulate_cvd(
                    original_image,
                    config['simulator'],
                    config['deficiency'],
                    config['severity']
                )
                cvd_images[name] = cvd_img

            cvd_images['achromatopsia'] = simulate_achromatopsia(original_image, 1.0)
            cvd_images['achromatomaly'] = simulate_achromatopsia(original_image, 0.5)

            browser.close()

        # VLM analysis — returns dict with findings, summary, passes
        vlm_result = analyze_image_with_vlm(original_image)

        # Format the WCAG report
        formatted_report = _format_wcag_report(vlm_result)

        # Convert cvd_images dict to list for Gradio Gallery
        cvd_list = []
        for name, img in cvd_images.items():
            cvd_list.append((img, name.replace('_', ' ').title()))

        return original_image, cvd_list, formatted_report

    except Exception as e:
        print(f"Error in create_accessibility_report: {e}")
        return None, None, f"Error processing URL: {str(e)}"


def _format_wcag_report(vlm_result: dict) -> str:
    """Convert VLM dict response into a formatted markdown report."""
    if not isinstance(vlm_result, dict):
        return f"## VLM Analysis (Raw)\n\n{vlm_result}"

    if 'error' in vlm_result:
        return f"⚠️ **Error:** {vlm_result['error']}"

    findings = vlm_result.get('findings', [])
    if not findings:
        if vlm_result.get('passes', False):
            return "✅ Pass — No accessibility issues detected."
        return "✅ **No accessibility issues detected.**"

    severity_icons = {'critical': '🔴', 'serious': '🟠', 'moderate': '🟡'}
    wcag_links = {
        '1.4.1': 'https://www.w3.org/WAI/WCAG21/Understanding/use-of-color',
        '1.4.3': 'https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum',
        '1.4.11': 'https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast',
    }

    report = "## WCAG Accessibility Report\n\n"
    report += f"**Overall:** {'✅ Pass' if vlm_result.get('passes', False) else '❌ Fail'}\n\n"

    for i, f in enumerate(findings, 1):
        icon = severity_icons.get(f.get('severity', 'moderate'), '⚪')
        wcag = f.get('wcag_criterion', 'N/A')
        link = wcag_links.get(wcag, '#')
        report += f"### {icon} Issue {i}: {f.get('type', 'Unknown')}\n\n"
        report += f"- **WCAG:** [{wcag}]({link})\n"
        report += f"- **Severity:** {f.get('severity', 'N/A').capitalize()}\n"
        report += f"- **Description:** {f.get('description', 'N/A')}\n"
        report += f"- **Location:** {f.get('location', 'N/A')}\n"
        report += f"- **Remediation:** {f.get('remediation', 'No specific remediation provided')}\n\n"

    if vlm_result.get('summary'):
        report += f"**Summary:** {vlm_result['summary']}\n"

    return report

# Gradio Interface
with gr.Blocks(title="Color-UX-Access: Colorblind Accessibility Tester") as demo:
    gr.Markdown("# Color-UX-Access")
    gr.Markdown("Test web pages for color accessibility issues using AI vision simulation for color vision deficiency.")
    
    with gr.Row():
        url_input = gr.Textbox(label="Website URL", placeholder="https://example.com")
        submit_btn = gr.Button("Analyze", variant="primary")
    
    with gr.Row():
        with gr.Column():
            original_output = gr.Image(label="Original Screenshot", type="pil")
        with gr.Column():
            cvd_output = gr.Gallery(label="CVD Simulations", show_label=True, columns=2, rows=4, object_fit="contain", height="auto")
    
    report_output = gr.Markdown(label="Accessibility Report")
    
    submit_btn.click(
        fn=create_accessibility_report,
        inputs=url_input,
        outputs=[original_output, cvd_output, report_output]
    )
    
    # Examples
    gr.Examples(
        examples=[
            ["https://www.google.com"],
            ["https://www.wikipedia.org"],
            ["https://www.apple.com"]
        ],
        inputs=url_input,
        outputs=[original_output, cvd_output, report_output],
        fn=create_accessibility_report,
        cache_examples=False
    )

if __name__ == "__main__":
    demo.launch(theme=color_ux_access_theme)