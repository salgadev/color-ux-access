import re
from playwright.sync_api import Page, expect
from scripts import *

target_website = "https://www.iflysouthern.com/"
title = "Southern Airways"
expected_title = re.compile(title)

def test_iflysouthern_website(page: Page):
    try:
        page.goto(target_website)
        screenshot_path = take_screenshot(page, title)
        
        for deficiency, config in deficiency_config.items():
            print(f'Simulating {deficiency}')
            cvd_file = simulate_cvd(screenshot_path, config['simulator'], config['deficiency'], config['severity'])
            cvd_file.save(os.path.join(SCREENSHOT_FOLDER, f'{deficiency}_{os.path.basename(screenshot_path)}'))
        
        expect(page).to_have_title(expected_title)
        
        screenshot_path = take_screenshot(page, title)
        base64_image = image_to_base64(screenshot_path)
        result = aria_image_analysis(base64_image, "What are the coordinates of the 'YOUR BOOKING' button?")
        print(result)
        button_coordinates = result.splitlines()[-1]
        page.click(button_coordinates.split(',')[0], button_coordinates.split(',')[1])
        
    except Exception as e:
        print(f"Error: {e}")
        page.screenshot(path="error_screenshot.png")
        raise
