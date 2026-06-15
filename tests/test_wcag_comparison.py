"""
Tests for CVD perception comparison summary — the heuristic comparison table
comparing original vs all CVD perspectives with perception_summary and pass/fail.
Replaces the old format_wcag_comparison tests (function was dead code).
"""
import sys
import pathlib

_project_root = pathlib.Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest
from app import _format_cvd_perception_comparison_summary


class TestPerceptionComparisonSummary:
    """Tests for the CVD perception comparison summary table."""

    def test_function_exists(self):
        """The comparison function should exist and be callable."""
        assert callable(_format_cvd_perception_comparison_summary)

    def test_original_and_cvd_perspectives_shown(self):
        """Table should include original design column and each CVD perspective."""
        original_vlm = {
            "perception_summary": "Clear and readable with normal vision.",
            "passes": True,
        }
        cvd_results = {
            "Protanopia (red-blind)": {
                "perception_summary": "Red elements are hard to distinguish.",
                "passes": False,
            },
            "Deuteranopia (green-blind)": {
                "perception_summary": "Green elements blend into background.",
                "passes": False,
            },
        }

        output = _format_cvd_perception_comparison_summary(
            original_vlm=original_vlm,
            cvd_results=cvd_results,
        )

        assert "Original design" in output
        assert "Protanopia (red-blind)" in output
        assert "Deuteranopia (green-blind)" in output

    def test_perception_summary_and_pass_status_in_table(self):
        """Each row shows perception_summary text and pass/fail indicator."""
        original_vlm = {
            "perception_summary": "Everything looks fine.",
            "passes": True,
        }
        cvd_results = {
            "Protanopia (red-blind)": {
                "perception_summary": "Red buttons are invisible.",
                "passes": False,
            },
        }

        output = _format_cvd_perception_comparison_summary(
            original_vlm=original_vlm,
            cvd_results=cvd_results,
        )

        assert "Everything looks fine." in output
        assert "Red buttons are invisible." in output
        assert "✅" in output
        assert "❌" in output

    def test_heuristic_disclaimer_present(self):
        """The output should contain a disclaimer that this is not a full WCAG audit."""
        output = _format_cvd_perception_comparison_summary(
            original_vlm={"perception_summary": "OK.", "passes": True},
            cvd_results={"Test": {"perception_summary": "Bad.", "passes": False}},
        )

        assert "heuristic" in output.lower()
        assert "not a substitute" in output.lower()
        assert "WCAG" in output or "audit" in output.lower()

    def test_all_pass_shows_heuristic_pass(self):
        """When all perspectives pass, overall should say heuristic pass."""
        original_vlm = {"perception_summary": "OK.", "passes": True}
        cvd_results = {
            "Protanopia": {"perception_summary": "OK too.", "passes": True},
            "Deuteranopia": {"perception_summary": "Also OK.", "passes": True},
        }

        output = _format_cvd_perception_comparison_summary(
            original_vlm=original_vlm,
            cvd_results=cvd_results,
        )

        assert "Heuristic pass" in output

    def test_any_fail_shows_heuristic_fail(self):
        """When any perspective fails, overall should say heuristic fail."""
        original_vlm = {"perception_summary": "OK.", "passes": True}
        cvd_results = {
            "Protanopia": {"perception_summary": "Bad.", "passes": False},
        }

        output = _format_cvd_perception_comparison_summary(
            original_vlm=original_vlm,
            cvd_results=cvd_results,
        )

        assert "Heuristic fail" in output

    def test_empty_perception_summary_uses_dash(self):
        """Missing or empty perception_summary should display an em dash."""
        original_vlm = {"perception_summary": "", "passes": True}
        cvd_results = {
            "Test": {"perception_summary": None, "passes": False},
        }

        output = _format_cvd_perception_comparison_summary(
            original_vlm=original_vlm,
            cvd_results=cvd_results,
        )

        assert "—" in output

    def test_no_original_vlm_skips_original_row(self):
        """When original_vlm is None, no 'Original design' row should appear."""
        cvd_results = {
            "Protanopia": {"perception_summary": "Bad.", "passes": False},
        }

        output = _format_cvd_perception_comparison_summary(
            original_vlm=None,
            cvd_results=cvd_results,
        )

        assert "Original design" not in output
        assert "Protanopia" in output

    def test_markdown_table_structure(self):
        """Output should have markdown table headers and separator."""
        output = _format_cvd_perception_comparison_summary(
            original_vlm={"perception_summary": "OK.", "passes": True},
            cvd_results={"Test": {"perception_summary": "Bad.", "passes": False}},
        )

        assert "| Perspective |" in output
        assert "VLM perception |" in output
        assert "Pass |" in output
        assert "|-------------|" in output


class TestMergeCvdResults:
    """Tests for the VLM result merging and deduplication logic."""

    def test_merge_preserves_all_findings(self):
        """All findings from each CVD perspective should appear in merged output."""
        from app import _merge_cvd_results

        results = {
            "Protanopia": {
                "passes": False,
                "findings": [{
                    "type": "Low Contrast",
                    "wcag_criterion": "1.4.3",
                    "severity": "serious",
                    "description": "Button contrast too low",
                    "location": "Submit button",
                }],
                "summary": "1 issue",
            },
            "Deuteranopia": {
                "passes": False,
                "findings": [{
                    "type": "Color Only Information",
                    "wcag_criterion": "1.4.1",
                    "severity": "critical",
                    "description": "Green/red status indicators",
                    "location": "Status panel",
                }],
                "summary": "1 issue",
            },
        }

        merged = _merge_cvd_results(results)
        assert len(merged["findings"]) == 2
        assert "Button contrast too low" in [f["description"] for f in merged["findings"]]
        assert "Green/red status indicators" in [f["description"] for f in merged["findings"]]

    def test_merge_deduplicates_same_finding(self):
        """Duplicated findings across CVD perspectives should only appear once."""
        from app import _merge_cvd_results

        results = {
            "Protanopia": {
                "passes": False,
                "findings": [{
                    "type": "Low Contrast",
                    "wcag_criterion": "1.4.3",
                    "severity": "serious",
                    "description": "Button contrast ratio is 2.8:1",
                    "location": "Submit button",
                }],
                "summary": "1 issue",
            },
            "Deuteranopia": {
                "passes": False,
                "findings": [{
                    "type": "Low Contrast",
                    "wcag_criterion": "1.4.3",
                    "severity": "serious",
                    "description": "Button contrast ratio is 2.8:1",
                    "location": "Submit button",
                }],
                "summary": "1 issue",
            },
        }

        merged = _merge_cvd_results(results)
        # Same description (first 80 chars) should be deduplicated
        assert len(merged["findings"]) == 1

    def test_merge_overall_pass_only_when_all_pass(self):
        """Merged passes should only be True when all perspectives pass."""
        from app import _merge_cvd_results

        # All pass
        all_pass = _merge_cvd_results({
            "A": {"passes": True, "findings": [], "summary": ""},
            "B": {"passes": True, "findings": [], "summary": ""},
        })
        assert all_pass["passes"] is True

        # One fails
        one_fail = _merge_cvd_results({
            "A": {"passes": True, "findings": [], "summary": ""},
            "B": {"passes": False, "findings": [{"type": "Bad", "wcag_criterion": "1.4.1",
                                                  "description": "x", "severity": "critical", "location": "x"}], "summary": ""},
        })
        assert one_fail["passes"] is False

    def test_merge_handles_error_results(self):
        """CVD results with errors should be skipped, not crash."""
        from app import _merge_cvd_results

        merged = _merge_cvd_results({
            "Protanopia": {"error": "VLM timeout", "findings": [], "passes": False},
            "Deuteranopia": {"passes": True, "findings": [], "summary": "OK"},
        })
        assert merged["passes"] is True
        assert len(merged["findings"]) == 0
        assert "VLM timeout" in merged.get("summary", "")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
