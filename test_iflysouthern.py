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
        ui_element_to_find = 'SELECT FROM'
        prompt = f'What are the coordinates of the "{ui_element_to_find}" button? Respond in a dictionary with the keys x,y,reasoning'
        aria_answer = aria_image_analysis(base64_image, prompt)
        x, y, reasoning = extract_coordinates_and_reasoning(aria_answer)        
        # result = find_element_coordinates(base64_image, 'YOUR BOOKING')
        # for debugging only
        print(x, y, reasoning)
        
        page.mouse.click(x, y)
        
    except Exception as e:
        print(f"Error: {e}")
        page.screenshot(path="error_screenshot.png")
        raise
