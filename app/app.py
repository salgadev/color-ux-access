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

# Mock VLM analysis for testing - replace with real model later
def analyze_image_with_vlm(image, prompt):
    """Mock VLM analysis - returns sample accessibility issues"""
    # Simulate some common accessibility issues
    mock_issues = [
        {
            "description": "Low contrast between text and background on button elements",
            "type": "low contrast",
            "remediation": "Increase contrast ratio to at least 4.5:1 by darkening text or lightening background",
            "bbox": [100, 200, 300, 250]
        },
        {
            "description": "Color-dependent error message without text label",
            "type": "color-dependent element",
            "remediation": "Add text label or icon to accompany color coding",
            "bbox": [400, 150, 600, 200]
        }
    ]
    
    # Return as JSON string like the real VLM would
    return json.dumps(mock_issues)

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
    """Main function to process URL and generate report."""
    if not url:
        return None, None, "Please enter a URL"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            page = browser.new_page(viewport={'width': 1280, 'height': 720})
            
            # Take original screenshot
            original_image = take_screenshot(page, url)
            
            # Generate CVD simulations
            cvd_images = {}
            for name, config in deficiency_config.items():
                cvd_img = simulate_cvd(
                    original_image, 
                    config['simulator'], 
                    config['deficiency'], 
                    config['severity']
                )
                cvd_images[name] = cvd_img
            
            # Add achromatopsia and achromatomaly
            cvd_images['achromatopsia'] = simulate_achromatopsia(original_image, 1.0)
            cvd_images['achromatomaly'] = simulate_achromatopsia(original_image, 0.5)
            
            browser.close()
        
        # Prepare prompt for VLM
        prompt = "Describe any color accessibility issues in this image, such as low contrast or color-dependent elements."
        
        # Get VLM analysis (using mock for now)
        vlm_result = analyze_image_with_vlm(original_image, prompt)
        
        # Try to parse as JSON, if fails return raw text
        try:
            # Extract JSON from the response (in case there's extra text)
            import re
            json_match = re.search(r'\[.*\]', vlm_result, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                issues = json.loads(json_str)
                # Format issues for display
                formatted_report = "## Accessibility Issues Found\n\n"
                if not issues:
                    formatted_report += "No accessibility issues detected."
                else:
                    for i, issue in enumerate(issues, 1):
                        formatted_report += f"### Issue {i}\n"
                        formatted_report += f"- **Description**: {issue.get('description', 'N/A')}\n"
                        formatted_report += f"- **Type**: {issue.get('type', 'N/A')}\n"
                        formatted_report += f"- **Remediation**: {issue.get('remediation', 'N/A')}\n"
                        formatted_report += f"- **Location**: {issue.get('bbox', issue.get('point', 'N/A'))}\n\n"
            else:
                # If no JSON found, return raw text
                formatted_report = f"## VLM Analysis\n\n{vlm_result}"
        except json.JSONDecodeError:
            formatted_report = f"## VLM Analysis (Raw Output)\n\n{vlm_result}"
        
        # Convert cvd_images dict to list for Gradio Gallery
        cvd_list = []
        for name, img in cvd_images.items():
            cvd_list.append((img, name.replace('_', ' ').title()))
        
        return original_image, cvd_list, formatted_report
    
    except Exception as e:
        print(f"Error in create_accessibility_report: {e}")
        return None, None, f"Error processing URL: {str(e)}"

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