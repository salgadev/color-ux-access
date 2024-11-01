import re
from playwright.sync_api import Page, expect
from daltonlens import simulate
import PIL
import numpy as np

title = "Playwright"
expected_title = re.compile(title)
target_website = "https://playwright.dev/"
screenshot_filename = f"{title}_screenshot.png"
protan_screenshot_filename = f"protan_{screenshot_filename}.png"
severe_protan_screenshot_filename = f"severe_protan_{screenshot_filename}.png"

# Create simulators
# Machado, 2009 for protanomaly/deuteranomly (severity < 1)
simulator = simulate.Simulator_Machado2009()

# Vienot, 1999 for protanopia/deuteranopia (severity = 1) 
severe_simulator = simulate.Simulator_Vienot1999()

# Brettel & Molon, 1997 for tritan simulations 
tritan_simulator = simulate.Simulator_Brettel1997()

def test_has_title(page: Page):
    page.goto(target_website)

    # Expect a title "to contain" a substring.
    expect(page).to_have_title(expected_title)

def test_screenshot(page: Page):
    page.goto(target_website)    
    page.screenshot(path=screenshot_filename)

def test_80_protan(page: Page):
    # convert to array
    im = np.asarray(PIL.Image.open(screenshot_filename).convert('RGB'))

    # Apply protanomaly simulation
    protan_im = simulator.simulate_cvd(im, simulate.Deficiency.PROTAN, severity=0.8)
    protan_file = PIL.Image.fromarray(protan_im)
    protan_file.save(protan_screenshot_filename)

def test_100_protan(page: Page):
    # convert to array
    im = np.asarray(PIL.Image.open(screenshot_filename).convert('RGB'))

    # Apply protanomaly simulation
    severe_protan_im = severe_simulator.simulate_cvd(im, simulate.Deficiency.PROTAN, severity=1)
    severe_protan_file = PIL.Image.fromarray(severe_protan_im)
    severe_protan_file.save(f'severe_protan_{screenshot_filename}')    

def test_80_deutan(page: Page):
    # convert to array
    im = np.asarray(PIL.Image.open(screenshot_filename).convert('RGB'))

    # Apply protanomaly simulation
    deutan_im = simulator.simulate_cvd(im, simulate.Deficiency.DEUTAN, severity=0.8)
    deutan_file = PIL.Image.fromarray(deutan_im)
    deutan_file.save(f'deutan_{screenshot_filename}')

def test_100_deutan(page: Page):
    # convert to array
    im = np.asarray(PIL.Image.open(screenshot_filename).convert('RGB'))

    # Apply protanomaly simulation
    severe_deutan_im = severe_simulator.simulate_cvd(im, simulate.Deficiency.DEUTAN, severity=1)
    severe_deutan_file = PIL.Image.fromarray(severe_deutan_im)
    severe_deutan_file.save(f'severe_deutan_{screenshot_filename}')

def test_tritan(page: Page):
    # convert to array
    im = np.asarray(PIL.Image.open(screenshot_filename).convert('RGB'))

    # Apply protanomaly simulation
    tritan_im = tritan_simulator.simulate_cvd(im, simulate.Deficiency.TRITAN, severity=0.8)
    tritan_file = PIL.Image.fromarray(tritan_im)
    tritan_file.save(f'tritan_{screenshot_filename}')