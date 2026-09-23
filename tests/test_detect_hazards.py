"""
test_detect_hazards.py — Unit tests for detect_hazards.py

All tests are self-contained. No network calls are made.
"""

import json
import sys
import pytest
from pathlib import Path

import detect_hazards as dh


# ---------------------------------------------------------------------------
# detect_hazard_patterns
# ---------------------------------------------------------------------------

class TestDetectHazardPatterns:

    def test_no_packages_returns_empty(self):
        result = dh.detect_hazard_patterns({})
        assert result["hazards_detected"] == []
        assert result["warnings"] == []

    def test_fastapi_and_flask_triggers_async_sync_hazard(self):
        packages = {
            "fastapi": {"version": "0.120.0"},
            "flask": {"version": "3.0.0"},
        }
        result = dh.detect_hazard_patterns(packages)
        classes = [h["hazard_class"] for h in result["hazards_detected"]]
        assert "async_sync_boundary" in classes

    def test_sqlalchemy_and_celery_triggers_session_lifecycle_hazard(self):
        packages = {
            "sqlalchemy": {"version": "2.0.36"},
            "celery": {"version": "5.4.0"},
        }
        result = dh.detect_hazard_patterns(packages)
        classes = [h["hazard_class"] for h in result["hazards_detected"]]
        assert "session_lifecycle_mismatch" in classes

    def test_aiohttp_and_httpx_triggers_event_loop_warning(self):
        packages = {
            "aiohttp": {"version": "3.9.0"},
            "httpx": {"version": "0.27.0"},
        }
        result = dh.detect_hazard_patterns(packages)
        warn_classes = [w["hazard_class"] for w in result["warnings"]]
        assert "event_loop_ownership" in warn_classes

    def test_pydantic_and_redis_triggers_serialization_warning(self):
        packages = {
            "pydantic": {"version": "2.9.2"},
            "redis": {"version": "5.1.0"},
        }
        result = dh.detect_hazard_patterns(packages)
        warn_classes = [w["hazard_class"] for w in result["warnings"]]
        assert "serialization_contract" in warn_classes

    def test_protobuf_v4_and_grpcio_triggers_warning(self):
        packages = {
            "protobuf": {"version": "4.25.0"},
            "grpcio": {"version": "1.62.0"},
        }
        result = dh.detect_hazard_patterns(packages)
        warn_classes = [w["hazard_class"] for w in result["warnings"]]
        assert "dependency_version_conflict" in warn_classes

    def test_protobuf_v3_does_not_trigger_grpc_warning(self):
        packages = {
            "protobuf": {"version": "3.20.3"},
            "grpcio": {"version": "1.62.0"},
        }
        result = dh.detect_hazard_patterns(packages)
        warn_classes = [w["hazard_class"] for w in result["warnings"]]
        assert "dependency_version_conflict" not in warn_classes

    def test_unrelated_packages_produce_no_hazards(self):
        packages = {
            "requests": {"version": "2.31.0"},
            "click": {"version": "8.1.7"},
        }
        result = dh.detect_hazard_patterns(packages)
        assert result["hazards_detected"] == []
        assert result["warnings"] == []

    def test_case_insensitive_package_names(self):
        """Package names should be matched case-insensitively."""
        packages = {
            "FastAPI": {"version": "0.120.0"},
            "Flask": {"version": "3.0.0"},
        }
        result = dh.detect_hazard_patterns(packages)
        classes = [h["hazard_class"] for h in result["hazards_detected"]]
        assert "async_sync_boundary" in classes

    def test_hazard_has_blast_radius(self):
        packages = {
            "fastapi": {"version": "0.120.0"},
            "flask": {"version": "3.0.0"},
        }
        result = dh.detect_hazard_patterns(packages)
        hazard = result["hazards_detected"][0]
        assert "blast_radius" in hazard
        assert hazard["blast_radius"] == "load-bearing"


# ---------------------------------------------------------------------------
# check_eol_packages
# ---------------------------------------------------------------------------

class TestCheckEolPackages:

    def test_no_packages_returns_empty(self):
        result = dh.check_eol_packages({})
        assert result["eol_packages"] == []
        assert result["yanked_packages"] == []

    def test_yanked_package_is_flagged(self):
        packages = {
            "mypackage": {"version": "1.0.0", "yanked": True},
        }
        result = dh.check_eol_packages(packages)
        assert len(result["yanked_packages"]) == 1
        assert result["yanked_packages"][0]["package"] == "mypackage"

    def test_not_yanked_package_is_not_flagged(self):
        packages = {
            "mypackage": {"version": "1.0.0", "yanked": False},
        }
        result = dh.check_eol_packages(packages)
        assert result["yanked_packages"] == []

    def test_missing_yanked_field_defaults_to_not_yanked(self):
        packages = {
            "mypackage": {"version": "1.0.0"},
        }
        result = dh.check_eol_packages(packages)
        assert result["yanked_packages"] == []

    def test_django_2_2_flagged_as_eol(self):
        packages = {
            "django": {"version": "2.2.28", "yanked": False},
        }
        result = dh.check_eol_packages(packages)
        assert len(result["eol_packages"]) == 1
        assert result["eol_packages"][0]["eol_date"] == "2024-04-01"

    def test_django_4_2_not_flagged_as_eol(self):
        packages = {
            "django": {"version": "4.2.9", "yanked": False},
        }
        result = dh.check_eol_packages(packages)
        assert result["eol_packages"] == []


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------

class TestGenerateReport:

    def _empty_hazards(self):
        return {"hazards_detected": [], "warnings": []}

    def _empty_eol(self):
        return {"eol_packages": [], "yanked_packages": [], "warnings": []}

    def test_no_issues_produces_ok_status(self):
        report = dh.generate_report(self._empty_hazards(), self._empty_eol(), {"a": {}})
        assert report["summary"]["status"] == "OK"

    def test_hazard_detected_produces_hazards_detected_status(self):
        hazards = {
            "hazards_detected": [{"hazard_class": "async_sync_boundary"}],
            "warnings": [],
        }
        report = dh.generate_report(hazards, self._empty_eol(), {"a": {}})
        assert report["summary"]["status"] == "HAZARDS_DETECTED"

    def test_warning_only_produces_warnings_status(self):
        hazards = {
            "hazards_detected": [],
            "warnings": [{"hazard_class": "serialization_contract"}],
        }
        report = dh.generate_report(hazards, self._empty_eol(), {"a": {}})
        assert report["summary"]["status"] == "WARNINGS"

    def test_yanked_package_produces_hazards_detected_status(self):
        eol = {
            "eol_packages": [],
            "yanked_packages": [{"package": "bad", "version": "0.1"}],
            "warnings": [],
        }
        report = dh.generate_report(self._empty_hazards(), eol, {"a": {}})
        assert report["summary"]["status"] == "HAZARDS_DETECTED"

    def test_package_count_in_summary(self):
        packages = {"a": {}, "b": {}, "c": {}}
        report = dh.generate_report(self._empty_hazards(), self._empty_eol(), packages)
        assert report["summary"]["packages_checked"] == 3


# ---------------------------------------------------------------------------
# load_uv_lock (filesystem, no network)
# ---------------------------------------------------------------------------

class TestLoadUvLock:

    def test_returns_none_for_missing_file(self, tmp_path):
        result = dh.load_uv_lock(str(tmp_path / "nonexistent.lock"))
        assert result is None

    def test_parses_basic_uv_lock(self, tmp_path):
        lock_content = """
version = 1
revision = 1

[[package]]
name = "sqlalchemy"
version = "2.0.36"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "pydantic"
version = "2.9.2"
source = { registry = "https://pypi.org/simple" }
"""
        lock_file = tmp_path / "uv.lock"
        lock_file.write_text(lock_content)
        result = dh.load_uv_lock(str(lock_file))
        assert result is not None
        assert "sqlalchemy" in result["packages"]
        assert result["packages"]["sqlalchemy"]["version"] == "2.0.36"
        assert "pydantic" in result["packages"]

    def test_empty_lock_returns_empty_packages(self, tmp_path):
        lock_content = "version = 1\nrevision = 1\n"
        lock_file = tmp_path / "uv.lock"
        lock_file.write_text(lock_content)
        result = dh.load_uv_lock(str(lock_file))
        assert result is not None
        assert result["packages"] == {}


# ---------------------------------------------------------------------------
# load_stack_lock (filesystem)
