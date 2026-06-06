import re
from playwright.sync_api import Page, expect
from scripts import *

title = "Playwright"
expected_title = re.compile(title)
target_website = "https://playwright.dev/"

def test_color_vision_deficiencies(page: Page):
    page.goto(target_website)
    screenshot_path = take_screenshot(page, title)
    
    for deficiency, config in deficiency_config.items():
        cvd_file = simulate_cvd(screenshot_path, config['simulator'], config['deficiency'], config['severity'])
        cvd_file.save(os.path.join(SCREENSHOT_FOLDER, f'{deficiency}_{os.path.basename(screenshot_path)}'))
        
def test_has_title(page: Page):
    page.goto(target_website)
    expect(page).to_have_title(expected_title)
