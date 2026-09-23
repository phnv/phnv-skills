# uv Integration: Phase 1 Cheat-Sheet

fact-check-stack delegates **version resolution and co-installability checks** to [uv](https://docs.astral.sh/uv/). This is a quick-reference card for agents: the key commands and exactly where their outputs feed into the skill's phases.

## Quick Decision Fork

```
Do you have a uv.lock already?
│
├── YES → Skip Phase 1 entirely. Feed uv.lock into Phase 2 directly.
│          See "Parsing uv.lock" below.
│
└── NO  → Run uv lock to generate one (see "Generating a lockfile").
           Then proceed to Phase 2.
```

---

## Generating a Lockfile (Phase 1)

```bash
# Standard: resolve for all platforms (recommended for ADR review)
uv lock --all-platforms

# From a requirements file
uv pip compile requirements.in -o requirements.txt
uv lock

# Check if uv is installed
which uv || echo "Install: curl -LsSf https://astral.sh/uv/install.sh | sh"

# uv lives at ~/.local/bin/uv if installed via the official script
# Add to PATH: export PATH="$HOME/.local/bin:$PATH"
```

**Output:** `uv.lock` — a fully-resolved, cross-platform lockfile. This is the ground truth for Phase 2 onward.

---

## Extracting Pinned Versions (feed into Phase 2)

Agents need a flat `{ package: version }` map to extract claims from. Parse `uv.lock`:

```bash
# List all pinned packages (name + version)
grep -A1 '^\[\[package\]\]' uv.lock | grep -E '^(name|version)' | paste - -

# Or with Python (stdlib):
python3 - <<'EOF'
import re, sys

with open('uv.lock') as f:
    content = f.read()

packages = {}
blocks = content.split('[[package]]')
for block in blocks[1:]:
    name = re.search(r'name\s*=\s*"([^"]+)"', block)
    version = re.search(r'version\s*=\s*"([^"]+)"', block)
    if name and version:
        packages[name.group(1)] = version.group(1)

for pkg, ver in sorted(packages.items()):
    print(f"{pkg}=={ver}")
EOF
```

Feed this map to `scripts/detect_hazards.py --uv-lock uv.lock`.

---

## Checking Co-installability (what uv gives you for free)

```bash
# Dry-run: resolve without writing lockfile; errors = conflict
uv lock --dry-run

# Check a specific set of constraints
uv pip install --dry-run "sqlalchemy==2.0.36" "asyncpg==0.29.0"

# Show what would be installed (resolution trace)
uv pip install --dry-run --verbose "fastapi==0.120.0" "pydantic==2.9.2"
```

**If this fails:** Resolution error = `REVISE-ADR`. Stop Phase 1 and report. A claim cannot be verified against a version that cannot be installed.

---

## Checking Python Version Compatibility

```bash
# Resolve against a specific Python version
uv lock --python 3.11

# List Python version constraints per package
uv pip show sqlalchemy | grep Requires-Python
```

---

## Mapping uv.lock Output → Skill Phases

| uv output | Used in | How |
|-----------|---------|-----|
| `uv.lock` (pinned versions) | Phase 2 (Claim Extraction) | Parse to get exact `package==version` for each claim subject |
| `uv lock --dry-run` result | Phase 1 gate | If error → REVISE-ADR. If OK → proceed. |
| `uv pip show <pkg>` | Phase 3 (Verify) | Get `Home-page` / `Project-URL` → input for `fetch_doc.py` |
| `uv lock --python X.Y` success/failure | Phase 4 (Cross-Ref) | Python version intersection check |
| `uv pip install --dry-run` verbose output | Phase 4 (Cross-Ref) | Transitive dep conflict check |

---

## What uv Does NOT Do (skill's unique value)

| Check | uv | detect_hazards.py / fact-check-stack |
|-------|----|---------------------------------------|
| Feature exists at version X | ✗ | ✓ (`probe_api.py` — live import + `inspect`) |
| API is deprecated/undocumented | ✗ | ✓ (`fetch_doc.py` + evidence-standards.md) |
| Async/sync boundary hazards | ✗ | ✓ (`detect_hazards.py`) |
| Session lifecycle mismatches | ✗ | ✓ (`detect_hazards.py`) |
| Real-world caveats from community | ✗ | ✓ (community-research.md + field sweep) |
| Advisory risk register + ADR amendments | ✗ | ✓ (`ledger.py`) |

---

## Troubleshooting

**`uv: command not found`**
```bash
# Install uv (Linux/macOS)
curl -LsSf https://astral.sh/uv/install.sh | sh
# Then add to PATH:
export PATH="$HOME/.local/bin:$PATH"
```

**`uv lock` fails with a resolution error**
→ Report as `REVISE-ADR` in Phase 1. Two packages in the ADR require incompatible versions of a shared dependency. Escalate to human architect.

**`uv.lock` already exists but is stale**
```bash
uv lock --upgrade   # Re-resolve to latest compatible versions
```
