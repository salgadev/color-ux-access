"""Headed browser E2E test for colorfail upload→analyze→compare flow."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, expect

# Path to test image
TEST_IMAGE = Path(__file__).parent.parent / "examples" / "UR.webp"
APP_URL = "http://localhost:7860"

async def run_e2e_test():
    async with async_playwright() as p:
        # Launch headed browser
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Track console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        print(f"[E2E] Navigating to {APP_URL}")
        await page.goto(APP_URL, wait_until="domcontentloaded", timeout=60000)
        
        # Wait for the file upload component
        file_input = page.locator('input[type="file"]').first
        await expect(file_input).to_be_attached()
        
        print(f"[E2E] Uploading test image: {TEST_IMAGE}")
        await file_input.set_input_files(str(TEST_IMAGE))
        
        # Wait for upload to process and gallery to populate
        print("[E2E] Waiting for upload to complete...")
        await page.wait_for_timeout(5000)
        
        # Debug: check what's on the page
        page_content = await page.content()
        print(f"[E2E] Page content length: {len(page_content)}")
        
        # Check for gallery images
        gallery_imgs = await page.locator('img').all()
        print(f"[E2E] Total images on page: {len(gallery_imgs)}")
        for i, img in enumerate(gallery_imgs[:15]):
            src = await img.get_attribute('src')
            alt = await img.get_attribute('alt')
            print(f"[E2E]   Image {i}: src={src[:80] if src else 'none'} alt={alt}")
        
        # Gallery should have 9+ images (original + 8 CVD variants)
        # Filter to only gallery images (those with gradio_api/file URLs)
        gallery_images = [img for img in gallery_imgs 
                         if await img.get_attribute('src') and 'gradio_api/file' in await img.get_attribute('src')]
        print(f"[E2E] Gallery images detected: {len(gallery_images)}")
        assert len(gallery_images) >= 9, f"Expected at least 9 gallery images, got {len(gallery_images)}"
        print("[E2E] ✓ Gallery shows 9+ images (original + 8 CVD variants)")
        
        # Click Analyze button
        print("[E2E] Clicking Analyze button...")
        analyze_btn = page.locator('button:has-text("Analyze")').first
        await expect(analyze_btn).to_be_enabled()
        await analyze_btn.click()
        
        # Wait for WCAG reports to populate
        print("[E2E] Waiting for WCAG reports...")
        await page.wait_for_timeout(3000)
        
        # Check original WCAG report populated - look for the report heading
        original_report_heading = page.locator('text="WCAG Report: Normal vision (original design)"').first
        await expect(original_report_heading).to_be_visible(timeout=60000)
        print("[E2E] ✓ Original WCAG report populated")
        
        # Check CVD WCAG report populated
        cvd_report_heading = page.locator('text="WCAG Report: Protanopia (red-blind)"').first
        await expect(cvd_report_heading).to_be_visible(timeout=60000)
        print("[E2E] ✓ CVD WCAG report populated")
        
        # Check comparison panel populated
        comparison_heading = page.locator('text="WCAG Comparison: Original vs Protanopia (red-blind)"').first
        await expect(comparison_heading).to_be_visible(timeout=30000)
        print("[E2E] ✓ WCAG comparison panel populated")
        
        # Verify no radio button interaction was required for basic comparison
        radio_buttons = page.locator('input[type="radio"]')
        radio_count = await radio_buttons.count()
        print(f"[E2E] Radio buttons present: {radio_count} (not required for basic comparison)")
        
        # Verify the basic comparison worked without selecting any radio button
        # (default protanopia was selected by default)
        comparison_text = await comparison_heading.locator('..').inner_text()
        assert "Protanopia" in comparison_text or "protanopia" in comparison_text.lower()
        print("[E2E] ✓ Basic comparison completed without manual radio button selection")
        
        # Take final screenshot for documentation
        await page.screenshot(path="e2e_test_result.png", full_page=True)
        print("[E2E] Screenshot saved to e2e_test_result.png")
        
        # Check for console errors
        if console_errors:
            print(f"[E2E] Console errors: {console_errors}")
        
        await browser.close()
        print("\n[E2E] ALL ASSERTIONS PASSED ✓")
        return True

if __name__ == "__main__":
    try:
        asyncio.run(run_e2e_test())
    except Exception as e:
        print(f"\n[E2E] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)