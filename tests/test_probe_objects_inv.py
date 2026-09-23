"""
test_probe_objects_inv.py — Unit tests for probe_objects_inv.py

All network calls are mocked. Tests exercise:
  - Correct Sphinx v2 header parsing
  - Zlib decompression
  - Symbol found / not found
  - Partial match / similar suggestions
  - HTTP errors
  - Malformed payloads
  - fetch_and_parse pipeline
  - search_symbol domain + role filtering
"""

import json
import zlib
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
import probe_objects_inv as poi


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_valid_inv_bytes(symbols: list[str] | None = None) -> bytes:
    """
    Build a well-formed Sphinx v2 objects.inv binary payload.

    Header: 4 lines (correct format).
    Body:   zlib-compressed symbol lines.
    """
    if symbols is None:
        symbols = [
            "AsyncSession.begin_nested py:method 1 orm/asyncio.html#$ -",
            "AsyncSession py:class 1 orm/asyncio.html#$ -",
            "BaseModel py:class 1 usage/models.html#$ -",
            "BaseModel.model_validate py:method 1 usage/models.html#$ -",
        ]

    header = (
        b"# Sphinx inventory version 2\n"
        b"# Project: TestProject\n"
        b"# Version: 1.0\n"
        b"# The remainder of this file is compressed using zlib.\n"
    )
    body = "\n".join(symbols) + "\n"
    return header + zlib.compress(body.encode("utf-8"))


def _mock_urlopen(data: bytes):
    """Return a context-manager-compatible mock for urllib.request.urlopen."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = data
    return mock_resp


# ---------------------------------------------------------------------------
# _parse_objects_inv_stdlib
# ---------------------------------------------------------------------------

class TestParseObjectsInvStdlib:

    def test_valid_v2_returns_nested_dict(self):
        inv = poi._parse_objects_inv_stdlib(_make_valid_inv_bytes())
        assert inv is not None
        assert isinstance(inv, dict)

    def test_known_symbol_present_after_parse(self):
        inv = poi._parse_objects_inv_stdlib(_make_valid_inv_bytes())
        assert inv is not None
        assert "py" in inv
        assert "method" in inv["py"]
        assert "AsyncSession.begin_nested" in inv["py"]["method"]

    def test_class_symbol_parsed_correctly(self):
        inv = poi._parse_objects_inv_stdlib(_make_valid_inv_bytes())
        assert inv is not None
        assert "AsyncSession" in inv.get("py", {}).get("class", {})

    def test_dollar_sign_replaced_with_symbol_name_in_url(self):
        inv = poi._parse_objects_inv_stdlib(_make_valid_inv_bytes())
        assert inv is not None
        url = inv["py"]["method"]["AsyncSession.begin_nested"]["url"]
        assert "$" not in url
        assert "AsyncSession.begin_nested" in url

    def test_domain_type_preserved(self):
        inv = poi._parse_objects_inv_stdlib(_make_valid_inv_bytes())
        assert inv is not None
        assert inv["py"]["method"]["AsyncSession.begin_nested"]["domain_type"] == "py:method"

    def test_wrong_header_returns_none(self):
        bad_data = b"# Not a Sphinx file\nstuff\n"
        result = poi._parse_objects_inv_stdlib(bad_data)
        assert result is None

    def test_too_short_returns_none(self):
        result = poi._parse_objects_inv_stdlib(b"# Sphinx inventory version 2\n")
        assert result is None

    def test_bad_zlib_returns_none(self):
        header = (
            b"# Sphinx inventory version 2\n"
            b"# Project: Test\n"
            b"# Version: 1.0\n"
            b"# The remainder of this file is compressed using zlib.\n"
        )
        result = poi._parse_objects_inv_stdlib(header + b"not_valid_zlib_data")
        assert result is None

    def test_empty_symbols_returns_empty_inv(self):
        inv = poi._parse_objects_inv_stdlib(_make_valid_inv_bytes(symbols=[]))
        assert inv is not None
        assert inv == {}

    def test_multiple_domains_parsed(self):
        symbols = [
            "some_function py:function 1 api.html#$ -",
            "SomeStruct c:type 1 api.html#$ -",
        ]
        inv = poi._parse_objects_inv_stdlib(_make_valid_inv_bytes(symbols=symbols))
        assert inv is not None
        assert "py" in inv
        assert "c" in inv


# ---------------------------------------------------------------------------
# fetch_and_parse (mocked network)
# ---------------------------------------------------------------------------

class TestFetchAndParse:

    def test_successful_fetch_and_parse(self):
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(_make_valid_inv_bytes())):
            inv = poi.fetch_and_parse("https://example.com/objects.inv")
        assert inv is not None
        assert "py" in inv

    def test_http_error_returns_none(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            url="https://example.com", code=404, msg="Not Found", hdrs=None, fp=None
        )):
            inv = poi.fetch_and_parse("https://example.com/objects.inv")
        assert inv is None

    def test_url_error_returns_none(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
            inv = poi.fetch_and_parse("https://example.com/objects.inv")
        assert inv is None

    def test_malformed_payload_returns_none(self):
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(b"garbage data no header")):
            inv = poi.fetch_and_parse("https://example.com/objects.inv")
        assert inv is None


# ---------------------------------------------------------------------------
# search_symbol
# ---------------------------------------------------------------------------

class TestSearchSymbol:

    def _inv(self):
        return poi._parse_objects_inv_stdlib(_make_valid_inv_bytes())

    def test_exact_match_returns_verified(self):
        result = poi.search_symbol(self._inv(), "AsyncSession.begin_nested")
        assert result["exists"] is True
        assert result["verdict"] == "VERIFIED"

    def test_exact_match_contains_url(self):
        result = poi.search_symbol(self._inv(), "AsyncSession.begin_nested")
        assert "url" in result
        assert result["url"]  # non-empty

    def test_exact_match_contains_domain_type(self):
        result = poi.search_symbol(self._inv(), "AsyncSession.begin_nested")
        assert result["domain_type"] == "py:method"

    def test_missing_symbol_returns_unsupported(self):
        result = poi.search_symbol(self._inv(), "NonExistent.method_xyz")
        assert result["exists"] is False
        assert result["verdict"] == "UNSUPPORTED"

    def test_missing_symbol_returns_similar_on_partial_match(self):
        # search_symbol does `if symbol.lower() in name.lower()` — the query must be
        # a substring of the candidate name.  "begin_nested" IS a substring of
        # "AsyncSession.begin_nested", so it should appear in the similar list.
        result = poi.search_symbol(self._inv(), "begin_nested")
        assert result["exists"] is False
        assert any("begin_nested" in s for s in result.get("similar", []))

    def test_domain_filter_restricts_search(self):
        # "AsyncSession.begin_nested" is in domain "py"
        result_with_py = poi.search_symbol(self._inv(), "AsyncSession.begin_nested", domain="py")
        result_with_c = poi.search_symbol(self._inv(), "AsyncSession.begin_nested", domain="c")
        assert result_with_py["exists"] is True
        assert result_with_c["exists"] is False

    def test_role_filter_restricts_search(self):
        result_method = poi.search_symbol(self._inv(), "AsyncSession.begin_nested", domain="py", role="method")
        result_class = poi.search_symbol(self._inv(), "AsyncSession.begin_nested", domain="py", role="class")
        assert result_method["exists"] is True
        assert result_class["exists"] is False

    def test_empty_inventory_returns_unsupported(self):
        result = poi.search_symbol({}, "AnySymbol")
        assert result["exists"] is False
        assert result["verdict"] == "UNSUPPORTED"

    def test_similar_list_capped_at_10(self):
        # Build an inventory with many similar symbols
        symbols = [f"Base.method_{i} py:method 1 api.html#$ -" for i in range(20)]
        inv = poi._parse_objects_inv_stdlib(_make_valid_inv_bytes(symbols=symbols))
        result = poi.search_symbol(inv, "Base.nonexistent")
        assert len(result.get("similar", [])) <= 10
