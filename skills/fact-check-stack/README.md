# fact-check-stack: Technical Feasibility Verification

A skill for AI coding agents to verify technical claims in Architecture Decision Records (ADRs) before generating code. Produces a structured feasibility report and risk register.

> **Source of truth:** `SKILL.md` defines the full workflow and schema. This README is a quick-start guide.

---

## Why This Skill Exists

LLMs hallucinate about API surfaces, library versions, and feature availability. This skill enforces that every load-bearing claim in an ADR — "this library supports this feature at this version" — is verified against Tier-0 sources before code generation begins.

---

## Quick Start

### Prerequisites

```bash
# uv is required for version resolution (Phase 1)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify
uv --version
```

### Typical Run

```bash
# Phase 1: Resolve versions → uv.lock
uv lock --all-platforms
# If this fails → REVISE-ADR. Stop and report the conflict.

# Phase 2: Extract claims from the ADR (manual or agent-driven)
# See SKILL.md §Phase 2 for the claim schema.

# Phase 3a: Verify symbols — pre-installation (no package install needed)
python scripts/probe_objects_inv.py \
    --url https://docs.sqlalchemy.org/20/objects.inv \
    --symbol AsyncSession.begin_nested \
    --json

# Phase 3b: Fetch and cache versioned docs
python scripts/fetch_doc.py \
    --url "https://docs.pydantic.dev/2.9/api/base_model/" \
    --claim-id C-001

# Phase 3c: Verify symbols post-install (if package is already in venv)
python scripts/probe_api.py \
    --package pydantic \
    --symbol "BaseModel.model_validate_json" \
    --json

# Phase 4: Detect semantic hazards (async/sync, lifecycle, serialization)
python scripts/detect_hazards.py --uv-lock uv.lock --output .fact-check/hazard-report.json

# Phase 5: Record a claim in the ledger
python scripts/ledger.py \
    --load .fact-check/ledger.json \
    --add-claim C-001 \
    --assertion "SQLAlchemy 2.0.36 supports AsyncSession.begin_nested()" \
    --verdict VERIFIED \
    --blast-radius load-bearing \
    --tier 0 \
    --source "https://docs.sqlalchemy.org/20/orm/extensions/asyncio.html"

# Phase 6: Generate feasibility report
python scripts/ledger.py \
    --load .fact-check/ledger.json \
    --report .fact-check/feasibility-report.md \
    --adr-name "ADR-003"
```

---

## Feasibility Verdicts

| Verdict | Meaning | Action |
|---------|---------|--------|
| **GO** | All load-bearing claims VERIFIED | Proceed to codegen |
| **GO-WITH-MITIGATION** | Some PARTIAL claims with documented mitigations | Proceed; document mitigations in ADR |
| **REVISE-ADR** | Load-bearing claim REFUTED, UNSUPPORTED, or uv lock failed | Update ADR; re-run from Phase 1 |

---

## Claim Verdicts

| Verdict | Tier | Trigger |
|---------|------|---------|
| VERIFIED | 0 or 1 | Official docs/source explicitly confirm the assertion |
| REFUTED | 0 or 1 | Official source contradicts the assertion |
| PARTIAL | 0 or 1 | Feature exists with caveats, deprecation, or version gate |
| UNVERIFIABLE | — | No Tier-0 source found after exhausting fetch budget |
| UNSUPPORTED | 0 | Symbol provably absent (probe_objects_inv.py or probe_api.py returns not-exists) |

---

## Folder Structure

```
fact-check-stack/
├── SKILL.md                               # Full workflow, schemas, decision rules
├── README.md                              # This file — quick-start
├── scripts/
│   ├── probe_objects_inv.py               # Pre-install: query remote Sphinx objects.inv
│   ├── probe_api.py                       # Post-install: live import + inspect
│   ├── fetch_doc.py                       # Fetch and cache versioned docs
│   ├── detect_hazards.py                  # Semantic hazard detection (async/lifecycle/serialization)
│   └── ledger.py                          # Claim ledger + feasibility report generator
├── references/
│   ├── uv-integration.md                  # uv cheat-sheet and Phase 1 fast-path
│   ├── evidence-standards.md              # Evidence tier definitions and verdict rules
│   ├── doc-access-playbook.md             # How to fetch versioned docs per ecosystem
│   ├── community-research.md              # Tier-2 sweep protocol
│   ├── compatibility-patterns.md          # Hazard catalog (async, lifecycle, serialization, etc.)
│   └── ecosystems/
│       └── python.md                      # Python-specific guide: PyPI, objects.inv, inspect
└── templates/
    ├── ledger-template.json               # Claim ledger scaffold
    ├── stack-lock-template.json           # Stack resolution output scaffold
    └── feasibility-report.md             # Feasibility report scaffold
```

---

## Scripts Reference

| Script | Input | Output | When to Use |
|--------|-------|--------|-------------|
| **probe_objects_inv.py** | `--url` `--symbol` | JSON verdict | Phase 3 — pre-installation symbol check |
| **probe_api.py** | `--package` `--symbol` | JSON verdict | Phase 3 — post-installation live probe |
| **fetch_doc.py** | `--url` `--claim-id` | Cached text, provenance log | Phase 3 — fetch and cache a doc page |
| **detect_hazards.py** | `--uv-lock` | JSON hazard report | Phase 4 — semantic hazard detection |
| **ledger.py** | `--load` `--add-claim` / `--report` | ledger.json, report.md | Phase 5/6 — record claims, generate report |

---

## Evidence Cache

All fetched documents are cached under `.fact-check/cache/` (gitignored):

```
.fact-check/
├── cache/
│   ├── c001_sqlalchemy_asyncsession_20.txt
│   └── c003_fastapi_lifespan_0120.txt
├── ledger.json
├── hazard-report.json
└── feasibility-report.md
```

Cache files are immutable. Each file contains the source URL and retrieval timestamp for provenance.

---

## Key Constraints

- **Max 20 claims per ADR.** Focus on load-bearing claims first.
- **Max 3 fetch calls per claim.** Use cache hits aggressively.
- **Tier 2 cannot promote a claim to VERIFIED.** Community sources feed the risk register only.
- **uv.lock is required** before Phase 3. Claims reference pinned versions; a claim against an unresolved version is unverifiable by definition.

---

## See Also

- `SKILL.md` — Full 6-phase workflow, claim schema, decision rules, and phase-by-phase checklists.
- `references/uv-integration.md` — uv fast-path and lockfile parsing.
- `references/evidence-standards.md` — Complete verdict and tier definitions.
- `references/doc-access-playbook.md` — Fetching docs per package type.
