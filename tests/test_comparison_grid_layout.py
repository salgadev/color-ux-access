"""
Tests for Comparison Grid Layout with Perspective Cards.

Requirements:
1. Replace radio-button selector with side-by-side comparison grid
2. One card per perspective: Original, Protanopia, Deuteranopia, Tritanopia, and other CVD variants
3. Each card contains: (1) clear label, (2) image display area, (3) WCAG results placeholder
4. All perspective images render simultaneously on upload without user interaction
5. No tabs — true side-by-side comparison grid
"""
import sys
import pathlib

_project_root = pathlib.Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import app as app_module
from PIL import Image
import gradio as gr
from unittest.mock import patch


class TestComparisonGridLayout:
    """Tests for the new comparison grid layout with perspective cards."""

    def test_generate_cvd_gallery_returns_all_perspectives(self):
        """generate_cvd_gallery should return all 9 entries: original + 8 CVD variants."""
        img = Image.new('RGB', (100, 100), color='red')
        gallery = app_module.generate_cvd_gallery(img)

        # Should have 9 entries: 1 original + 8 CVD variants
        assert len(gallery) == 9, f"Expected 9 entries, got {len(gallery)}"

        # First entry should be original
        first_img, first_label = gallery[0]
        assert first_label == "Normal vision (original design)"
        assert first_img is img

        # Remaining 8 should be CVD variants with correct labels
        expected_labels = {
            "Protanopia (red-blind)",
            "Severe Protanopia (red-blind)",
            "Deuteranopia (green-blind)",
            "Severe Deuteranopia (green-blind)",
            "Tritanopia (blue-blind)",
            "Protanomaly (red-weak)",
            "Deuteranomaly (green-weak)",
            "Tritanomaly (blue-weak)",
        }
        actual_labels = {label for _, label in gallery[1:]}
        assert actual_labels == expected_labels, f"Expected {expected_labels}, got {actual_labels}"

    def test_ui_has_comparison_grid_with_perspective_cards(self):
        """UI should have a comparison grid with one card per perspective."""
        source = pathlib.Path(app_module.__file__).read_text()

        # Should have perspective_labels list with all 9 perspectives
        assert 'perspective_labels' in source, "Should have perspective_labels list"
        assert 'Normal vision (original design)' in source
        assert 'Protanopia (red-blind)' in source
        assert 'Deuteranopia (green-blind)' in source
        assert 'Tritanopia (blue-blind)' in source

        # Should have comparison-grid CSS class container
        assert "comparison-grid" in source, "Should have comparison-grid CSS class"

        # Should have perspective-card CSS classes
        assert "perspective-card" in source, "Should have perspective-card CSS class"
        assert "perspective-card-header" in source, "Should have card header class"
        assert "perspective-card-image-wrapper" in source, "Should have image wrapper class"
        assert "perspective-card-report" in source, "Should have report class"

        # Should loop through labels to create cards
        assert 'for label in perspective_labels' in source, "Should loop through perspective_labels"

    def test_each_perspective_card_has_label_image_wcag_placeholder(self):
        """Each perspective card should have: label, image display, WCAG placeholder."""
        source = pathlib.Path(app_module.__file__).read_text()

        # Should create Image components inside the loop
        assert 'gr.Image' in source, "Should create gr.Image components"
        
        # Should create Markdown components for WCAG reports inside the loop
        assert 'gr.Markdown' in source, "Should create gr.Markdown components"
        
        # Card creation should include Markdown for label (header)
        assert "perspective-card-header" in source
        
        # Labels should be present for each perspective in the labels list
        expected_labels = [
            "Normal vision (original design)",
            "Protanopia",
            "Deuteranopia",
            "Tritanopia",
            "Protanomaly",
            "Deuteranomaly",
            "Tritanomaly",
            "Severe Protanopia",
            "Severe Deuteranopia",
        ]
        for label in expected_labels:
            assert label in source, f"Should have label '{label}' in UI"

    def test_all_images_render_on_upload_no_user_interaction(self):
        """On file upload, all perspective images should render simultaneously."""
        from app import handle_file_upload
        import io

        # Create a test image
        img = Image.new('RGB', (100, 100), color='cyan')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        file_bytes = buf.getvalue()

        result = handle_file_upload(file_bytes)

        # Result structure: [cvd_grid, state, container_visible, 9 card_images, 9 card_reports, comparison]
        cvd_grid_hidden = result[0]
        cvd_grid_state = result[1]
        container_visible = result[2]
        card_images = result[3:12]  # 9 card images
        card_reports = result[12:21]  # 9 card reports
        comparison = result[21]

        # cvd_grid (hidden) should have all 9 entries
        assert len(cvd_grid_hidden) == 9, f"Hidden gallery should have 9 entries, got {len(cvd_grid_hidden)}"

        # cvd_grid_state should have all 9 entries
        assert len(cvd_grid_state) == 9, f"cvd_grid_state should have 9 entries, got {len(cvd_grid_state)}"

        # Container should become visible
        assert container_visible, "Comparison grid container should be visible after upload"

        # Should have 9 card images
        assert len(card_images) == 9, f"Should have 9 card images, got {len(card_images)}"
        
        # Should have 9 card reports
        assert len(card_reports) == 9, f"Should have 9 card reports, got {len(card_reports)}"

        # Each card image should be a PIL Image
        for card_img in card_images:
            assert isinstance(card_img, Image.Image), f"Card image should be PIL Image, got {type(card_img)}"

        # Each card report should be a string placeholder
        for card_report in card_reports:
            assert isinstance(card_report, str), f"Card report should be string, got {type(card_report)}"
            assert "WCAG results will appear" in card_report, "Should have placeholder text"

    def test_no_tabs_in_layout(self):
        """Layout should not use tabs — true side-by-side comparison grid."""
        source = pathlib.Path(app_module.__file__).read_text()

        # Should not use gr.Tabs or gr.Tab
        assert 'gr.Tabs' not in source, "Should not use gr.Tabs"
        assert 'gr.Tab' not in source, "Should not use gr.Tab"

    def test_grid_responsive_multiple_columns(self):
        """Grid should be responsive with multiple columns on desktop."""
        source = pathlib.Path(app_module.__file__).read_text()

        # Should use CSS grid for responsive layout
        assert 'grid-template-columns: repeat(3, 1fr)' in source, "Should have 3-column grid on desktop"

        # Should have responsive breakpoints
        assert '@media (max-width: 1024px)' in source, "Should have 1024px breakpoint"
        assert '@media (max-width: 768px)' in source, "Should have 768px breakpoint"
        assert '@media (max-width: 480px)' in source, "Should have 480px breakpoint (mobile)"

        # Should stack to 2 columns at 1024px
        assert 'grid-template-columns: repeat(2, 1fr)' in source

        # Should stack to 1 column at 480px
        assert 'grid-template-columns: 1fr' in source


class TestPerspectiveCardComponents:
    """Tests for individual perspective card components."""

    def test_card_structure_has_required_elements(self):
        """Each perspective card should have header, image wrapper, and report sections."""
        source = pathlib.Path(app_module.__file__).read_text()

        # Card structure: gr.Group(perspective-card) contains:
        # - gr.Markdown (header with label)
        # - gr.Group(perspective-card-image-wrapper) with gr.Image
        # - gr.Group(perspective-card-report) with gr.Markdown (WCAG results)
        assert "perspective-card" in source
        assert "perspective-card-header" in source
        assert "perspective-card-image-wrapper" in source
        assert "perspective-card-report" in source


class TestComparisonGridEventHandlers:
    """Tests for event handlers in the new comparison grid layout."""

    def test_handle_file_upload_populates_all_cards(self):
        """handle_file_upload should populate all perspective cards with images."""
        from app import handle_file_upload
        import io

        img = Image.new('RGB', (100, 100), color='yellow')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        file_bytes = buf.getvalue()

        result = handle_file_upload(file_bytes)

        cvd_grid_hidden = result[0]
        cvd_grid_state = result[1]
        card_images = result[3:12]
        card_reports = result[12:21]

        # Gallery should have all 9 images
        assert len(cvd_grid_hidden) == 9

        # State should have all 9 entries
        assert len(cvd_grid_state) == 9

        # Should have 9 card images (PIL Images)
        assert len(card_images) == 9
        for img_obj in card_images:
            assert isinstance(img_obj, Image.Image)

        # Should have 9 card reports (strings with placeholders)
        assert len(card_reports) == 9
        for card_report in card_reports:
            assert isinstance(card_report, str)
            assert "WCAG results will appear" in card_report

    def test_analyze_all_perspectives_populates_wcag_for_all_cards(self):
        """Running analysis should populate WCAG results for all perspective cards."""
        from app import analyze_all_perspectives_with_cache, _vlm_merged_cache, _vlm_cache
        import gradio as gr

        img = Image.new('RGB', (100, 50), color='green')
        cvd_grid = [
            (img, "Normal vision (original design)"),
            (img, "Protanopia (red-blind)"),
            (img, "Deuteranopia (green-blind)"),
            (img, "Tritanopia (blue-blind)"),
        ]

        _vlm_merged_cache.clear()
        _vlm_cache.clear()

        with patch('app._call_minicpm_endpoint') as mock_vlm:
            mock_vlm.return_value = {"findings": [], "passes": True, "summary": "Test"}

            progress = gr.Progress()
            progress.tqdm = lambda x: x
            progress.__call__ = lambda x, desc=None: None

            result = analyze_all_perspectives_with_cache(cvd_grid, progress=progress)

            # Should call VLM for each perspective
            assert mock_vlm.call_count == 4

            # Result should have findings from all perspectives
            assert 'findings' in result

    def test_run_vlm_analysis_returns_reports_for_all_cards(self):
        """run_vlm_analysis should return WCAG reports for all 9 perspective cards."""
        from app import run_vlm_analysis, _vlm_merged_cache, _vlm_cache
        import gradio as gr

        img = Image.new('RGB', (100, 50), color='orange')
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

        with patch('app._call_minicpm_endpoint') as mock_vlm:
            mock_vlm.return_value = {"findings": [], "passes": True, "summary": "Test"}

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
            
            # Each card report should be a formatted WCAG report
            for card_report in card_reports:
                assert isinstance(card_report, str)
                assert "WCAG" in card_report or "Pass" in card_report or "No accessibility" in card_report

            assert original_vlm is not None
            assert isinstance(cvd_results, dict)
            assert len(cvd_results) == 8  # 8 CVD variants (excluding original)


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])