"""
Screenshot capture module for color-ux-access.
Takes a screenshot of a given URL using Playwright and returns a PIL Image.
Screenshot is a proxy for the colorblind user's visual perspective
(mirroring how NARWALL uses NVDA as a proxy for screen reader users).
"""
from io import BytesIO
from PIL import Image


def take_screenshot(page, url: str, timeout: int = 60000) -> Image.Image:
    """
    Navigate to URL, wait for network idle, capture full-page screenshot.

    Args:
        page: Playwright page object (from browser.new_page())
        url: URL to navigate to
        timeout: Navigation timeout in ms (default 60s)

    Returns:
        PIL Image of the full page

    Raises:
        playwright.sync_api.Error: on navigation/timeout failure
    """
    page.goto(url, wait_until='networkidle', timeout=timeout)
    page.wait_for_timeout(5000)  # Allow JS frameworks to fully render
    screenshot_bytes = page.screenshot(full_page=True, timeout=timeout)
    image = Image.open(BytesIO(screenshot_bytes))
    page.close()  # Release browser context to prevent resource leaks
    return image