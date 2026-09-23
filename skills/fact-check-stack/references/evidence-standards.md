# Evidence Standards & Verdict Rubric

## Evidence Tiers

The tier of an evidence source determines what verdict it can support.

| Tier | Source Examples | Can Establish | Cannot Establish |
|------|---|---|---|
| **Tier 0** | Version-pinned official docs; source code at release tag; CHANGELOG; type stubs (`*.pyi`); `objects.inv` (Sphinx inventory); live probe via `probe_api.py` (`inspect` on installed source); release notes | VERIFIED, REFUTED | Mitigations (too official) |
| **Tier 1** | Maintainer statements in GitHub issues (closed with explanation); GitHub Discussions (maintainer answer); Pull Request comments (author/maintainer); official project announcements | VERIFIED, REFUTED | Firm timelines or guarantees (outside scope) |
| **Tier 2** | Accepted Stack Overflow answers (green checkmark); GitHub Discussions (community consensus); high-quality blog posts by package maintainers or well-known community members; project mailing list archives; official community forums | Caveats, Known-Bug Flags, Implementation Hazards, Risk Entries | Verdict promotion. Must be gated to mitigation/caveat only. |
| **Tier 3** | General blogs, tutorials, LLM-generated content, Reddit, AI chatbot outputs, unofficial wikis | Leads only. Must be traced back to Tier 0/1 or discarded. | Anything else. |

### Verdict Mapping to Evidence Tiers

| Verdict | Minimum Tier | Notes |
|---------|---|---|
| VERIFIED | 0 or 1 | Assertion explicitly supported by official docs or maintainer statement. |
| REFUTED | 0 or 1 | Assertion explicitly contradicted by official docs or maintainer statement. |
| PARTIAL | 0 or 1 | Feature exists but with documented caveats, version-gating, deprecation warnings, or undocumented behavior flagged in Tier-0. |
| UNVERIFIABLE | 0 (no source) + failed Tier 2 | No Tier-0 source found; Tier-2 sweep found no high-signal evidence. |
| UNSUPPORTED | 0 (symbol probe) | Assertion names a symbol/capability that provably does not exist in the target version. Discovered via remote `objects.inv` or `probe_api.py` (live import + `inspect.signature()`). |

**Critical rule:** A Tier-2 post cannot promote a claim to VERIFIED, but it *can* raise it from UNVERIFIABLE to a mitigation/caveat entry in the risk register.

---

## Citation Format

Every evidence entry must include:

```json
{
  "source": "https://docs.sqlalchemy.org/20/orm/extensions/asyncio.html",
  "anchor": "#sqlalchemy.ext.asyncio.AsyncSession.begin_nested",
  "retrieved": "2026-09-22T14:30:00Z",
  "tier": 0,
  "cache_path": ".fact-check/cache/c007_sq_asyncio_20.txt"
}
```

**Fields:**
- `source`: Full, versioned URL. Never `latest`, always specific release.
- `anchor`: Fragment identifier or page section. If fetching raw markdown/rst, note the line range or section header.
- `retrieved`: ISO 8601 timestamp when the citation was fetched.
- `tier`: 0, 1, or 2 (not 3).
- `cache_path`: Relative path to the cached artifact. Format: `.fact-check/cache/[claim_id]_[source_slug]_[version].txt`.

### Cache File Format

```
METADATA
--------
source_url: https://docs.sqlalchemy.org/20/orm/extensions/asyncio.html
retrieved: 2026-09-22T14:30:00Z
http_status: 200
content_type: text/html (converted to markdown)

CONTENT
-------
[Full or relevant excerpt of the fetched document, with section preserved]

RELEVANCE_NOTE
--------------
[Agent's note on which parts of the content answered the claim]
```

Cache files are immutable once written. If a version is updated, a new cache entry is created.

---

## Staleness Rules

### For Tier-0 (Official Docs)

A Tier-0 source is stale if:
- The pinned version is > 18 months old AND the current major version has advanced AND the feature was changed between versions.
- The docs site has been deprecated or the version has been EOL'd for > 12 months without a compatibility guide.

**Action:** If stale, treat as UNVERIFIABLE and escalate to Tier-2 for real-world implementation caveats.

Example: "We're using Django 2.2 (EOL 2024-04-01). The docs say it supports async views, but that was added in Django 3.1. Current docs show Django 5.0+. Treat as UNVERIFIABLE."

### For Tier-1 (Maintainer Statements)

Tier-1 is stale if:
- The maintainer statement is from an issue closed > 2 years ago, the package has had major version bumps since, and the statement doesn't reference the current version.
- The PR/issue references a feature that was later reverted or changed.

**Action:** Cross-reference with current Tier-0 docs. If contradiction, note discrepancy and escalate.

### For Tier-2 (Community Sources)

A Tier-2 source is stale if:
- Posted date < the target package's release date (impossible to have tested the exact version).
- Posted date > 18 months before current date AND the package has had 2+ minor or major version bumps since.
- The poster explicitly states "I tested this on version X" and X ≠ the target version.

**Action:** Flag as stale and do not cite. Tier-2 findings must be post-dated after the target package release or they are unreliable.

**Example:** "This SO answer is from 2022-03, discussing 'newer versions of fastapi.' The target is fastapi==0.120.0 (2024-11). The answer is stale unless it explicitly confirms the newer version."

---

## Stop Rules & Scope Boundaries

### Claim Extraction

- **Max claims per ADR:** 20. If the ADR implies more, prioritize:
  1. Architectural hinges (load-bearing claims that determine framework choice).
  2. Cross-library boundaries (async contracts, session lifecycles, event loops).
  3. Constraints that would invalidate the design (unsupported Python version, license conflict).
  4. Ignore implementation details, cosmetic library choices, and reversible configuration.

### Verification Phase

- **Max fetches per claim:** 3 (initial doc, backup source, confirm conflict if needed).
- **Stop at Tier-0:** If official docs are silent and the claim is reversible, stop and mark UNVERIFIABLE. Do not escalate to Tier-2 without explicit instruction.

### Field Sweep (Tier-2)

- **Only run for load-bearing claims with verdict PARTIAL or UNVERIFIABLE.**
- **Max field-sweep claims:** 5. If more are UNVERIFIABLE, accept them as risk and document.
- **Max fetches per field-sweep claim:** 5 total searches + 2 read-throughs.

### Report Generation

- **Max risk entries:** All extracted claims. (No truncation here.)
- **Proposed amendments:** If > 3 claims require REVISE-ADR, synthesize into 1–2 ADR revision sections rather than one-to-one mappings.

---

## Contradictions & Edge Cases

### What if Tier-0 and Tier-1 conflict?

Example: Official docs say feature X exists, but a GitHub issue from a maintainer says it was removed.

1. Check release dates. If the issue post-dates the docs, the docs are outdated. Escalate to Tier-0 again (check current version).
2. If dates are ambiguous, cite both sources and mark verdict as PARTIAL with a caveat: "Contradictory documentation."
3. Escalate to human review with both citations.

### What if Tier-0 is ambiguous or undocumented?

If the official docs do not mention a feature, but the source code at the tag clearly implements it:

1. This is still Tier-0. Query the remote `objects.inv` file, or run `probe_api.py --package <pkg> --symbol <symbol>` to check live source if the package is installed.
2. Verdict: VERIFIED if the symbol exists; UNSUPPORTED if it doesn't.
3. Caveat: Mark as "undocumented feature" in the risk register.

### What if there's no official docs (e.g., small package)?

1. Fall back to Tier-1: well-documented GitHub README, CHANGELOG, and PR comments.
2. If no Tier-1 source, install and probe with `inspect.signature()` — this is Tier-0 ground truth.
3. If the package is unmaintained or undocumented, mark all claims as UNVERIFIABLE and document the risk.

### What if Tier-2 evidence contradicts Tier-0?

This is a real-world scenario: docs say something will work, but a dozen SO answers say it doesn't.

1. Do not demote Tier-0. Instead, create a separate caveat entry: "Official docs claim X, but community reports consistent failure on [condition]."
2. Verdict remains VERIFIED (it *is* documented), but blast_radius and mitigation reflect the caveat.
3. Example: "FastAPI docs claim WebSocket is fully async, VERIFIED. Caveat: Community reports show connection pooling can block event loop in production without explicit `asyncio.wait_for()` wrapping. Mark as PARTIAL and mitigate with explicit timeout."

---

## Verdict Examples

### VERIFIED
```json
{
  "claim": "pydantic.BaseModel supports .model_validate_json() in pydantic==2.5.0",
  "tier": 0,
  "source": "https://docs.pydantic.dev/2.5/api/base_model/#pydantic.BaseModel.model_validate_json",
  "verdict": "VERIFIED",
  "caveat": null
}
```

### REFUTED
```json
{
  "claim": "pydantic==1.10 supports model_validate_json()",
  "tier": 0,
  "source": "https://docs.pydantic.dev/1.10/api/base_model/ (no such method listed)",
  "verdict": "REFUTED",
  "mitigation": "Upgrade to pydantic>=2.0 or use .parse_raw() and .parse_obj() in v1."
}
```

### PARTIAL
```json
{
  "claim": "asyncpg connection pooling is thread-safe",
  "tier": 0,
  "source": "https://magicstack.github.io/asyncpg/current/api/index.html#connection-pools",
  "verdict": "PARTIAL",
  "caveat": "Docs state pools are safe for asyncio tasks within a single thread. Not safe across threads without locks. Design must pin pool to single event loop.",
  "mitigation": "Document in ADR: 'Pool is per-event-loop. Pass same pool instance to all tasks in the loop.'"
}
```

### UNVERIFIABLE
```json
{
  "claim": "SQLAlchemy 2.0 async queries perform better than sync queries on high-concurrency workloads",
  "tier": 0,
  "source": "No quantitative performance claims in official docs",
  "tier_2_result": "Found SO answer claiming 2–3x faster, but on author's specific workload (thousands of small queries). Not generalizable.",
  "verdict": "UNVERIFIABLE",
  "blast_radius": "reversible",
  "recommendation": "Accept as risk. Design for async. If performance is poor, profile and consider sync as fallback."
}
```

### UNSUPPORTED
```json
{
  "claim": "fastapi.FastAPI().on_event('shutdown') in fastapi==0.100.0",
  "tier": 0,
  "source": "objects.inv probe + docs: method removed in 0.100.0; use lifespan context instead",
  "verdict": "UNSUPPORTED",
  "mitigation": "Replace on_event() with async context manager lifespan pattern."
}
```

---

## When to Stop

### Stop Verification If:
1. The pinned version does not exist (resolution failed). Hard gate; cannot proceed.
2. The claim is resolved to VERIFIED and blast_radius is not load-bearing.
3. The claim is UNVERIFIABLE, blast_radius is reversible, and Tier-2 sweep would exceed the cost boundary.

### Stop Field Sweep If:
1. More than 5 claims remain UNVERIFIABLE or PARTIAL. Accept them as risk; proceed to report.
2. You've spent > 10 total Tier-2 fetches. Consolidate findings and report.
3. Multiple Tier-2 sources contradict each other with no clear consensus. Document disagreement and escalate to human review.

### Stop Report If:
1. More than 3 load-bearing claims require ADR revision. The ADR itself is questionable; recommend full re-review rather than incremental patches.

---

## How Agents Use This Document

- **Claim extractors:** Use the examples and verdict definitions to write falsifiable claims.
- **Verifiers:** Use tiers and stop rules to decide when to fetch, when to probe, when to escalate.
- **Field-sweep agents:** Use staleness rules and Tier-2 guidance to vet community evidence.
- **Report generators:** Use verdict mappings and caveat examples to justify feasibility statements.

