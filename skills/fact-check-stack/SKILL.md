# fact-check-stack

**Purpose:** Verify technical feasibility and feature correctness of project architectures before agentic codegen begins. Double-check ADR assumptions against live documentation, cross-reference package compatibility, and surface implementation hazards.

**Type:** Advisory verification; produces a human-readable feasibility report and risk register. Non-blocking — does not halt planning agents, but flags decisions that warrant review or ADR revision.

**Scope:** Python (default). Version resolution is delegated to [uv](https://docs.astral.sh/uv/); the skill's unique value is Phases 2–6: claim verification, hazard detection, field research, and advisory reporting.

---

## Quick Entry-Point Decision

```
Do you already have a uv.lock or pinned requirements?
│
├── YES → Skip Phase 1. Go directly to Phase 2 (Claim Extraction).
│          Parse uv.lock for package versions (see references/uv-integration.md).
│
└── NO  → Run Phase 1: `uv lock --all-platforms`
           If uv is unavailable: install via `curl -LsSf https://astral.sh/uv/install.sh | sh`
           If uv lock fails (resolution error): report REVISE-ADR and stop.
```

---

## Workflow

### Phase 1: Intake & Stack Resolution (optional if uv.lock exists)

Input: ADR artifact(s) defining architecture, dependencies, and version constraints.

**If a `uv.lock` already exists:** skip to Phase 2. Parse it to extract the pinned package map (see `references/uv-integration.md`).

**If no lockfile exists:**
1. Parse explicit version pins, ranges, and constraints from ADR text.
2. Run `uv lock --all-platforms` to produce `uv.lock`:
   - Resolves version ranges to concrete releases using PubGrub (the same solver as cargo)
   - Validates co-installability, Python version ranges, transitive constraints
   - **Hard gate:** If `uv lock` fails (resolution error), report REVISE-ADR and stop. A claim cannot be verified against a version that cannot be installed.

### Phase 2: Claim Extraction

From ADR prose, extract atomic claims using the schema in **Claim Model** below. Rank by **blast radius**:
- `load-bearing`: Architecture decision hinge. No mitigation path. Blocks if REFUTED.
- `contained`: Single component. Affects implementation detail. Can refactor if wrong.
- `reversible`: Config, optional feature, shim-able. Low cost to reverse.

**Stop rule:** Extract up to 20 claims per ADR. If more exist, focus on load-bearing and cross-reference boundaries. Advisory mode accepts incomplete coverage.

### Phase 3: Verify (Tier 0/1 — Official Sources)

For each claim:

1. Consult `references/doc-access-playbook.md` for the appropriate fetch endpoint (pinned version, raw markdown, API).
2. Run `scripts/fetch_doc.py [url] [claim-context]` to retrieve, cache, and extract relevant passage.
3. For Python packages, verify symbol existence (Tier-0 ground truth) using one of these methods:
   - **Pre-installation (Preferred during planning):** Run `scripts/probe_objects_inv.py --url <objects.inv URL> --symbol <name>` to query the remote Sphinx inventory without installing the package.
   - **Post-installation (Fallback):** If the package is already installed (e.g., via `uv sync`), run `scripts/probe_api.py --package [package] --symbol [symbol.path]` to verify via live import.
4. **Verdict candidates:**
   - `VERIFIED`: Tier-0 source (official docs, type stubs, source at tag) explicitly confirms or implies the assertion.
   - `REFUTED`: Tier-0 source contradicts the assertion.
   - `PARTIAL`: Tier-0 source documents the feature but with caveats (version-gated, beta, deprecated path, undocumented behavior).
   - `UNVERIFIABLE`: No Tier-0 source found, and the claim is reversible or contained (no Tier-2 sweep).

### Phase 4: Cross-Reference (Mechanical & Semantic)

Run `scripts/detect_hazards.py --uv-lock uv.lock`:
- **Mechanical (uv's job):** Version resolution, co-installability, Python version ranges — already done in Phase 1.
- **Semantic (skill's job):** Agent detects known hazard patterns from the package set: async/sync boundary violations, session-lifecycle mismatches, event-loop ownership conflicts, serialization contract mismatches, yanked and EOL packages.
- Patterns are catalogued in `references/compatibility-patterns.md`.

Document each hazard as a separate claim and route to Tier-2 sweep if load-bearing.

### Phase 5: Field Sweep (Tier 2 — Community Sources)

**Only run for:**
- Claims that came back PARTIAL or UNVERIFIABLE and are load-bearing.
- Hazard patterns flagged in cross-reference that need real-world implementation validation.

Consult `references/community-research.md` for query strategy and trusted sources (Stack Overflow, GitHub discussions, official forums, project wikis). Run guided agent search; agent must check post date vs. package release date and scope evidence staleness.

**Cost boundary:** Max 5 fetches per claim; stop after N total field-sweep claims reach verdict.

### Phase 6: Adjudicate & Report

Aggregate verdicts into:
- **Feasibility statement:** GO / GO-WITH-MITIGATION / REVISE-ADR.
- **Risk register:** Claim ID, verdict, blast radius, evidence tier, mitigation (if applicable).
- **Proposed amendments:** For PARTIAL or REVISE-ADR claims, write out ADR diffs.

Serialize to `feasibility-report.md` and `risk-register.json`. Cache all evidence under `.fact-check/cache/[sha].txt` with retrieval timestamp.

---

## Claim Model

```json
{
  "claim_id": "C-007",
  "adr_ref": "ADR-003 §Persistence",
  "type": "capability | version-compat | api-shape | perf | ops | licensing | cost",
  "subject": "sqlalchemy@2.0.36",
  "assertion": "AsyncSession supports nested transactions via begin_nested()",
  "context": "Used in request-scoped handler to isolate tenant-specific writes.",
  "blast_radius": "load-bearing | contained | reversible",
  "verification": {
    "tier": 0,
    "source": "https://docs.sqlalchemy.org/20/orm/extensions/asyncio.html",
    "anchor": "#sqlalchemy.ext.asyncio.AsyncSession.begin_nested",
    "retrieved": "2026-09-22T14:30:00Z",
    "cache_path": ".fact-check/cache/c007_docs_sq2-0-36.txt"
  },
  "verdict": "VERIFIED | REFUTED | PARTIAL | UNVERIFIABLE",
  "caveat": "Optional. If PARTIAL, explain limitation (e.g., 'feature is beta', 'undocumented behavior', 'version-gated').",
  "mitigation": "Optional. If verdict is PARTIAL or GO-WITH-MITIGATION, propose concrete change to ADR or implementation.",
  "related_claims": ["C-006", "C-009"]
}
```

**Verdict definitions:**

| Verdict | Meaning | Next Action |
|---------|---------|------------|
| VERIFIED | Tier-0 source explicitly supports the assertion. | Document evidence, move forward. |
| REFUTED | Tier-0 source contradicts the assertion. | Flag REVISE-ADR; propose alternative approach. |
| PARTIAL | Tier-0 source confirms feature with caveats (beta, undocumented, version-gated, deprecated). | Assess risk. If load-bearing, propose mitigation and document decision. |
| UNVERIFIABLE | No Tier-0 source found. Tier-2 sweep did not yield high-signal evidence. | If reversible/contained, accept as risk and document. If load-bearing, escalate to REVISE-ADR. |
| UNSUPPORTED | Assertion describes a capability that doesn't exist in the stated version. Often discovered during symbol probe. | Trigger REVISE-ADR. |

---

## Integration with Agents

### For IDE/Coding Agents

When agent encounters a tool call referencing fact-check-stack:

1. **Do not invoke browser/computer-use tools.** All document fetches go through `scripts/fetch_doc.py`.
2. **Do not guess URLs.** Consult `references/doc-access-playbook.md` for the canonical endpoint for the package host.
3. **Always include version.** `docs.sqlalchemy.org/2.0/` or `docs.sqlalchemy.org/3.0/`. Never `docs.sqlalchemy.org/latest/`.
4. **Cache is law.** If a cache hit exists for [package]@[version] at [claim], reuse it. Reduces redundant calls.
5. **Stop at Tier-0.** If official docs are silent, that's UNVERIFIABLE — do not invent a search strategy. Escalate to the planning/review agent with UNVERIFIABLE + blast_radius for decision.

### For Planning/Architecture Agents

When review phase yields a report:

1. **GO:** All load-bearing claims are VERIFIED or PARTIAL-with-mitigation. Proceed to codegen.
2. **GO-WITH-MITIGATION:** Some load-bearing claims are PARTIAL. Document mitigations in ADR §Risk Assumptions. Proceed if mitigations are concrete (e.g., "use X wrapper to hide version-specific behavior").
3. **REVISE-ADR:** One or more load-bearing claims are REFUTED or UNVERIFIABLE with no Tier-2 evidence. Update ADR with alternative approach (e.g., swap library, pin earlier version, use conditional codegen). Re-run Phase 1–3.
4. **REVISE-ADR (most severe):** Unresolvable conflicts (e.g., two dependencies require incompatible Python versions, a pinned version doesn't exist, or Phase 1 `uv lock` fails). Update the ADR and re-run from Phase 1.

---

## Reference Files

- **`references/uv-integration.md`** — ⭐ Start here if you have a uv.lock. uv commands, lockfile parsing, Phase 1 fast-path, what uv cannot do.
- **`references/evidence-standards.md`** — Tiers, citation format, verdict rubric detail, staleness rules, stop conditions.
- **`references/doc-access-playbook.md`** — Endpoint recipes per ecosystem host, anti-patterns to avoid, HTTP caching strategy.
- **`references/community-research.md`** — Trusted sources, query strategies, how to spot red-flag posts, date validation.
- **`references/compatibility-patterns.md`** — Hazard class catalog (async/sync boundary, session-lifecycle, event loops, serialization, etc.) + probe recipes.
- **`references/ecosystems/python.md`** — Python-specific: PyPI, objects.inv, uv/pip, wheel tags, `inspect.signature()` ground truth.

## Scripts

All scripts are standalone, stdlib-heavy, require no installation of the skill itself.
**Version resolution is handled by `uv` — not by a skill script.**

- **`scripts/detect_hazards.py`** — Semantic hazard pattern detection (async/sync, session lifecycle, serialization) + EOL/yanked package signals. Accepts `--uv-lock uv.lock` (required; run `uv lock` first).
- **`scripts/fetch_doc.py`** — Fetch versioned docs, cache, extract passages, log provenance.
- **`scripts/probe_objects_inv.py`** — Pre-installation symbol verification. Fetches and parses remote Sphinx `objects.inv` without installing the target package. Accepts `--url`, `--symbol`, `--domain`, `--role`, `--json`.
- **`scripts/probe_api.py`** — Post-installation live import + `inspect` probe (Tier-0). Fallback when the package is already installed. Accepts `--package` and `--symbol`.
- **`scripts/ledger.py`** — Validate, append, aggregate claims; compute feasibility statement; serialize report and risk register.

## Templates

- **`templates/ledger-template.json`** — Claim ledger structure; `ledger.py` validates against this.
- **`templates/feasibility-report.md`** — Feasibility report scaffold with placeholder sections.

## Usage Example (Agent Prompt)

```
You are designing a feature to cache API responses. Your ADR pins:
  - fastapi==0.120.0
  - redis==5.1.0
  - pydantic==2.9.2

Before writing code, verify:
1. That fastapi and redis versions are compatible (both support async).
2. That pydantic can serialize objects to Redis values.
3. That there are no known issues with redis>=5.0 and asyncio.

Use the fact-check-stack skill:

# Phase 1 (skip if uv.lock already exists)
uv lock --all-platforms          # Resolution error → REVISE-ADR and stop.

# Phase 2: Parse lockfile → extract claim subjects
# C-001: FastAPI 0.120.0 supports async route handlers
# C-002: Pydantic 2.9.2 → Redis serialization contract
# C-003: redis==5.1.0 + asyncio compatibility

# Phase 3: Verify claims against official docs
python scripts/fetch_doc.py --url "https://fastapi.tiangolo.com/..." --claim-id C-001
python scripts/probe_objects_inv.py --url https://docs.pydantic.dev/2.9/objects.inv --symbol "BaseModel.model_validate_json" --json
# (fallback if pydantic already installed)
python scripts/probe_api.py --package pydantic --symbol "BaseModel.model_validate_json" --json

# Phase 4: Detect semantic hazards
python scripts/detect_hazards.py --uv-lock uv.lock --output .fact-check/hazard-report.json

# Phase 5: Record claims
python scripts/ledger.py --load .fact-check/ledger.json --add-claim C-001 --verdict VERIFIED --blast-radius load-bearing

# Phase 6: Aggregate and report
python scripts/ledger.py --load .fact-check/ledger.json --report .fact-check/feasibility-report.md --adr-name "ADR-003"
```

---

## Design Principles

1. **Falsifiable claims only.** "The API is good" is not a claim. "AsyncSession.begin_nested() exists in sqlalchemy==2.0.36" is.
2. **Evidence tier gates verdict.** Community posts can raise caveats; they cannot promote a claim to VERIFIED.
3. **Scope is bounded.** Extract ~20 claims, verify load-bearing and cross-references exhaustively, accept incomplete coverage on reversible claims.
4. **Advisory, not blocking.** Reports inform human review and ADR revision; they do not halt planning agents.
5. **Caches are auditable.** Every citation has a retrieved-date and a cache file. Reports are diffable in version control.
6. **Vendor-agnostic patterns.** The claim, evidence tier, and verdict model apply to Python, Node.js, Go, and other ecosystems.

---

## Version

- **Skill version:** 2.0.0
- **Last updated:** 2026-09-23
- **Ecosystem default:** Python 3.8+ (version resolution requires uv)
- **Breaking change from v1:** `resolve_stack.py` removed; `check_compat.py` renamed to `detect_hazards.py` with narrowed scope; `probe_api.py` objects.inv parsing removed, now live-import only; `probe_objects_inv.py` added as pre-installation symbol probe; `BLOCKED` feasibility state removed, replaced by `REVISE-ADR`.
