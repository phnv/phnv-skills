"""
test_fetch_doc.py — Unit tests for fetch_doc.py

Network calls (urllib.request.urlopen) are mocked throughout.
Filesystem writes use pytest's tmp_path fixture.
"""

import json
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

import fetch_doc as fd


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------

class TestSanitizeFilename:

    def test_strips_http_prefix(self):
        result = fd.sanitize_filename("http://docs.example.com/page")
        assert not result.startswith("http")

    def test_strips_https_prefix(self):
        result = fd.sanitize_filename("https://docs.example.com/page")
        assert not result.startswith("https")

    def test_replaces_slashes_with_underscore(self):
        result = fd.sanitize_filename("https://docs.example.com/a/b/c")
        assert "/" not in result

    def test_truncates_to_100_chars(self):
        long_url = "https://example.com/" + "a" * 200
        result = fd.sanitize_filename(long_url)
        assert len(result) <= 100


# ---------------------------------------------------------------------------
# build_cache_path
# ---------------------------------------------------------------------------

class TestBuildCachePath:

    def test_includes_claim_id_in_filename(self, tmp_path):
        path = fd.build_cache_path("C-007", "https://docs.example.com/page", "2.0", str(tmp_path))
        assert "C-007" in path.name

    def test_includes_version_slug_in_filename(self, tmp_path):
        path = fd.build_cache_path("C-001", "https://docs.example.com/page", "2.0.36", str(tmp_path))
        assert "2_0_36" in path.name

    def test_returns_path_object(self, tmp_path):
        result = fd.build_cache_path("C-001", "https://example.com", "", str(tmp_path))
        assert isinstance(result, Path)

    def test_cache_dir_is_parent(self, tmp_path):
        result = fd.build_cache_path("C-001", "https://example.com", "1.0", str(tmp_path))
        assert result.parent == tmp_path


# ---------------------------------------------------------------------------
# write_cache / read_cache roundtrip
# ---------------------------------------------------------------------------

class TestCacheRoundtrip:

    def test_write_then_read_returns_metadata(self, tmp_path):
        cache_path = tmp_path / "C-001_test.txt"
        fd.write_cache(cache_path, "https://example.com", "Hello world", 200, "text/plain", "C-001")
        result = fd.read_cache(cache_path)
        assert result is not None
        assert result["metadata"]["source_url"] == "https://example.com"
        assert result["metadata"]["http_status"] == "200"

    def test_write_then_read_returns_content(self, tmp_path):
        cache_path = tmp_path / "C-001_test.txt"
        fd.write_cache(cache_path, "https://example.com", "My doc content", 200, "text/plain")
        result = fd.read_cache(cache_path)
        assert "My doc content" in result["content"]

    def test_read_missing_file_returns_none(self, tmp_path):
        result = fd.read_cache(tmp_path / "nonexistent.txt")
        assert result is None

    def test_write_creates_parent_directories(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "cache.txt"
        fd.write_cache(nested, "https://example.com", "content", 200, "text/plain")
        assert nested.exists()


# ---------------------------------------------------------------------------
# normalize_html_to_text
# ---------------------------------------------------------------------------

class TestNormalizeHtmlToText:

    def test_strips_html_tags(self):
        html = "<h1>Title</h1><p>Paragraph</p>"
        result = fd.normalize_html_to_text(html)
        assert "<h1>" not in result
        assert "Title" in result
        assert "Paragraph" in result

    def test_strips_script_tags(self):
        html = "<script>alert('xss')</script><p>Content</p>"
        result = fd.normalize_html_to_text(html)
        assert "alert" not in result
        assert "Content" in result

    def test_strips_style_tags(self):
        html = "<style>.cls { color: red }</style><p>Content</p>"
        result = fd.normalize_html_to_text(html)
        assert ".cls" not in result
        assert "Content" in result

    def test_decodes_html_entities(self):
        html = "<p>A &amp; B &lt; C &gt; D</p>"
        result = fd.normalize_html_to_text(html)
        assert "&amp;" not in result
        assert "&" in result


# ---------------------------------------------------------------------------
# extract_relevant_passage
# ---------------------------------------------------------------------------

class TestExtractRelevantPassage:

    def test_returns_lines_containing_keyword(self):
        content = "Line 1\nLine with AsyncSession here\nLine 3"
        result = fd.extract_relevant_passage(content, ["AsyncSession"])
        assert "AsyncSession" in result

    def test_returns_context_lines_around_match(self):
        lines = [f"Line {i}" for i in range(20)]
        content = "\n".join(lines)
        # keyword is on line 10
        lines[10] = "KEYWORD is here"
        content = "\n".join(lines)
        result = fd.extract_relevant_passage(content, ["KEYWORD"], context_lines=2)
        # Lines 8–12 should appear
        assert "Line 8" in result
        assert "Line 12" in result

    def test_no_match_returns_first_50_lines(self):
        lines = [f"Line {i}" for i in range(100)]
        content = "\n".join(lines)
        result = fd.extract_relevant_passage(content, ["NOMATCH"])
        # Should return first 50 lines
        assert "Line 49" in result
        assert "Line 50" not in result

    def test_multiple_keywords_union_of_matches(self):
        content = "Alpha here\nBeta there\nGamma nowhere"
        result = fd.extract_relevant_passage(content, ["Alpha", "Beta"])
        assert "Alpha" in result
        assert "Beta" in result


# ---------------------------------------------------------------------------
# fetch_document (mocked network)
# ---------------------------------------------------------------------------

class TestFetchDocument:

    def _make_mock_response(self, content: str, status: int = 200, content_type: str = "text/html"):
        mock = MagicMock()
        mock.status = status
        mock.headers.get.return_value = content_type
        mock.read.return_value = content.encode("utf-8")
        mock.__enter__ = lambda s: s
        mock.__exit__ = MagicMock(return_value=False)
        return mock

    def test_successful_fetch_returns_tuple(self):
        mock_resp = self._make_mock_response("<html><body>Hello</body></html>")
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fd.fetch_document("https://example.com")
        assert result is not None
        content, status, ctype = result
        assert status == 200
        assert "text/html" in ctype

    def test_http_error_returns_none(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            url="https://example.com", code=404, msg="Not Found", hdrs=None, fp=None
        )):
            result = fd.fetch_document("https://example.com")
        assert result is None

    def test_url_error_returns_none(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            result = fd.fetch_document("https://example.com")
        assert result is None
