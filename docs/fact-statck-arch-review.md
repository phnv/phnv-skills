Good catch. **Yes, there's real redundancy in Phases 1 and 4**, and you should absolutely use `uv` where it's better. Let me be direct:

## What's Redundant

| Task | uv | fact-check-stack | Winner |
|------|----|----|--------|
| Resolve version ranges → concrete versions | Fast, deterministic, battle-tested Rust | Slower Python script | **uv** |
| Check version range conflicts | Uses PubGrub solver, very accurate | Basic string matching | **uv** |
| Validate co-installability | ✓ (via dry-run resolution) | ✓ (via dry-run resolution) | **uv** |
| Produce lockfile | ✓ (`uv.lock`) | stack-lock.json | **uv.lock** |
| Fetch wheel metadata | ✓ | ✓ (PyPI JSON API) | **uv** (faster) |
| Validate Python version ranges | ✓ | ✓ (basic) | **uv** |

**Verdict:** Phase 1 (resolve_stack.py) and most of Phase 4 (check_compat.py for mechanical checks) should be replaced with `uv lock --all-platforms` + parsing `uv.lock`.

## What's NOT Redundant

| Task | uv | fact-check-stack | Winner |
|------|----|----|--------|
| Verify *feature* exists at version X | ✗ | ✓ (objects.inv, live introspection) | **skill** |
| Check if symbol API is undocumented/deprecated | ✗ | ✓ (Tier-0 + Tier-2 sweep) | **skill** |
| Detect semantic hazards (async/sync boundary, session lifecycle mismatch) | ✗ | ✓ (compatibility-patterns.md) | **skill** |
| Surface real-world caveats from community | ✗ | ✓ (Tier-2 field sweep) | **skill** |
| Validate assumptions against live docs | ✗ | ✓ (fetch_doc.py + doc-access-playbook) | **skill** |
| Produce advisory risk register + proposed ADR amendments | ✗ | ✓ | **skill** |

## New Approach

Refactor fact-check-stack to **delegate** Phase 1 and mechanical Phase 4 to uv - minimizing usage of scripts as possible:

## New Architecture (Revised)

```
fact-check-stack (v2.0)
├── SKILL.md (updated to mention uv integration)
├── references/
│   └── ... (unchanged)
├── scripts/
│   ├── fetch_doc.py (unchanged)
│   ├── probe_api.py (unchanged)
│   └── ledger.py (unchanged)
└── assets/
    └── uv-resources.md (NEW: how to use uv.lock as input)
```


## What I'd Change in the Artifact Set

1. **SKILL.md:** Add a note: "Phase 1 is optional if you already have a uv.lock file. fact-check-stack is primarily for Phases 2–6."

2. **resolve_stack.py:** Delete `resolve_stack.py` completely. Keep `uv lock` commands in `uv-resources.md` - no need for resolve_stack.py at all.

3. **check_compat.py:** Remove version range checks; keep only:
   - Hazard pattern detection
   - EOL package detection
   - (Version resolution is uv's job now)

4. **New file:** `uv-resources.md` explaining the handoff.

5. **Update doc-access-playbook.md:** Add a section: "For users with uv.lock, the version resolution phase is complete. Skip directly to Phase 3 (verify claims)."

## Bottom Line

**fact-check-stack is not primarily a version resolver.** It's a **claim verifier + hazard detector + advisory reporter**. 

The fact: uv does it better and faster. The real value is:

- Phases 3–6 (verify assumptions, detect hazards, field research, report).
- `doc-access-playbook.md` (safe agent endpoints).
- `compatibility-patterns.md` (semantic hazard classes).