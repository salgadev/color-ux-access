"""
Smoke tests — verify core modules are importable and basic contracts hold.
No VLM API calls, no Playwright, no network.
"""
import sys, os, pathlib

# Ensure project root is on path (belt-and-suspenders; pytest.ini also sets pythonpath)
_project_root = pathlib.Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import daltonlens
from daltonlens import simulate
from colorspacious import cspace_convert
import numpy as np
from PIL import Image


class TestCoreImports:
    def test_daltonlens_import(self):
        assert simulate.Simulator_Machado2009 is not None

    def test_colorspacious_import(self):
        # cspace_convert should be callable
        assert callable(cspace_convert)

    def test_cv_sim_import(self):
        from color_ux_access import cvd_sim
        assert hasattr(cvd_sim, 'simulate_cvd')
        assert hasattr(cvd_sim, 'CVD_VARIANTS')

    def test_app_import(self):
        import app as app_module
        assert hasattr(app_module, 'deficiency_config')
        assert hasattr(app_module, 'generate_cvd_gallery')
        assert hasattr(app_module, 'format_wcag_report')


class TestDaltonLens:
    def test_simulator_machado2009(self):
        sim = simulate.Simulator_Machado2009()
        arr = np.zeros((10, 10, 3), dtype=np.uint8)
        arr[:, :] = [200, 100, 50]
        result = sim.simulate_cvd(arr, simulate.Deficiency.DEUTAN, 1.0)
        assert result.shape == (10, 10, 3)
        assert result.dtype == np.uint8

    def test_cvd_variants_defined(self):
        from color_ux_access.cvd_sim import CVD_VARIANTS
        expected = {'deuteranopia', 'protanopia', 'tritanopia',
                    'achromatopsia', 'deuteranomaly', 'protanomaly', 'tritanomaly'}
        assert set(CVD_VARIANTS) == expected


class TestColorspacious:
    def test_cspace_convert_returns_jch(self):
        # JCh is perceptual color space; cspace_convert returns a named tuple
        rgb = [[100, 150, 200]]
        result = cspace_convert(rgb, "sRGB1", "JChQMsH")
        # JChQMsH → 7 components: J, C, h, Q, M, s, H
        assert result.shape[1] == 7


class TestGradioApps:
    def test_theme_setup_exists(self):
        import app as app_module
        # Gradio 5/6 compat via _is_gradio6 flag
        assert hasattr(app_module, '_is_gradio6')
        # Theme and CSS are built at module load
        assert hasattr(app_module, '_launch_theme')
        assert hasattr(app_module, '_launch_css')

    def test_app_has_cvd_gallery(self):
        import app as app_module
        assert callable(app_module.generate_cvd_grid)

    def test_deficiency_config_has_8_types(self):
        import app as app_module
        assert len(app_module.deficiency_config) == 8


class TestCVDVariants:
    def test_all_cvd_type_names_unique(self):
        import app as app_module
        img = Image.new('RGB', (50, 50), (100, 100, 100))
        gallery = app_module.generate_cvd_grid(img)
        names = [label for _, label in gallery]
        assert len(names) == len(set(names)), "CVD type labels must be unique"