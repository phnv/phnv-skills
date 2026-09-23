"""
test_ledger.py — Unit tests for ledger.py

Tests claim creation, ledger management, validation,
feasibility computation, and report generation.
No network calls.
"""

import json
import pytest

import ledger as lg


# ---------------------------------------------------------------------------
# create_claim
# ---------------------------------------------------------------------------

class TestCreateClaim:

    def _valid_kwargs(self, **overrides):
        base = dict(
            claim_id="C-001",
            assertion="SQLAlchemy 2.0 supports AsyncSession.begin_nested()",
            verdict="VERIFIED",
            blast_radius="load-bearing",
            tier=0,
            source="https://docs.sqlalchemy.org/20/orm/extensions/asyncio.html",
        )
        base.update(overrides)
        return base

    def test_creates_valid_claim(self):
        claim = lg.create_claim(**self._valid_kwargs())
        assert claim["claim_id"] == "C-001"
        assert claim["verdict"] == "VERIFIED"
        assert claim["blast_radius"] == "load-bearing"
        assert claim["tier"] == 0
        assert "recorded_at" in claim

    def test_all_valid_verdicts_accepted(self):
        for verdict in ("VERIFIED", "REFUTED", "PARTIAL", "UNVERIFIABLE", "UNSUPPORTED"):
            claim = lg.create_claim(**self._valid_kwargs(verdict=verdict))
            assert claim["verdict"] == verdict

    def test_invalid_verdict_raises(self):
        with pytest.raises(ValueError, match="Invalid verdict"):
            lg.create_claim(**self._valid_kwargs(verdict="MAYBE"))

    def test_all_valid_blast_radii_accepted(self):
        for radius in ("load-bearing", "contained", "reversible"):
            claim = lg.create_claim(**self._valid_kwargs(blast_radius=radius))
            assert claim["blast_radius"] == radius

    def test_invalid_blast_radius_raises(self):
        with pytest.raises(ValueError, match="Invalid blast_radius"):
            lg.create_claim(**self._valid_kwargs(blast_radius="catastrophic"))

    def test_all_valid_tiers_accepted(self):
        for tier in (0, 1, 2, 3):
            claim = lg.create_claim(**self._valid_kwargs(tier=tier))
            assert claim["tier"] == tier

    def test_invalid_tier_raises(self):
        with pytest.raises(ValueError, match="Invalid tier"):
            lg.create_claim(**self._valid_kwargs(tier=99))

    def test_optional_caveat_included(self):
        claim = lg.create_claim(**self._valid_kwargs(caveat="Feature is beta"))
        assert claim["caveat"] == "Feature is beta"

    def test_optional_mitigation_included(self):
        claim = lg.create_claim(**self._valid_kwargs(mitigation="Use wrapper"))
        assert claim["mitigation"] == "Use wrapper"


# ---------------------------------------------------------------------------
# load_ledger / save_ledger
# ---------------------------------------------------------------------------

class TestLedgerIO:

    def test_load_creates_new_ledger_if_missing(self, tmp_path):
        result = lg.load_ledger(str(tmp_path / "nonexistent.json"))
        assert result is not None
        assert "claims" in result
        assert result["claims"] == []

    def test_load_returns_none_for_invalid_json(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{ not valid }")
        result = lg.load_ledger(str(bad))
        assert result is None

    def test_save_and_reload_roundtrip(self, tmp_path):
        ledger = {"claims": [], "created_at": "2026-09-22T00:00:00Z"}
        path = str(tmp_path / "ledger.json")
        assert lg.save_ledger(ledger, path) is True
        loaded = lg.load_ledger(path)
        assert loaded == ledger


# ---------------------------------------------------------------------------
# add_claim_to_ledger
# ---------------------------------------------------------------------------

class TestAddClaimToLedger:

    def _make_claim(self, claim_id="C-001"):
        return lg.create_claim(
            claim_id=claim_id,
            assertion="Test assertion",
            verdict="VERIFIED",
            blast_radius="contained",
            tier=0,
            source="https://example.com",
        )

    def test_adds_claim_to_empty_ledger(self):
        ledger = {"claims": []}
        lg.add_claim_to_ledger(ledger, self._make_claim())
        assert len(ledger["claims"]) == 1

    def test_duplicate_claim_id_replaces_existing(self):
        ledger = {"claims": []}
        claim_v1 = self._make_claim("C-001")
        claim_v2 = lg.create_claim(
            claim_id="C-001",
            assertion="Updated assertion",
            verdict="PARTIAL",
            blast_radius="contained",
            tier=0,
            source="https://example.com",
        )
        lg.add_claim_to_ledger(ledger, claim_v1)
        lg.add_claim_to_ledger(ledger, claim_v2)
        assert len(ledger["claims"]) == 1
        assert ledger["claims"][0]["verdict"] == "PARTIAL"

    def test_different_claim_ids_accumulate(self):
        ledger = {"claims": []}
        lg.add_claim_to_ledger(ledger, self._make_claim("C-001"))
        lg.add_claim_to_ledger(ledger, self._make_claim("C-002"))
        assert len(ledger["claims"]) == 2


# ---------------------------------------------------------------------------
# validate_ledger
# ---------------------------------------------------------------------------

class TestValidateLedger:

    def _valid_ledger(self):
        return {
            "claims": [
                {
                    "claim_id": "C-001",
                    "assertion": "X supports Y",
                    "verdict": "VERIFIED",
                    "blast_radius": "load-bearing",
                    "tier": 0,
                    "source": "https://example.com",
                }
            ]
        }

    def test_valid_ledger_returns_no_errors(self):
        errors = lg.validate_ledger(self._valid_ledger())
        assert errors == []

    def test_missing_claims_key_returns_error(self):
        errors = lg.validate_ledger({})
        assert any("claims" in e for e in errors)

    def test_missing_required_field_returns_error(self):
        ledger = {"claims": [{"claim_id": "C-001"}]}  # missing most fields
        errors = lg.validate_ledger(ledger)
        assert len(errors) > 0

    def test_invalid_verdict_in_claim_returns_error(self):
        ledger = self._valid_ledger()
        ledger["claims"][0]["verdict"] = "WRONG"
        errors = lg.validate_ledger(ledger)
        assert any("verdict" in e.lower() for e in errors)

    def test_invalid_blast_radius_returns_error(self):
        ledger = self._valid_ledger()
        ledger["claims"][0]["blast_radius"] = "nuclear"
        errors = lg.validate_ledger(ledger)
        assert any("blast_radius" in e.lower() for e in errors)

    def test_invalid_tier_returns_error(self):
        ledger = self._valid_ledger()
        ledger["claims"][0]["tier"] = 99
        errors = lg.validate_ledger(ledger)
        assert any("tier" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# compute_feasibility_statement
# ---------------------------------------------------------------------------

class TestComputeFeasibilityStatement:

    def _claim(self, verdict, blast_radius="load-bearing", mitigation=""):
        return {
            "blast_radius": blast_radius,
            "verdict": verdict,
            "mitigation": mitigation,
        }

    def test_no_claims_returns_go(self):
        assert lg.compute_feasibility_statement([]) == "GO"

    def test_no_load_bearing_claims_returns_go(self):
        claims = [
            self._claim("REFUTED", blast_radius="reversible"),
        ]
        assert lg.compute_feasibility_statement(claims) == "GO"

    def test_all_verified_load_bearing_returns_go(self):
        claims = [self._claim("VERIFIED"), self._claim("VERIFIED")]
        assert lg.compute_feasibility_statement(claims) == "GO"

    def test_refuted_load_bearing_returns_revise_adr(self):
        claims = [self._claim("REFUTED")]
        assert lg.compute_feasibility_statement(claims) == "REVISE-ADR"

    def test_unsupported_load_bearing_returns_revise_adr(self):
        claims = [self._claim("UNSUPPORTED")]
        assert lg.compute_feasibility_statement(claims) == "REVISE-ADR"

    def test_partial_with_mitigation_returns_go_with_mitigation(self):
        claims = [self._claim("PARTIAL", mitigation="Use X instead")]
        assert lg.compute_feasibility_statement(claims) == "GO-WITH-MITIGATION"

    def test_unverifiable_without_mitigation_returns_revise_adr(self):
        claims = [self._claim("UNVERIFIABLE")]
        assert lg.compute_feasibility_statement(claims) == "REVISE-ADR"


# ---------------------------------------------------------------------------
# generate_markdown_report
# ---------------------------------------------------------------------------

class TestGenerateMarkdownReport:

    def _ledger_with_claims(self, *claims):
        return {"claims": list(claims)}

    def _claim(self, claim_id, verdict, blast_radius="load-bearing", **kwargs):
        base = {
            "claim_id": claim_id,
            "assertion": f"Test assertion for {claim_id}",
            "verdict": verdict,
            "blast_radius": blast_radius,
            "tier": 0,
            "source": "https://example.com",
            "caveat": "",
            "mitigation": "",
        }
        base.update(kwargs)
        return base

    def test_report_contains_adr_name(self):
        ledger = self._ledger_with_claims()
        report = lg.generate_markdown_report(ledger, "ADR-007")
        assert "ADR-007" in report

    def test_report_contains_feasibility_status(self):
        ledger = self._ledger_with_claims(
            self._claim("C-001", "VERIFIED")
        )
        report = lg.generate_markdown_report(ledger)
        assert "GO" in report

    def test_report_contains_risk_register_section(self):
        ledger = self._ledger_with_claims(
            self._claim("C-001", "PARTIAL", caveat="Known issue")
        )
        report = lg.generate_markdown_report(ledger)
        assert "Risk Register" in report

    def test_refuted_claim_appears_in_report(self):
        ledger = self._ledger_with_claims(
            self._claim("C-002", "REFUTED")
        )
        report = lg.generate_markdown_report(ledger)
        assert "C-002" in report
        assert "REFUTED" in report

    def test_empty_ledger_produces_valid_report(self):
        ledger = {"claims": []}
        report = lg.generate_markdown_report(ledger)
        assert "# Feasibility Report" in report
        assert "No risks identified" in report
