"""
Tests for UI Layout Redesign — verify the original vs CVD comparison layout.

Requirements:
1. Original screenshot image displayed above CVD gallery on left
2. Original WCAG evaluation displayed above CVD WCAG evaluation on right
3. Gallery/CVD selector changes only update CVD report, keep original report fixed
4. VLM analysis includes original perspective as distinct entry
5. Caching keys on original screenshot
"""
import sys
import pathlib

_project_root = pathlib.Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import gradio as gr
import app as app_module
from PIL import Image
from unittest.mock import patch, MagicMock


class TestUILayoutRedesign:
    """Tests for the redesigned UI layout with original vs CVD comparison."""

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
        from app import analyze_all_perspectives_with_cache, _vlm_merged_cache
        
        img = Image.new('RGB', (100, 50), color='red')
        cvd_grid = [
            (img, "Normal vision (original design)"),
            (img, "Protanopia (red-blind)"),
        ]
        
        _vlm_merged_cache.clear()
        
        with patch('app._call_minicpm_endpoint') as mock_vlm:
            mock_vlm.return_value = {"findings": [], "passes": True, "summary": "Test"}
            
            result = analyze_all_perspectives_with_cache(cvd_grid)
            
            # Should call VLM for each perspective including original
            assert mock_vlm.call_count == 2, f"Expected 2 VLM calls (original + 1 CVD), got {mock_vlm.call_count}"

    def test_run_vlm_analysis_returns_original_report_to_original_output(self):
        """run_vlm_analysis should return original perspective report to original_report_output."""
        from app import run_vlm_analysis, _vlm_merged_cache, _vlm_cache
        
        img = Image.new('RGB', (100, 50), color='yellow')  # Unique color to avoid cache conflicts
        cvd_grid = [
            (img, "Normal vision (original design)"),
            (img, "Protanopia (red-blind)"),
            (img, "Deuteranopia (green-blind)"),
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
            # Returns: (original_report, status, cvd_report, original_vlm, cvd_results, comparison)
            import gradio as gr
            progress = gr.Progress()
            progress.tqdm = lambda x: x
            progress.__call__ = lambda x, desc=None: None
            
            result = run_vlm_analysis(cvd_grid, progress=progress)
            
            original_report, status, cvd_report, original_vlm, cvd_results, comparison = result
            
            # original_report should contain original WCAG evaluation
            assert "Original" in original_report or "normal" in original_report.lower(), "Original report should mention original design"
            assert "1.4.3" in original_report, "Original report should show original findings"
            
            # cvd_report should contain first CVD perspective evaluation
            assert "Protanopia" in cvd_report or "CVD" in cvd_report, "CVD report should show CVD perspective"
            assert "1.4.1" in cvd_report, "CVD report should show CVD findings"

    def test_handle_gallery_select_preserves_original_report(self):
        """handle_gallery_select should only update CVD report, keep original report unchanged."""
        from app import handle_gallery_select, analyze_single_perspective, _vlm_cache
        
        img = Image.new('RGB', (100, 50), color='purple')  # Unique color to avoid cache conflicts
        cvd_grid = [
            (img, "Normal vision (original design)"),
            (img, "Protanopia (red-blind)"),
            (img, "Deuteranopia (green-blind)"),
        ]
        
        _vlm_cache.clear()
        
        # Pre-populate cache with original and CVD results
        original_result = {"findings": [{"type": "Low Contrast", "wcag_criterion": "1.4.3", "severity": "moderate", "description": "Original issue", "location": "Body"}], "passes": False, "summary": "Original has issues", "cvd_label": "Normal vision (original design)"}
        protan_result = {"findings": [{"type": "Color Only Information", "wcag_criterion": "1.4.1", "severity": "critical", "description": "Protan issue", "location": "Button"}], "passes": False, "summary": "Protan has issues", "cvd_label": "Protanopia (red-blind)"}
        deuter_result = {"findings": [{"type": "Color Only Information", "wcag_criterion": "1.4.1", "severity": "serious", "description": "Deuter issue", "location": "Button"}], "passes": False, "summary": "Deuter has issues", "cvd_label": "Deuteranopia (green-blind)"}
        
        original_key = app_module._get_cache_key(img, "Normal vision (original design)")
        protan_key = app_module._get_cache_key(img, "Protanopia (red-blind)")
        deuter_key = app_module._get_cache_key(img, "Deuteranopia (green-blind)")
        _vlm_cache[original_key] = original_result
        _vlm_cache[protan_key] = protan_result
        _vlm_cache[deuter_key] = deuter_result
        
        original_vlm = original_result
        cvd_results = {"Protanopia (red-blind)": protan_result, "Deuteranopia (green-blind)": deuter_result}
        
        # Simulate clicking on Deuteranopia (index 2)
        class MockEvent:
            index = 2
        
        evt = MockEvent()
        result = handle_gallery_select(evt, cvd_grid, original_vlm, cvd_results)
        
        # Returns: (original_report_update, cvd_report, comparison, new_cvd_results)
        orig_report_update, cvd_report, comparison, new_cvd_results = result
        
        # original_report_update should be gr.update() (no change) or the original report
        # The key assertion: original report should NOT be cleared (empty string)
        assert orig_report_update != "", "Original report should not be cleared to empty string"
        
        # cvd_report should show Deuteranopia results
        assert "Deuteranopia" in cvd_report or "deuter" in cvd_report.lower(), "CVD report should show selected CVD"
        assert "1.4.1" in cvd_report, "CVD report should show selected CVD findings"

    def test_handle_cvd_selector_change_updates_only_cvd_report(self):
        """handle_cvd_selector_change should update CVD image and CVD report, keep original report."""
        from app import handle_cvd_selector_change
        
        img = Image.new('RGB', (100, 50), color='orange')  # Unique color to avoid cache conflicts
        
        original_vlm = {"findings": [{"type": "Low Contrast", "wcag_criterion": "1.4.3", "severity": "moderate", "description": "Original issue", "location": "Body"}], "passes": False, "summary": "Original has issues", "cvd_label": "Normal vision (original design)"}
        cvd_results = {
            "Protanopia (red-blind)": {"findings": [{"type": "Color Only Information", "wcag_criterion": "1.4.1", "severity": "critical", "description": "Protan issue", "location": "Button"}], "passes": False, "summary": "Protan has issues", "cvd_label": "Protanopia (red-blind)"},
            "Deuteranopia (green-blind)": {"findings": [{"type": "Color Only Information", "wcag_criterion": "1.4.1", "severity": "serious", "description": "Deuter issue", "location": "Button"}], "passes": False, "summary": "Deuter has issues", "cvd_label": "Deuteranopia (green-blind)"},
        }
        
        # Change to deuteranopia
        cvd_transformed, cvd_report, comparison = handle_cvd_selector_change('deuteranopia', img, original_vlm, cvd_results)
        
        assert cvd_transformed is not None, "Should return CVD transformed image"
        assert cvd_report != gr.update(), "Should return updated CVD report"
        assert "Deuteranopia" in cvd_report or "deuter" in cvd_report.lower(), "CVD report should show Deuteranopia results"
        assert "Deuteranopia" in comparison, "Comparison should show Deuteranopia results"

    def test_original_image_displayed_on_upload(self):
        """handle_file_upload should return original image for original_image component."""
        from app import handle_file_upload
        import io
        
        # Create a test image file with unique color to avoid cache conflicts
        img = Image.new('RGB', (100, 100), color='cyan')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        file_bytes = buf.getvalue()
        
        result = handle_file_upload(file_bytes)
        
        # Returns: gallery, current_cvd_grid, original_image, cvd_image, current_original, current_original_vlm, current_cvd_results, wcag_comparison_output
        gallery, cvd_grid_state, original_image, cvd_image, current_original, current_original_vlm, current_cvd_results, comparison = result
        
        # original_image should be the PIL Image
        assert isinstance(original_image, Image.Image), "original_image should be a PIL Image"
        assert original_image.size == (100, 100), "original_image should have correct size"
        
        # current_original should be the same PIL Image
        assert current_original is original_image, "current_original should reference the same image"
        
        # Gallery should have 9 entries (1 original + 8 CVD)
        assert len(gallery) == 9, f"Gallery should have 9 entries, got {len(gallery)}"

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
