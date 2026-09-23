"""
test_probe_api.py — Unit tests for probe_api.py v2.0

probe_api.py now uses live import + inspect exclusively (Tier-0 ground truth).
objects.inv parsing has been removed. All tests are pure unit tests — no network.
Live introspection tests use stdlib modules guaranteed to exist.
"""

import pytest
import probe_api as pa


# ---------------------------------------------------------------------------
# probe_live_symbol (backward-compat API; uses stdlib — guaranteed to exist)
# ---------------------------------------------------------------------------

class TestProbeLiveSymbol:
    """
    Tests for the probe_live_symbol(package, version, symbol_path) interface.
    Version parameter is accepted but not used (version is managed by uv.lock).
    """

    def test_finds_existing_stdlib_symbol(self):
        """json.dumps exists in the json stdlib module."""
        result = pa.probe_live_symbol("json", "3.12", "dumps")
        assert result is not None
        assert result["exists"] is True

    def test_returns_signature_for_callable(self):
        result = pa.probe_live_symbol("json", "3.12", "dumps")
        assert result is not None
        assert "signature" in result

    def test_missing_symbol_returns_none(self):
        result = pa.probe_live_symbol("json", "3.12", "completely_nonexistent_function_xyz")
        assert result is None

    def test_nonexistent_package_returns_none(self):
        result = pa.probe_live_symbol("this_package_does_not_exist_xyz", "1.0", "whatever")
        assert result is None

    def test_finds_nested_attribute_path(self):
        """pathlib.Path.read_text — multi-segment path."""
        result = pa.probe_live_symbol("pathlib", "3.12", "Path.read_text")
        assert result is not None
        assert result["exists"] is True

    def test_finds_class_and_returns_public_methods(self):
        result = pa.probe_live_symbol("json", "3.12", "JSONEncoder")
        assert result is not None
        assert "public_methods" in result

    def test_version_parameter_is_ignored(self):
        """Version does not affect the result — both calls should be equal."""
        r1 = pa.probe_live_symbol("json", "1.0", "dumps")
        r2 = pa.probe_live_symbol("json", "99.99", "dumps")
        assert r1 is not None
        assert r2 is not None
        assert r1["exists"] == r2["exists"]

    def test_includes_type_field(self):
        result = pa.probe_live_symbol("json", "3.12", "dumps")
        assert result is not None
        assert "type" in result

    def test_includes_module_version(self):
        result = pa.probe_live_symbol("json", "3.12", "dumps")
        assert result is not None
        assert "module_version" in result


# ---------------------------------------------------------------------------
# probe_symbol (new public API; never returns None)
# ---------------------------------------------------------------------------

class TestProbeSymbol:

    def test_never_returns_none_for_missing_symbol(self):
        result = pa.probe_symbol("json", "nonexistent_function_xyz")
        assert result is not None

    def test_returns_verified_for_existing_symbol(self):
        result = pa.probe_symbol("json", "dumps")
        assert result["exists"] is True
        assert result["verdict"] == "VERIFIED"

    def test_returns_unsupported_for_missing_symbol(self):
        result = pa.probe_symbol("json", "nonexistent_function_xyz")
        assert result["exists"] is False
        assert result["verdict"] == "UNSUPPORTED"

    def test_returns_unsupported_for_bad_package(self):
        result = pa.probe_symbol("totally_fake_package_xyz", "anything")
        assert result["exists"] is False
        assert result["verdict"] == "UNSUPPORTED"

    def test_tier_is_always_zero(self):
        """Tier-0 = ground truth from source code."""
        r_verified = pa.probe_symbol("json", "dumps")
        r_missing = pa.probe_symbol("json", "nonexistent_xyz")
        assert r_verified["tier"] == 0
        assert r_missing["tier"] == 0

    def test_package_field_is_set(self):
        result = pa.probe_symbol("json", "dumps")
        assert result["package"] == "json"

    def test_symbol_field_is_set(self):
        result = pa.probe_symbol("json", "dumps")
        assert result["symbol"] == "dumps"

    def test_nested_symbol_path_verified(self):
        """pathlib.Path.read_text as multi-segment path."""
        result = pa.probe_symbol("pathlib", "Path.read_text")
        assert result["exists"] is True
        assert result["verdict"] == "VERIFIED"

    def test_nested_symbol_path_missing(self):
        """pathlib.Path.this_does_not_exist — fails at last segment."""
        result = pa.probe_symbol("pathlib", "Path.this_does_not_exist_xyz")
        assert result["exists"] is False
        assert result["verdict"] == "UNSUPPORTED"

    def test_details_message_on_failure(self):
        result = pa.probe_symbol("json", "nonexistent_xyz")
        details = result.get("details", {})
        assert "message" in details
        assert "json" in details["message"] or "nonexistent_xyz" in details["message"]

    def test_class_probe_has_public_methods(self):
        result = pa.probe_symbol("json", "JSONEncoder")
        assert result["exists"] is True
        # public_methods may be in result or result['details'] depending on structure
        assert "public_methods" in result or "public_methods" in result.get("details", {})
