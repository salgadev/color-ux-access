"""
Tests for CVD functionality and simplified UI layout.

The UI now has:
1. Upload area (file input + Analyze button)
2. CVD Gallery — always visible comparison grid (9 variants)
3. WCAG Report (merged multi-perspective analysis)
4. WCAG Comparison Panel (side-by-side criterion comparison)
"""
import sys, pathlib
_project_root = pathlib.Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from PIL import Image
import numpy as np
from unittest.mock import patch, MagicMock


class TestCVDCache:
    """Tests for CVD image cache module-level functionality."""

    def test_cvd_cache_module_level_exists(self):
        """CVD image cache should be module-level dict for persistence."""
        import app as app_module
        assert hasattr(app_module, '_cvd_image_cache'), "app should have _cvd_image_cache"
        assert isinstance(app_module._cvd_image_cache, dict), "_cvd_image_cache should be a dict"

    def test_cvd_cache_key_uses_original_hash_and_variant(self):
        """Cache key should combine original image hash and CVD variant."""
        import app as app_module
        from PIL import Image
        import io

        # Create test image
        img = Image.new('RGB', (100, 50), color='red')
        variant = 'protanopia'

        # Check _get_cvd_cache_key exists and produces consistent keys
        if hasattr(app_module, '_get_cvd_cache_key'):
            key1 = app_module._get_cvd_cache_key(img, variant)
            key2 = app_module._get_cvd_cache_key(img, variant)
            assert key1 == key2, "Same image+variant should produce same cache key"

            # Different variant should produce different key
            key3 = app_module._get_cvd_cache_key(img, 'deuteranopia')
            assert key1 != key3, "Different variants should produce different keys"

    def test_cvd_cache_stores_and_retrieves(self):
        """Cache should store and retrieve transformed images."""
        import app as app_module
        from PIL import Image

        img = Image.new('RGB', (50, 50), color='red')
        variant = 'protanopia'
        transformed = Image.new('RGB', (50, 50), color='blue')

        if hasattr(app_module, '_cvd_image_cache') and hasattr(app_module, '_get_cvd_cache_key'):
            key = app_module._get_cvd_cache_key(img, variant)
            app_module._cvd_image_cache[key] = transformed

            assert key in app_module._cvd_image_cache
            assert app_module._cvd_image_cache[key] is transformed

    def test_get_cvd_transformed_returns_cached_when_available(self):
        """get_cvd_transformed should return cached result on second call."""
        import app as app_module
        from PIL import Image
        from unittest.mock import patch

        original = Image.new('RGB', (50, 50), color='red')

        if hasattr(app_module, 'get_cvd_transformed'):
            with patch('app.simulate_cvd') as mock_simulate:
                mock_simulate.return_value = Image.new('RGB', (50, 50), color='blue')

                # First call - should call simulate_cvd
                result1 = app_module.get_cvd_transformed(original, 'protanopia')
                first_calls = mock_simulate.call_count

                # Second call - should use cache
                result2 = app_module.get_cvd_transformed(original, 'protanopia')
                second_calls = mock_simulate.call_count

                assert second_calls == first_calls, "Should not call simulate_cvd on cached hit"
                assert result1 is result2, "Should return same cached object"

    def test_cvd_variant_options_match_expected(self):
        """CVD variants should match the 8 types from deficiency_config."""
        import app as app_module
        expected_variants = {
            'protanopia', 'severe_protanopia', 'deuteranopia', 'severe_deuteranopia',
            'tritanopia', 'protanomaly', 'deuteranomaly', 'tritanomaly'
        }
        assert hasattr(app_module, 'deficiency_config')
        actual_variants = set(app_module.deficiency_config.keys())
        assert actual_variants == expected_variants

    def test_simulate_cvd_works_for_all_variants(self):
        """simulate_cvd should handle all CVD variant types including achromatopsia."""
        from app import simulate_cvd, simulate_achromatopsia
        from color_ux_access.cvd_sim import simulate_cvd as cvd_sim

        # Create test image
        img = Image.new('RGB', (100, 100), color='red')

        # Test all variants from deficiency_config
        variants = ['protanopia', 'deuteranopia', 'tritanopia', 'protanomaly',
                    'deuteranomaly', 'tritanomaly']

        for variant in variants:
            result = cvd_sim(img, variant)
            assert isinstance(result, Image.Image)
            assert result.size == img.size

        # Test achromatopsia separately (handled by simulate_achromatopsia)
        result = simulate_achromatopsia(img, 1.0)
        assert isinstance(result, Image.Image)
        assert result.size == img.size
        # Achromatopsia should be grayscale
        arr = np.array(result)
        # All RGB channels should be equal for grayscale
        assert np.allclose(arr[:, :, 0], arr[:, :, 1])
        assert np.allclose(arr[:, :, 1], arr[:, :, 2])


class TestSimplifiedUILayout:
    """Tests for the simplified UI layout without CVD selector or split-view."""

    def test_app_has_basic_structure(self):
        """App should have basic Gradio Blocks structure."""
        import app as app_module
        assert hasattr(app_module, 'demo'), "app should have a demo Blocks instance"

    def test_ui_has_upload_area(self):
        """UI should have file input for screenshot upload."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert 'gr.File' in source, "Should have gr.File for upload"
        assert 'Screenshot' in source, "File input should have Screenshot label"
        assert '.png' in source and '.jpg' in source, "Should accept image formats"

    def test_ui_has_analyze_button(self):
        """UI should have a single Analyze button."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert 'gr.Button' in source, "Should have gr.Button"
        assert 'Analyze' in source, "Button should be labeled Analyze"
        assert "variant='primary'" in source or 'variant="primary"' in source, "Analyze button should be primary"

    def test_ui_has_cvd_gallery(self):
        """UI should have CVD Gallery component showing all variants."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert 'gr.Gallery' in source, "Should have gr.Gallery for CVD gallery"
        assert 'Color-Vision Simulation Gallery' in source, "Gallery should have descriptive label"
        assert '9 variants' in source, "Gallery label should mention 9 variants"

    def test_ui_has_wcag_report_output(self):
        """UI should have WCAG report output (Markdown)."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert 'gr.Markdown' in source, "Should have gr.Markdown for reports"
        assert 'WCAG Accessibility Report' in source, "Should have WCAG report label"

    def test_ui_has_wcag_comparison_output(self):
        """UI should have WCAG comparison panel."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert 'WCAG Comparison: Original vs CVD' in source, "Should have comparison panel"

    def test_ui_no_cvd_selector(self):
        """UI should NOT have CVD variant Radio selector."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert 'cvd_selector' not in source, "Should not have cvd_selector Radio component"
        assert "gr.Radio" not in source, "Should not use gr.Radio for CVD selection"

    def test_ui_no_split_view(self):
        """UI should NOT have split-view comparison grid."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert 'split-view-grid' not in source, "Should not have split-view-grid CSS class"
        assert 'split-view-column' not in source, "Should not have split-view-column CSS class"
        assert 'split-view-image-container' not in source, "Should not have split-view-image-container CSS class"
        assert 'split-view-report-container' not in source, "Should not have split-view-report-container CSS class"

    def test_ui_no_original_cvd_image_components(self):
        """UI should NOT have separate original_image and cvd_image components."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        # The only gr.Image should be in the Gallery (handled automatically)
        # There should be no explicit gr.Image for original or CVD view
        # gr.Image is used by Gallery internally, but we check there's no explicit one
        assert 'original_image = gr.Image' not in source, "Should not have original_image component"
        assert 'cvd_image = gr.Image' not in source, "Should not have cvd_image component"
        assert 'cvd_report_output =' not in source, "Should not have cvd_report_output component"

    def test_generate_cvd_gallery_includes_original_as_first_entry(self):
        """generate_cvd_gallery should return original as first entry with correct label."""
        from app import generate_cvd_gallery
        img = Image.new('RGB', (100, 100), color='red')
        gallery = generate_cvd_gallery(img)

        # Should have 9 entries: 1 original + 8 CVD variants
        assert len(gallery) == 9, f"Expected 9 entries, got {len(gallery)}"

        # First entry should be original
        first_img, first_label = gallery[0]
        assert first_label == "Normal vision (original design)", f"First label should be 'Normal vision (original design)', got '{first_label}'"
        assert first_img is img, "First image should be the original"

    def test_vlm_cvd_prompts_includes_original(self):
        """_VLM_CVD_PROMPTS should have an entry for original design."""
        import app as app_module
        assert "Normal vision (original design)" in app_module._VLM_CVD_PROMPTS
        prompt = app_module._VLM_CVD_PROMPTS["Normal vision (original design)"]
        assert "normal color vision" in prompt.lower() or "normal vision" in prompt.lower()

    def test_analyze_all_perspectives_includes_original(self):
        """analyze_all_perspectives_with_cache should analyze original perspective."""
        from app import analyze_all_perspectives_with_cache, _vlm_merged_cache
        from unittest.mock import patch

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
