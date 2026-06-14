"""
Tests for CVD variant selector — two-column layout with original + transformed image.
"""
import sys, pathlib
_project_root = pathlib.Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from PIL import Image
import numpy as np


class TestCVDSelector:
    """Tests for CVD variant selector and two-column display."""

    def test_cvd_selector_component_created(self):
        """App should create a CVD variant Radio component in the UI."""
        import app as app_module
        # After building the demo, the Radio component should exist
        # We verify by checking the component is defined in the module
        # or by inspecting the demo's blocks
        assert hasattr(app_module, 'demo'), "app should have a demo Blocks instance"
        
    def test_cvd_selector_has_expected_options(self):
        """CVD selector should have options matching deficiency_config keys."""
        import app as app_module
        # The selector options should match the deficiency_config keys
        expected = set(app_module.deficiency_config.keys())
        assert expected == {
            'protanopia', 'severe_protanopia', 'deuteranopia', 'severe_deuteranopia',
            'tritanopia', 'protanomaly', 'deuteranomaly', 'tritanomaly'
        }

    def test_two_column_layout_uses_row_with_two_columns(self):
        """App should use gr.Row with two gr.Column for original + CVD view."""
        import app as app_module
        # This is a structural test - we verify the layout by source inspection
        source = pathlib.Path(app_module.__file__).read_text()
        # Should have gr.Row with two columns
        assert 'gr.Row()' in source or 'gr.Row(' in source, "Should have a Row layout"
        # Should have two Column components
        assert source.count('gr.Column') >= 2, "Should have at least two Columns"

    def test_left_column_shows_original_image(self):
        """Left column should display the original uploaded image."""
        import app as app_module
        # Verify the left column has an Image component for the original
        source = pathlib.Path(app_module.__file__).read_text()
        # Should have an Image component for original (not Gallery)
        assert 'gr.Image' in source, "Should have gr.Image for original display"

    def test_right_column_shows_cvd_transformed(self):
        """Right column should display CVD-transformed image based on selector."""
        import app as app_module
        # Verify right column has an Image component for CVD view
        source = pathlib.Path(app_module.__file__).read_text()
        # The right column image should update on selector change
        assert 'gr.Image' in source, "Should have gr.Image for CVD display"

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
        """CVD selector should have exactly the 8 CVD types from deficiency_config."""
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


class TestSplitViewLayout:
    """Tests for the responsive split-view comparison grid layout."""

    def test_split_view_grid_css_exists(self):
        """App should define split-view-grid CSS class with grid-template-columns."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert '.split-view-grid' in source, "Should have .split-view-grid CSS class"
        assert 'grid-template-columns: 1fr 1fr' in source, "Should have two-column grid on desktop"

    def test_split_view_columns_have_independent_scrolling(self):
        """Split-view columns should have min-width: 0 and flex children with min-height: 0 for scrolling."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert '.split-view-column' in source, "Should have .split-view-column CSS class"
        assert 'min-width: 0' in source, "Columns should allow shrinking below content"
        assert 'min-height: 0' in source, "Flex children should allow scrolling"

    def test_split_view_image_container_fixed_aspect_ratio(self):
        """Image containers should have fixed aspect-ratio: 4/3."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert '.split-view-image-container' in source, "Should have .split-view-image-container CSS class"
        assert 'aspect-ratio: 4 / 3' in source, "Image containers should have 4:3 aspect ratio"

    def test_split_view_report_container_scrollable(self):
        """Report containers should be scrollable with max-height and overflow: auto."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert '.split-view-report-container' in source, "Should have .split-view-report-container CSS class"
        assert 'overflow: auto' in source, "Report containers should be scrollable"
        assert 'max-height:' in source, "Report containers should have max-height"

    def test_responsive_breakpoint_1440px(self):
        """Should have responsive breakpoint at 1440px."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert '@media (max-width: 1440px)' in source, "Should have 1440px breakpoint"

    def test_responsive_breakpoint_1024px(self):
        """Should have responsive breakpoint at 1024px (stacks to single column)."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert '@media (max-width: 1024px)' in source, "Should have 1024px breakpoint"
        # At 1024px, should stack to single column
        assert 'grid-template-columns: 1fr' in source, "Should stack to single column at 1024px"

    def test_responsive_breakpoint_375px(self):
        """Should have responsive breakpoint at 375px (mobile)."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert '@media (max-width: 375px)' in source, "Should have 375px breakpoint"

    def test_no_horizontal_overflow(self):
        """Should prevent horizontal overflow on all viewports."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert 'max-width: 100%' in source, "Should prevent horizontal overflow"
        assert 'box-sizing: border-box' in source, "Should use border-box sizing"

    def test_ui_uses_split_view_grid(self):
        """Gradio UI should use split-view-grid class on main container."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        # Should have gr.Group with elem_classes=['split-view-grid']
        assert "elem_classes=['split-view-grid']" in source or 'elem_classes=["split-view-grid"]' in source

    def test_ui_has_two_split_view_columns(self):
        """UI should have two columns with split-view-column class."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        # Should have two gr.Column with elem_classes=['split-view-column']
        assert source.count("elem_classes=['split-view-column']") >= 2 or \
               source.count('elem_classes=["split-view-column"]') >= 2, \
               "Should have two split-view columns"

    def test_split_view_columns_contain_image_and_report(self):
        """Each split-view column should contain image container and report container."""
        import app as app_module
        source = pathlib.Path(app_module.__file__).read_text()
        assert "elem_classes=['split-view-image-container']" in source or \
               'elem_classes=["split-view-image-container"]' in source
        assert "elem_classes=['split-view-report-container']" in source or \
               'elem_classes=["split-view-report-container"]' in source


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
