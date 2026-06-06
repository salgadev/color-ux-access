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

class TestCVDGallery:
    def test_gallery_returns_ten_items(self):
        img = img_factory(200, 200)
        gallery = app_module.generate_cvd_gallery(img)
        assert len(gallery) == 10, f"Expected 10 CVD variants, got {len(gallery)}"

    def test_gallery_items_are_pil_images(self):
        img = img_factory(200, 200)
        gallery = app_module.generate_cvd_gallery(img)
        for item, label in gallery:
            assert isinstance(item, Image.Image), f"Expected PIL Image, got {type(item)}"

    def test_gallery_labels_not_empty(self):
        img = img_factory(200, 200)
        gallery = app_module.generate_cvd_gallery(img)
        for _, label in gallery:
            assert label, "Gallery label must not be empty"

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
        assert "Error" in report or "⚠" in report

    def test_report_no_findings_without_pass_flag(self):
        result = {"findings": [], "summary": "No issues detected"}
        report = app_module.format_wcag_report(result)
        assert "No accessibility issues" in report


# ── MODELS Dict Tests ─────────────────────────────────────────────────────────

class TestMODELS:
    def test_models_dict_exists(self):
        assert hasattr(app_module, 'MODELS')

    def test_aya_vision_model_present(self):
        assert "aya-vision-32b" in app_module.MODELS
        entry = app_module.MODELS["aya-vision-32b"]
        assert "model_id" in entry
        assert entry["model_id"] == "CohereLabs/aya-vision-32b"

    def test_minicpm_model_present(self):
        assert "minicpm-v-4.6" in app_module.MODELS
        entry = app_module.MODELS["minicpm-v-4.6"]
        assert "model_id" in entry

    def test_all_models_have_required_keys(self):
        for name, entry in app_module.MODELS.items():
            assert "model_id" in entry, f"{name} missing model_id"
            assert "provider" in entry, f"{name} missing provider"


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