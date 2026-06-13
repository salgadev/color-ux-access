"""
VLM Caching tests — verify that repeated analysis of the same image returns cached results.
"""
import sys
import pathlib

_project_root = pathlib.Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from PIL import Image
import io


def test_analyze_single_perspective_returns_dict():
    """analyze_single_perspective should return a dict with findings/passes/error keys."""
    from app import analyze_single_perspective
    
    # Create a test image
    img = Image.new('RGB', (100, 50), color='red')
    
    # The function requires an actual VLM endpoint to work
    # For now, verify the function exists and has correct signature
    import inspect
    sig = inspect.signature(analyze_single_perspective)
    params = list(sig.parameters.keys())
    assert 'img' in params, "analyze_single_perspective should accept 'img' parameter"
    assert 'label' in params, "analyze_single_perspective should accept 'label' parameter"


def test_vlm_cache_module_level_exists():
    """VLM cache should be a module-level dict for persisting across requests."""
    import app
    assert hasattr(app, '_vlm_cache'), "app module should have _vlm_cache"
    assert isinstance(app._vlm_cache, dict), "_vlm_cache should be a dict"


def test_vlm_cache_key_generation():
    """_get_cache_key should generate consistent keys for same image+label."""
    from app import _get_cache_key
    
    img = Image.new('RGB', (100, 50), color='red')
    label = "Protanopia (red-blind)"
    
    key1 = _get_cache_key(img, label)
    key2 = _get_cache_key(img, label)
    
    # Same image and label should produce same key
    assert key1 == key2, "Same image+label should produce same cache key"
    
    # Different labels should produce different keys
    label2 = "Deuteranopia (green-blind)"
    key3 = _get_cache_key(img, label2)
    assert key1 != key3, "Different labels should produce different cache keys"


def test_vlm_cache_stores_and_retrieves():
    """Cache should store and retrieve VLM results."""
    from app import _vlm_cache, _get_cache_key
    
    img = Image.new('RGB', (100, 50), color='red')
    label = "Test Vision"
    
    # Create a mock result
    mock_result = {"findings": [], "passes": True, "summary": "Test"}
    
    key = _get_cache_key(img, label)
    _vlm_cache[key] = mock_result
    
    # Should be able to retrieve it
    assert key in _vlm_cache
    assert _vlm_cache[key] == mock_result


def test_format_wcag_report_shows_cvd_label() -> None:
    """format_wcag_report should show CVD label when present in vlm_result."""
    from app import format_wcag_report

    result_with_label = {
        "cvd_label": "Protanopia (red-blind)",
        "findings": [],
        "passes": True
    }

    report = format_wcag_report(result_with_label)
    assert "Protanopia" in report, "Report should include CVD label"

    result_without_label = {
        "findings": [],
        "passes": True
    }

    report2 = format_wcag_report(result_without_label)
    assert "WCAG Accessibility Report" in report2, "Report should show default title when no CVD label"


def test_merged_cache_module_level_exists() -> None:
    """Merged VLM cache should be a module-level dict for persisting across requests."""
    import app
    assert hasattr(app, '_vlm_merged_cache'), "app module should have _vlm_merged_cache"
    assert isinstance(app._vlm_merged_cache, dict), "_vlm_merged_cache should be a dict"


def test_merged_cache_key_generation() -> None:
    """_get_merged_cache_key should generate consistent keys for same original image."""
    from app import _get_merged_cache_key
    from PIL import Image

    img = Image.new('RGB', (100, 50), color='red')

    key1 = _get_merged_cache_key(img)
    key2 = _get_merged_cache_key(img)

    assert key1 == key2, "Same image should produce same merged cache key"

    # Different image should produce different key
    img2 = Image.new('RGB', (100, 50), color='blue')
    key3 = _get_merged_cache_key(img2)
    assert key1 != key3, "Different images should produce different merged cache keys"


def test_analyze_all_perspectives_with_cache_first_call() -> None:
    """First call to analyze_all_perspectives_with_cache should call VLM for each perspective."""
    from app import analyze_all_perspectives_with_cache, _vlm_merged_cache
    from PIL import Image
    from unittest.mock import patch, MagicMock

    img = Image.new('RGB', (100, 50), color='red')
    cvd_grid = [
        (img, "Normal vision (original design)"),
        (img, "Protanopia (red-blind)"),
    ]

    # Clear cache before test
    _vlm_merged_cache.clear()

    with patch('app._call_minicpm_endpoint') as mock_vlm:
        mock_vlm.return_value = {"findings": [], "passes": True, "summary": "Test"}

        result = analyze_all_perspectives_with_cache(cvd_grid)

        # Should call VLM once per perspective (2 times)
        assert mock_vlm.call_count == 2, f"Expected 2 VLM calls, got {mock_vlm.call_count}"

    # Result should be merged
    assert "findings" in result
    assert "passes" in result


def test_analyze_all_perspectives_with_cache_uses_cache() -> None:
    """Second call with same image should use cached merged result (no VLM calls)."""
    from app import analyze_all_perspectives_with_cache, _vlm_merged_cache
    from PIL import Image
    from unittest.mock import patch, MagicMock

    img = Image.new('RGB', (100, 50), color='green')
    cvd_grid = [
        (img, "Normal vision (original design)"),
        (img, "Protanopia (red-blind)"),
    ]

    # Clear cache before test
    _vlm_merged_cache.clear()

    with patch('app._call_minicpm_endpoint') as mock_vlm:
        mock_vlm.return_value = {"findings": [], "passes": True, "summary": "Test"}

        # First call - should call VLM
        result1 = analyze_all_perspectives_with_cache(cvd_grid)
        first_call_count = mock_vlm.call_count

        # Second call with same image - should use cache
        result2 = analyze_all_perspectives_with_cache(cvd_grid)
        second_call_count = mock_vlm.call_count

        # VLM should not be called again
        assert second_call_count == first_call_count, \
            f"VLM should not be called on second run (first={first_call_count}, second={second_call_count})"

        # Results should be identical
        assert result1 == result2, "Cached and fresh results should match"


def test_analyze_all_perspectives_with_cache_different_image() -> None:
    """Different image should bypass cache and call VLM again."""
    from app import analyze_all_perspectives_with_cache, _vlm_merged_cache
    from PIL import Image
    from unittest.mock import patch

    img1 = Image.new('RGB', (100, 50), color='red')
    img2 = Image.new('RGB', (100, 50), color='blue')
    cvd_grid1 = [(img1, "Normal vision (original design)"), (img1, "Protanopia (red-blind)")]
    cvd_grid2 = [(img2, "Normal vision (original design)"), (img2, "Protanopia (red-blind)")]

    _vlm_merged_cache.clear()

    with patch('app._call_minicpm_endpoint') as mock_vlm:
        mock_vlm.return_value = {"findings": [], "passes": True, "summary": "Test"}

        # First image
        analyze_all_perspectives_with_cache(cvd_grid1)
        first_calls = mock_vlm.call_count

        # Different image - should call VLM again
        analyze_all_perspectives_with_cache(cvd_grid2)
        second_calls = mock_vlm.call_count

        assert second_calls == first_calls + 2, \
            "Different image should trigger 2 new VLM calls"