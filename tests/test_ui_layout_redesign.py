"""
Tests for UI Layout Redesign — verify the comparison grid layout with perspective cards.

Requirements:
1. Original screenshot + 8 CVD variants displayed in comparison grid
2. Each perspective card has: label, image display, WCAG results placeholder
3. All perspectives render simultaneously on upload without user interaction
4. Click Analyze runs WCAG evaluation for all perspectives
5. No tabs — true side-by-side comparison grid
"""
import sys
import pathlib

_project_root = pathlib.Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import gradio as gr
import app as app_module
from PIL import Image
from unittest.mock import patch


class TestUILayoutRedesign:
    """Tests for the redesigned UI layout with comparison grid."""

    def test_generate_cvd_gallery_includes_original_as_first_entry(self):
        """generate_cvd_gallery should return original as first entry with correct label."""
        img = Image.new('RGB', (100, 100), color='red')
        gallery = app_module.generate_cvd_gallery(img)
        
        # Should have 9 entries: 1 original + 8 CVD variants
        assert len(gallery) == 9, f"Expected 9 entries, got {len(gallery)}"
        
        # First entry should be original
        first_img, first_label = gallery[0]
        assert first_label == "Normal vision (original design)", f"First label should be 'Normal vision (original design)', got '{first_label}'"
        assert first_img is img, "First image should be the original"

    def test_vlm_cvd_prompts_includes_original(self):
        """_VLM_CVD_PROMPTS should have an entry for original design."""
        assert "Normal vision (original design)" in app_module._VLM_CVD_PROMPTS
        prompt = app_module._VLM_CVD_PROMPTS["Normal vision (original design)"]
        assert "normal color vision" in prompt.lower() or "normal vision" in prompt.lower()

    def test_analyze_all_perspectives_includes_original(self):
        """analyze_all_perspectives_with_cache should analyze original perspective."""
        from app import analyze_all_perspectives_with_cache, _vlm_merged_cache, _vlm_cache

        img = Image.new('RGB', (100, 50), color='red')
        cvd_grid = [
            (img, "Normal vision (original design)"),
            (img, "Protanopia (red-blind)"),
        ]

        _vlm_merged_cache.clear()
        _vlm_cache.clear()

        with patch('app._call_minicpm_endpoint') as mock_vlm:
            mock_vlm.return_value = {"findings": [], "passes": True, "summary": "Test"}

            result = analyze_all_perspectives_with_cache(cvd_grid)

            # Should call VLM for each perspective including original
            assert mock_vlm.call_count == 2, f"Expected 2 VLM calls (original + 1 CVD), got {mock_vlm.call_count}"

    def test_run_vlm_analysis_returns_reports_for_all_cards(self):
        """run_vlm_analysis should return WCAG reports for all 9 perspective cards."""
        from app import run_vlm_analysis, _vlm_merged_cache, _vlm_cache
        import gradio as gr
        
        img = Image.new('RGB', (100, 50), color='yellow')  # Unique color to avoid cache conflicts
        cvd_grid = [
            (img, "Normal vision (original design)"),
            (img, "Protanopia (red-blind)"),
            (img, "Deuteranopia (green-blind)"),
            (img, "Tritanopia (blue-blind)"),
            (img, "Protanomaly (red-weak)"),
            (img, "Deuteranomaly (green-weak)"),
            (img, "Tritanomaly (blue-weak)"),
            (img, "Severe Protanopia (red-blind)"),
            (img, "Severe Deuteranopia (green-blind)"),
        ]
        
        _vlm_merged_cache.clear()
        _vlm_cache.clear()
        
        # Mock VLM to return different results for original vs CVD
        call_results = []
        
        def mock_vlm_side_effect(image_bytes, system_prompt):
            call_results.append(system_prompt)
            if "normal color vision" in system_prompt.lower() or "normal vision" in system_prompt.lower():
                return {"findings": [{"type": "Low Contrast", "wcag_criterion": "1.4.3", "severity": "moderate", "description": "Original issue", "location": "Body"}], "passes": False, "summary": "Original has issues"}
            else:
                return {"findings": [{"type": "Color Only Information", "wcag_criterion": "1.4.1", "severity": "critical", "description": "CVD issue", "location": "Button"}], "passes": False, "summary": "CVD has issues"}
        
        with patch('app._call_minicpm_endpoint', side_effect=mock_vlm_side_effect):
            # run_vlm_analysis signature: (cvd_grid_state, progress)
            # Returns: [status, 9 card_reports, original_vlm, cvd_results, comparison]
            import gradio as gr
            progress = gr.Progress()
            progress.tqdm = lambda x: x
            progress.__call__ = lambda x, desc=None: None
            
            result = run_vlm_analysis(cvd_grid, progress=progress)
            
            # Result structure: [status, 9 card_reports, original_vlm, cvd_results, comparison]
            status = result[0]
            card_reports = result[1:10]
            original_vlm = result[10]
            cvd_results = result[11]
            comparison = result[12]
            
            assert status == "*Done — see reports above*"
            assert len(card_reports) == 9, f"Should have 9 card reports, got {len(card_reports)}"
            
            # original_report should be in card_reports[0] (first card is original)
            original_report = card_reports[0]
            assert "1.4.3" in original_report, "Original report should show original findings"
            assert "Low Contrast" in original_report, "Original report should show original issue type"
            
            # CVD reports should contain CVD findings
            cvd_report = card_reports[1]  # Second card is Protanopia
            assert "1.4.1" in cvd_report, "CVD report should show CVD findings"
            assert "Color Only Information" in cvd_report, "CVD report should show CVD issue type"

    def test_handle_file_upload_populates_all_cards(self):
        """handle_file_upload should populate all 9 perspective cards with images."""
        from app import handle_file_upload
        import io
        
        # Create a test image file with unique color to avoid cache conflicts
        img = Image.new('RGB', (100, 100), color='cyan')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        file_bytes = buf.getvalue()
        
        result = handle_file_upload(file_bytes)
        
        # Result structure: [cvd_grid_hidden, cvd_grid_state, container_visible, 9 card_images, 9 card_reports, comparison]
        cvd_grid_hidden = result[0]
        cvd_grid_state = result[1]
        container_visible = result[2]
        card_images = result[3:12]
        card_reports = result[12:21]
        comparison = result[21]
        
        # cvd_grid_hidden (gallery) should have 9 entries
        assert len(cvd_grid_hidden) == 9, f"Gallery should have 9 entries, got {len(cvd_grid_hidden)}"
        
        # cvd_grid_state should have 9 entries
        assert len(cvd_grid_state) == 9, f"cvd_grid_state should have 9 entries, got {len(cvd_grid_state)}"
        
        # Container should be visible
        assert container_visible, "Comparison grid container should be visible"
        
        # Should have 9 card images
        assert len(card_images) == 9, f"Should have 9 card images, got {len(card_images)}"
        for card_img in card_images:
            assert isinstance(card_img, Image.Image), "Each card image should be a PIL Image"
        
        # Should have 9 card reports with placeholders
        assert len(card_reports) == 9, f"Should have 9 card reports, got {len(card_reports)}"
        for card_report in card_reports:
            assert isinstance(card_report, str)
            assert "WCAG results will appear" in card_report

    def test_caching_keys_on_original_screenshot(self):
        """VLM cache should key on original screenshot, not selected thumbnail."""
        from app import _get_merged_cache_key, _vlm_merged_cache
        
        img1 = Image.new('RGB', (100, 50), color='red')
        img2 = Image.new('RGB', (100, 50), color='blue')
        
        key1 = _get_merged_cache_key(img1)
        key2 = _get_merged_cache_key(img1)
        key3 = _get_merged_cache_key(img2)
        
        # Same image should produce same key
        assert key1 == key2, "Same original image should produce same cache key"
        
        # Different image should produce different key
        assert key1 != key3, "Different original images should produce different cache keys"
        
        # Cache should store merged results per original image
        _vlm_merged_cache.clear()
        _vlm_merged_cache[key1] = {"findings": [], "passes": True}
        assert key1 in _vlm_merged_cache
        assert key3 not in _vlm_merged_cache


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])