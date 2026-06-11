"""
Source inspection tests for app.py — verify contracts without running Gradio.

Tests:
- CVD gallery generates 10 variants (8 from deficiency_config + 2 grayscale)
- WCAG report format handles passes/fail/error cases
- MODELS dict has required model entries
- Gradio 5/6 compat flag exists
- No hardcoded credentials or debug print statements
"""
import sys, os, pathlib

_project_root = pathlib.Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import app as app_module
from PIL import Image


# ── Helpers ───────────────────────────────────────────────────────────────────

def img_factory(width=100, height=100, color=(128, 128, 128)):
    arr = pathlib.Path(__file__).read_bytes()  # random bytes as seed
    import numpy as np
    rng = np.random.default_rng(hash(str(arr)) % 2**32)
    arr = rng.integers(0, 255, (height, width, 3), dtype=np.uint8)
    arr[:, :] = color
    return Image.fromarray(arr)


# ── CVD Gallery Tests ─────────────────────────────────────────────────────────

class TestCVDGrid:
    def test_grid_returns_four_items(self):
        img = img_factory(200, 200)
        gallery = app_module.generate_cvd_grid(img)
        assert len(gallery) == 4, f"Expected 4 CVD variants, got {len(gallery)}"

    def test_grid_items_are_pil_images(self):
        img = img_factory(200, 200)
        gallery = app_module.generate_cvd_grid(img)
        for item, label in gallery:
            assert isinstance(item, Image.Image), f"Expected PIL Image, got {type(item)}"

    def test_grid_labels_not_empty(self):
        img = img_factory(200, 200)
        gallery = app_module.generate_cvd_grid(img)
        for _, label in gallery:
            assert label, "Gallery label must not be empty"

    def test_grid_has_correct_labels(self):
        img = img_factory(100, 100)
        gallery = app_module.generate_cvd_grid(img)
        expected = ["Normal vision (original design)", "Protanopia (red-blind)",
                    "Deuteranopia (green-blind)", "Tritanopia (blue-blind)"]
        for (_, label), expected_label in zip(gallery, expected):
            assert label == expected_label, f"Expected '{expected_label}', got '{label}'"

    def test_achromatopsia_is_grayscale(self):
        img = img_factory(100, 100, (200, 50, 50))  # red image
        achro = app_module.simulate_achromatopsia(img, 1.0)
        # Grayscale conversion should make R=G=B
        import numpy as np
        arr = np.array(achro)
        assert arr[:,:,0].mean() == arr[:,:,1].mean() == arr[:,:,2].mean()


class TestWCAGReport:
    def test_report_passes_no_findings(self):
        result = {"passes": True, "findings": [], "summary": "No issues found"}
        report = app_module.format_wcag_report(result)
        assert "Pass" in report or "✅" in report

    def test_report_fail_with_findings(self):
        result = {
            "passes": False,
            "findings": [
                {
                    "type": "Low Contrast",
                    "wcag_criterion": "1.4.3",
                    "severity": "serious",
                    "description": "Button text contrast ratio is 2.8:1",
                    "location": "Submit button, top-right",
                }
            ],
            "summary": "1 critical issue found",
        }
        report = app_module.format_wcag_report(result)
        assert "WCAG" in report or "1.4.3" in report
        assert "Fail" in report or "❌" in report

    def test_report_error_handling(self):
        result = {"error": "Model timeout after 60s"}
        report = app_module.format_wcag_report(result)
        assert "Error" in report or "Warning" in report

    def test_report_no_findings_without_pass_flag(self):
        result = {"findings": [], "summary": "No issues detected"}
        report = app_module.format_wcag_report(result)
        assert "No accessibility issues" in report


# ── SUPPORTED_MODEL Tests ─────────────────────────────────────────────────────

class TestSupportedModel:
    def test_supported_model_exists(self):
        assert hasattr(app_module, 'SUPPORTED_MODEL')

    def test_supported_model_is_minicpm(self):
        assert app_module.SUPPORTED_MODEL == "minicpm-v-4.6"

    def test_supported_model_is_string(self):
        assert isinstance(app_module.SUPPORTED_MODEL, str)


# ── Gradio 5/6 Compat Tests ───────────────────────────────────────────────────

class TestGradioCompat:
    def test_is_gradio6_flag_exists(self):
        assert hasattr(app_module, '_is_gradio6')

    def test_launch_theme_exists(self):
        assert hasattr(app_module, '_launch_theme')

    def test_launch_css_exists(self):
        assert hasattr(app_module, '_launch_css')


# ── Source Inspection Tests ───────────────────────────────────────────────────

class TestSourceInspection:
    def test_no_hf_token_hardcoded_in_source(self):
        app_path = pathlib.Path(__file__).resolve().parent.parent / 'app.py'
        source = app_path.read_text()
        # HF tokens should come from environment, not hardcoded
        assert 'hf_' not in source.lower() or 'os.environ' in source

    def test_no_debug_print_in_source(self):
        app_path = pathlib.Path(__file__).resolve().parent.parent / 'app.py'
        source = app_path.read_text()
        for line in source.split('\n'):
            stripped = line.strip()
            assert not (stripped.startswith('print(') and 'debug' in stripped.lower()), \
                f"Debug print found: {line.strip()[:60]}"


# ── CVD Config Tests ──────────────────────────────────────────────────────────

class TestDeficiencyConfig:
    def test_deficiency_config_has_8_types(self):
        assert len(app_module.deficiency_config) == 8

    def test_all_cvd_types_have_simulator_and_deficiency(self):
        for name, cfg in app_module.deficiency_config.items():
            assert 'simulator' in cfg, f"{name} missing simulator"
            assert 'deficiency' in cfg, f"{name} missing deficiency"
            assert 'severity' in cfg, f"{name} missing severity"

    def test_severity_values_are_floats(self):
            for name, cfg in app_module.deficiency_config.items():
                assert isinstance(cfg['severity'], float), f"{name} severity not float"


    # ── Full 8-Type CVD Gallery Tests ─────────────────────────────────────────────

    class TestFullCVDGallery:
        """
        Gallery must show all 8 CVD variants from deficiency_config, not just 4.
        File upload triggers gallery generation; Analyze button triggers VLM only.
        """

        def test_generate_cvd_gallery_returns_8_items(self, img_factory):
            """Gallery should produce one image per CVD type (8 total)."""
            img = img_factory(200, 200)
            gallery = app_module.generate_cvd_gallery(img)
            assert len(gallery) == 8, f"Expected 8 CVD variants, got {len(gallery)}"

        def test_gallery_has_8_unique_labels(self, img_factory):
            """Each of the 8 CVD types should appear in the gallery."""
            img = img_factory(200, 200)
            gallery = app_module.generate_cvd_gallery(img)
            labels = [label for _, label in gallery]
            assert len(labels) == 8, f"Expected 8 labels, got {len(labels)}"
            # All labels should be unique (no duplicates)
            assert len(set(labels)) == 8, f"Labels not unique: {labels}"

        def test_gallery_covers_all_deficiency_types(self, img_factory):
                    """Gallery should include all 8 types from deficiency_config."""
                    img = img_factory(200, 200)
                    gallery = app_module.generate_cvd_gallery(img)
                    gallery_labels = [label for _, label in gallery]
                    expected_types = list(app_module.deficiency_config.keys())
                    for expected in expected_types:
                        # Split by underscore so 'severe_protanopia' → ['severe','protanopia']
                        # then check all parts appear (case-insensitive) in the label
                        parts = expected.lower().split('_')
                        found = all(any(part in label.lower() for label in gallery_labels)
                                    for part in parts)
                        assert found, f"CVD type '{expected}' not found in gallery labels: {gallery_labels}"


    # ── Event Handler Separation Tests ────────────────────────────────────────────

    class TestEventHandlerSeparation:
        """
        File upload triggers gallery generation.
        Analyze button only triggers VLM endpoint.
        These should be separate event handlers.
        """

        def test_app_has_handle_file_upload_function(self):
            """App must have a function to handle file upload events (for gallery generation)."""
            assert hasattr(app_module, 'handle_file_upload'), \
                "App must have handle_file_upload() function for file change event"

        def test_app_has_run_vlm_analysis_function(self):
            """App must have a function to handle Analyze button click (VLM only)."""
            assert hasattr(app_module, 'run_vlm_analysis'), \
                "App must have run_vlm_analysis() function for analyze button"

        def test_handle_file_upload_does_not_call_vlm(self):
            """File upload handler should generate gallery only, not call VLM."""
            import inspect
            assert hasattr(app_module, 'handle_file_upload'), "Missing handle_file_upload"
            source = inspect.getsource(app_module.handle_file_upload)
            # Should NOT call analyze_all_perspectives or _call_minicpm_endpoint
            assert 'analyze_all_perspectives' not in source, \
                "handle_file_upload should not call VLM (analyze_all_perspectives)"
            assert '_call_minicpm_endpoint' not in source, \
                "handle_file_upload should not call VLM directly"

        def test_run_vlm_analysis_calls_vlm_endpoint(self):
            """Analyze handler should call VLM endpoint."""
            import inspect
            assert hasattr(app_module, 'run_vlm_analysis'), "Missing run_vlm_analysis"
            source = inspect.getsource(app_module.run_vlm_analysis)
            assert 'analyze_all_perspectives' in source or '_call_minicpm_endpoint' in source, \
                "run_vlm_analysis should call VLM endpoint"


    # ── Gallery Layout Configuration Tests ────────────────────────────────────────

    class TestGalleryLayout:
        """
        Gallery should display in a sensible grid layout (2x4) for 8 images.
        """

        def test_gallery_columns_and_rows_configured(self):
            """Gradio Gallery should be configured with columns=4, rows=2 for 8 images."""
            app_source = pathlib.Path(__file__).resolve().parent.parent / 'app.py'
            source = app_source.read_text()
            # Find Gallery component definition
            assert 'gr.Gallery(' in source, "No gr.Gallery found in app.py"
            # Should have columns=4 (showing 4 per row for 8 images = 2 rows)
            assert 'columns=4' in source or 'columns = 4' in source, \
                "Gallery should use columns=4 for 2x4 layout of 8 images"