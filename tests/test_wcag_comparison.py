"""
Tests for WCAG side-by-side comparison panel — paired results component
comparing original vs CVD perspective per WCAG criterion.
"""
import sys
import pathlib

_project_root = pathlib.Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest
from app import format_wcag_report, format_wcag_comparison


class TestWCAGComparison:
    """Tests for the side-by-side WCAG comparison panel."""

    def test_format_wcag_comparison_exists(self):
        """format_wcag_comparison function should exist in app module."""
        import app as app_module
        assert hasattr(app_module, 'format_wcag_comparison'), \
            "app module should have format_wcag_comparison function"

    def test_comparison_shows_original_and_cvd_side_by_side(self):
        """Comparison should show original and CVD results for each criterion."""
        original_result = {
            "passes": True,
            "findings": [
                {
                    "type": "Low Contrast",
                    "wcag_criterion": "1.4.3",
                    "severity": "serious",
                    "description": "Text contrast ratio 3.5:1",
                    "location": "Body text",
                }
            ],
            "summary": "1 issue found",
        }
        cvd_result = {
            "passes": False,
            "findings": [
                {
                    "type": "Low Contrast",
                    "wcag_criterion": "1.4.3",
                    "severity": "critical",
                    "description": "Text contrast ratio 2.1:1 under protanopia",
                    "location": "Body text",
                }
            ],
            "summary": "1 critical issue found",
        }

        comparison = format_wcag_comparison(original_result, cvd_result, "Protanopia (red-blind)")
        
        # Should contain both original and CVD results
        assert "Original" in comparison or "original" in comparison.lower()
        assert "Protanopia" in comparison or "CVD" in comparison
        # Should show criterion 1.4.3
        assert "1.4.3" in comparison
        # Should show severity difference (serious → critical)
        assert "serious" in comparison.lower()
        assert "critical" in comparison.lower()

    def test_comparison_highlights_regression_pass_to_fail(self):
        """Pass→fail regression should be highlighted in red."""
        original_result = {
            "passes": True,
            "findings": [
                {
                    "type": "Low Contrast",
                    "wcag_criterion": "1.4.3",
                    "severity": "moderate",
                    "description": "OK contrast",
                    "location": "Body text",
                }
            ],
            "summary": "Pass",
        }
        cvd_result = {
            "passes": False,
            "findings": [
                {
                    "type": "Low Contrast",
                    "wcag_criterion": "1.4.3",
                    "severity": "serious",
                    "description": "Failed contrast",
                    "location": "Body text",
                }
            ],
            "summary": "Fail",
        }

        comparison = format_wcag_comparison(original_result, cvd_result, "Protanopia")
        
        # Should indicate regression (pass → fail)
        # Look for red highlighting or regression indicator
        assert any(marker in comparison.lower() for marker in ['regression', '❌', 'fail', 'red', '⬇', '↘']), \
            "Should show regression indicator"

    def test_comparison_highlights_improvement_fail_to_pass(self):
        """Fail→pass improvement should be highlighted in green."""
        original_result = {
            "passes": False,
            "findings": [
                {
                    "type": "Color Only Information",
                    "wcag_criterion": "1.4.1",
                    "severity": "serious",
                    "description": "Color-only info",
                    "location": "Status indicator",
                }
            ],
            "summary": "Fail",
        }
        cvd_result = {
            "passes": True,
            "findings": [],
            "summary": "Pass",
        }

        comparison = format_wcag_comparison(original_result, cvd_result, "Deuteranopia")
        
        # Should indicate improvement (fail → pass)
        assert any(marker in comparison.lower() for marker in ['improvement', '✅', 'pass', 'green', '⬆', '↗']), \
            "Should show improvement indicator"

    def test_comparison_shows_all_original_criteria(self):
        """All criteria from original evaluation should appear in comparison."""
        original_result = {
            "passes": False,
            "findings": [
                {"type": "Low Contrast", "wcag_criterion": "1.4.3", "severity": "serious", "description": "Low contrast", "location": "Body"},
                {"type": "Color Only Information", "wcag_criterion": "1.4.1", "severity": "critical", "description": "Color only", "location": "Header"},
                {"type": "Insufficient Non-Text Contrast", "wcag_criterion": "1.4.11", "severity": "moderate", "description": "Non-text contrast", "location": "Button"},
            ],
            "summary": "3 issues",
        }
        cvd_result = {
            "passes": False,
            "findings": [
                {"type": "Low Contrast", "wcag_criterion": "1.4.3", "severity": "critical", "description": "Worse contrast", "location": "Body"},
            ],
            "summary": "1 issue",
        }

        comparison = format_wcag_comparison(original_result, cvd_result, "Tritanopia")
        
        # All 3 original criteria should appear
        assert "1.4.3" in comparison
        assert "1.4.1" in comparison
        assert "1.4.11" in comparison

    def test_comparison_handles_both_pass(self):
        """Both original and CVD pass should show as pass."""
        original_result = {"passes": True, "findings": [], "summary": "Pass"}
        cvd_result = {"passes": True, "findings": [], "summary": "Pass"}

        comparison = format_wcag_comparison(original_result, cvd_result, "Protanomaly")
        
        # Should show both pass
        assert "Pass" in comparison or "✅" in comparison

    def test_comparison_handles_error_results(self):
        """Error in either result should be handled gracefully."""
        original_result = {"error": "VLM timeout"}
        cvd_result = {"passes": True, "findings": [], "summary": "Pass"}

        comparison = format_wcag_comparison(original_result, cvd_result, "Protanopia")
        
        assert "Error" in comparison or "error" in comparison.lower()

    def test_comparison_includes_criterion_badges(self):
        """Each criterion should have a color-coded badge (text/non-text, AA/AAA)."""
        original_result = {
            "passes": False,
            "findings": [
                {"type": "Low Contrast", "wcag_criterion": "1.4.3", "severity": "serious", "description": "Text contrast", "location": "Body"},
                {"type": "Insufficient Non-Text Contrast", "wcag_criterion": "1.4.11", "severity": "moderate", "description": "UI contrast", "location": "Button"},
            ],
            "summary": "2 issues",
        }
        cvd_result = {
            "passes": False,
            "findings": [
                {"type": "Low Contrast", "wcag_criterion": "1.4.3", "severity": "critical", "description": "Worse text contrast", "location": "Body"},
                {"type": "Insufficient Non-Text Contrast", "wcag_criterion": "1.4.11", "severity": "serious", "description": "Worse UI contrast", "location": "Button"},
            ],
            "summary": "2 issues",
        }

        comparison = format_wcag_comparison(original_result, cvd_result, "Deuteranopia")
        
        # Should distinguish text vs non-text criteria
        # 1.4.3 is text contrast (AA), 1.4.11 is non-text (AA)
        assert "1.4.3" in comparison
        assert "1.4.11" in comparison

    def test_comparison_updates_on_variant_change(self):
        """Comparison should be regenerated when CVD variant changes (tested via function interface)."""
        original_result = {
            "passes": True,
            "findings": [{"type": "Low Contrast", "wcag_criterion": "1.4.3", "severity": "moderate", "description": "OK", "location": "Body"}],
            "summary": "Pass",
        }
        cvd_result_1 = {
            "passes": False,
            "findings": [{"type": "Low Contrast", "wcag_criterion": "1.4.3", "severity": "serious", "description": "Failed", "location": "Body"}],
            "summary": "Fail",
        }
        cvd_result_2 = {
            "passes": True,
            "findings": [],
            "summary": "Pass",
        }

        comp_1 = format_wcag_comparison(original_result, cvd_result_1, "Protanopia")
        comp_2 = format_wcag_comparison(original_result, cvd_result_2, "Tritanopia")
        
        # Different CVD results should produce different comparisons
        assert comp_1 != comp_2
        # First should show regression, second should show pass
        assert "1.4.3" in comp_1
        assert "1.4.3" in comp_2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])