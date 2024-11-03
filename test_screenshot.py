import re
from playwright.sync_api import Page, expect
from daltonlens import simulate
import PIL
import numpy as np

title = "Playwright"
expected_title = re.compile(title)
target_website = "https://playwright.dev/"
screenshot_filename = f"{title}_screenshot.png"

# Create simulators
simulator = simulate.Simulator_Machado2009()
severe_simulator = simulate.Simulator_Vienot1999()
tritan_simulator = simulate.Simulator_Brettel1997()

def simulate_cvd(image, simulator, deficiency, severity):
    image_array = np.asarray(PIL.Image.open(image).convert('RGB'))
    cvd_im = simulator.simulate_cvd(image_array, deficiency, severity)
    cvd_file = PIL.Image.fromarray(cvd_im)
    return cvd_file

deficiency_config = {
    'protan': {'simulator': simulator, 'severity': 0.8, 'deficiency': simulate.Deficiency.PROTAN},
    'severe_protan': {'simulator': severe_simulator, 'severity': 1, 'deficiency': simulate.Deficiency.PROTAN},
    'deutan': {'simulator': simulator, 'severity': 0.8, 'deficiency': simulate.Deficiency.DEUTAN},
    'severe_deutan': {'simulator': severe_simulator, 'severity': 1, 'deficiency': simulate.Deficiency.DEUTAN},
    'tritan': {'simulator': tritan_simulator, 'severity': 0.8, 'deficiency': simulate.Deficiency.TRITAN},
}

def test_color_vision_deficiencies(page: Page):
    page.goto(target_website)
    page.screenshot(path=screenshot_filename)

    for deficiency, config in deficiency_config.items():
        cvd_file = simulate_cvd(screenshot_filename, config['simulator'], config['deficiency'], config['severity'])
        cvd_file.save(f'{deficiency}_{screenshot_filename}')
        
def test_has_title(page: Page):
    page.goto(target_website)
    expect(page).to_have_title(expected_title)
