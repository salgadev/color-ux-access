"""
Tests for backend_api.py — pure Python wrappers for CVD gallery + VLM pipeline.
No Gradio components, no network calls (VLM mocked).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import patch

# ── Fixtures ─────────────────────────────────────────────────────────────────

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "button_panel_accessible.png"


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestApiGenerateGalleryFromBytes:
    """api_generate_gallery_from_bytes should produce 8 (bytes, label) items."""

    def test_generate_gallery_from_bytes_returns_8_items(self):
        """Gallery should produce one image per CVD type (8 total)."""
        from backend_api import api_generate_gallery_from_bytes

        image_bytes = FIXTURE_PATH.read_bytes()
        result = api_generate_gallery_from_bytes(image_bytes)

        assert isinstance(result, list), f"Expected list, got {type(result)}"
        assert len(result) == 8, f"Expected 8 CVD variants, got {len(result)}"

    def test_generate_gallery_from_bytes_each_item_has_label(self):
        """Each item must be (bytes, str) with non-empty label."""
        from backend_api import api_generate_gallery_from_bytes

        image_bytes = FIXTURE_PATH.read_bytes()
        result = api_generate_gallery_from_bytes(image_bytes)

        for i, item in enumerate(result):
            assert isinstance(item, tuple), f"Item {i} is not a tuple: {type(item)}"
            assert len(item) == 2, f"Item {i} should be (image_bytes, label), got {len(item)} elements"
            img_bytes, label = item
            assert isinstance(img_bytes, bytes), f"Item {i} image_bytes not bytes: {type(img_bytes)}"
            assert isinstance(label, str), f"Item {i} label not str: {type(label)}"
            assert len(label) > 0, f"Item {i} label is empty"

    def test_generate_gallery_from_bytes_produces_consistent_size(self):
        """All 8 simulated images should share the same dimensions."""
        from backend_api import api_generate_gallery_from_bytes
        from PIL import Image
        import io

        image_bytes = FIXTURE_PATH.read_bytes()
        result = api_generate_gallery_from_bytes(image_bytes)

        sizes = set()
        for img_bytes, _label in result:
            img = Image.open(io.BytesIO(img_bytes))
            sizes.add(img.size)

        assert len(sizes) == 1, f"Expected all images same size, got {len(sizes)} distinct sizes: {sizes}"

    def test_generate_gallery_from_bytes_produces_4_3_aspect_ratio(self):
        """All images should have approximately 4:3 aspect ratio (within 5% tolerance)."""
        from backend_api import api_generate_gallery_from_bytes
        from PIL import Image
        import io

        image_bytes = FIXTURE_PATH.read_bytes()
        result = api_generate_gallery_from_bytes(image_bytes)

        for i, (img_bytes, label) in enumerate(result):
            img = Image.open(io.BytesIO(img_bytes))
            w, h = img.size
            ratio = w / h
            expected = 4 / 3
            assert abs(ratio - expected) / expected < 0.05, \
                f"Item {i} ({label}): aspect ratio {ratio:.3f} != 4:3 ({expected:.3f})"


class TestApiAnalyzeCvdGridFromBytes:
    """api_analyze_cvd_grid_from_bytes should reconstruct images and run VLM analysis."""

    @patch("backend_api._analyze_all_perspectives")
    def test_analyze_cvd_grid_from_bytes_handles_empty_findings(self, mock_analyze):
        """Merged result should have 'findings', 'summary', and 'passes' keys."""
        from backend_api import api_generate_gallery_from_bytes, api_analyze_cvd_grid_from_bytes

        mock_analyze.return_value = {
            "findings": [],
            "summary": "Test passed — no issues.",
            "passes": True,
        }

        image_bytes = FIXTURE_PATH.read_bytes()
        gallery = api_generate_gallery_from_bytes(image_bytes)

        result = api_analyze_cvd_grid_from_bytes(gallery)

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "findings" in result, f"Missing 'findings' key in result"
        assert "summary" in result, f"Missing 'summary' key in result"
        assert "passes" in result, f"Missing 'passes' key in result"
        assert result["passes"] is True

    @patch("backend_api._analyze_all_perspectives")
    def test_analyze_cvd_grid_from_bytes_with_finding(self, mock_analyze):
        """Result with a finding should preserve the finding description."""
        from backend_api import api_generate_gallery_from_bytes, api_analyze_cvd_grid_from_bytes

        mock_analyze.return_value = {
            "findings": [
                {
                    "type": "Low Contrast",
                    "wcag_criterion": "1.4.3",
                    "description": "Submit button has insufficient contrast ratio.",
                    "severity": "serious",
                    "location": "Bottom-right",
                }
            ],
            "summary": "1 issue found.",
            "passes": False,
        }

        image_bytes = FIXTURE_PATH.read_bytes()
        gallery = api_generate_gallery_from_bytes(image_bytes)

        result = api_analyze_cvd_grid_from_bytes(gallery)

        assert result["passes"] is False
        assert len(result["findings"]) == 1
        assert "Submit button" in result["findings"][0]["description"]

    @patch("backend_api._analyze_all_perspectives")
    def test_analyze_cvd_grid_from_bytes_deduplicates_findings(self, mock_analyze):
        """Same finding from multiple CVD perspectives should appear only once."""
        from backend_api import api_generate_gallery_from_bytes, api_analyze_cvd_grid_from_bytes

        mock_analyze.return_value = {
            "findings": [
                {
                    "type": "Color Only Information",
                    "wcag_criterion": "1.4.1",
                    "description": "Green validation icon conveys status without text.",
                    "severity": "critical",
                    "location": "Top-left",
                }
            ],
            "summary": "Issue found.",
            "passes": False,
        }

        image_bytes = FIXTURE_PATH.read_bytes()
        gallery = api_generate_gallery_from_bytes(image_bytes)

        result = api_analyze_cvd_grid_from_bytes(gallery)

        # Should be deduplicated to 1 finding
        assert len(result["findings"]) == 1


class TestApiReportFromJson:
    """api_report_from_json should return markdown containing WCAG report content."""

    def test_api_report_from_json_includes_overall_status(self):
        """Markdown should include 'Overall:' and the finding description."""
        from backend_api import api_report_from_json

        vlm_result = {
            "findings": [
                {
                    "type": "Low Contrast",
                    "wcag_criterion": "1.4.3",
                    "description": "Submit button contrast ratio is 2.1:1, below 4.5:1 minimum.",
                    "severity": "serious",
                    "location": "Bottom-right",
                }
            ],
            "summary": "1 serious issue detected.",
            "passes": False,
        }

        markdown = api_report_from_json(vlm_result)

        assert isinstance(markdown, str), f"Expected str, got {type(markdown)}"
        assert "Overall:" in markdown, "Markdown should contain 'Overall:'"
        assert "Fail" in markdown, "Markdown should indicate overall failure"
        assert "Submit button" in markdown, "Markdown should contain the finding description"

    def test_api_report_from_json_passes_true(self):
        """No findings with passes=True should produce a clean pass message."""
        from backend_api import api_report_from_json

        vlm_result = {
            "findings": [],
            "summary": "No issues detected.",
            "passes": True,
        }

        markdown = api_report_from_json(vlm_result)

        assert "Pass" in markdown or "pass" in markdown.lower()

    def test_api_report_from_json_error_handling(self):
        """Error response should be reflected in the markdown."""
        from backend_api import api_report_from_json

        vlm_result = {
            "error": "MiniCPM endpoint timed out (cold-start may need ~90s). Try again.",
            "findings": [],
            "passes": False,
        }

        markdown = api_report_from_json(vlm_result)

        assert "Warning" in markdown or "error" in markdown.lower()