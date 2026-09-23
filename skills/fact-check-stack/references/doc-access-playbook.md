# Doc Access Playbook: Structured Endpoints & Anti-Patterns

This guide shows agents how to fetch pinned-version documentation for popular Python packages without using browser automation or unversioned endpoints.

## Golden Rules

1. **Always use a version-specific URL.** Never `latest/`, `main/`, or `/docs/` without a version fragment.
2. **Prefer structured endpoints** (API, raw files, inventory) over HTML rendering.
3. **Validate the URL before fetching.** Cross-reference with the official package repo.
4. **Cache the result.** Include retrieval timestamp and a local path reference.
5. **If a URL changes structure between versions, document it.** Some older packages have completely different doc locations.

---

## Python Package Ecosystems

### PyPI Metadata API (Universal)

Fastest way to get version info, dependencies, and doc URL:

```
GET https://pypi.org/pypi/{package}/{version}/json

Response fields of interest:
  - info.version
  - info.home_page (project homepage, often links to docs)
  - info.docs_url (if filled in; unreliable but a starting point)
  - info.requires_python
  - info.requires_dist (dependencies with version specs)
  - urls[].filename (wheels, indicates supported platforms)
```

**Example:**
```
curl -s https://pypi.org/pypi/sqlalchemy/2.0.36/json | \
  jq '.info | {version, requires_python, requires_dist, home_page, project_urls}'
```

**Use case:** Confirm version exists, extract doc URL, check Python compatibility before diving into docs.

---

### Sphinx-Documented Packages (objects.inv)

Most Python packages with official docs use Sphinx. The `objects.inv` file is a machine-readable inventory of all documented symbols, cross-referenced with anchors. **Because it is hosted remotely, it is the preferred way to verify symbol existence *before* installing a package.**

**Location pattern:**
```
{docs_base}/objects.inv
```

**Example:**
```
https://docs.sqlalchemy.org/20/objects.inv
https://docs.pydantic.dev/2.5/objects.inv
https://django-docs.readthedocs.io/en/4.2/objects.inv
```

**What it contains:** Every documented class, function, method, attribute, indexed by name and type. Includes anchors for direct linking.

#### Agent Tooling: Using probe_objects_inv.py

Use `scripts/probe_objects_inv.py` to verify symbol existence from a remote `objects.inv` file **without installing the target package**. This is the recommended pre-installation method.

```bash
# Verify a method exists
python scripts/probe_objects_inv.py \
    --url https://docs.sqlalchemy.org/20/objects.inv \
    --symbol AsyncSession.begin_nested

# Filter by domain and role for precise results
python scripts/probe_objects_inv.py \
    --url https://docs.pydantic.dev/2.9/objects.inv \
    --symbol BaseModel.model_validate_json \
    --domain py --role method --json

# If not found, the output lists similar symbols to help resolve naming ambiguity
```

**Output (human-readable):**
```
✓ VERIFIED  AsyncSession.begin_nested
  Domain/Role: py:method
  URL:         orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.AsyncSession.begin_nested
```

**Output (--json, for ledger integration):**
```json
{
  "exists": true,
  "verdict": "VERIFIED",
  "symbol": "AsyncSession.begin_nested",
  "domain": "py",
  "role": "method",
  "url": "orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.AsyncSession.begin_nested",
  "domain_type": "py:method",
  "similar": []
}
```

**Anti-pattern:** Don't use `fetch_doc.py` to check symbol existence \u2014 it fetches raw HTML. Don't use `probe_api.py` if the package isn't installed yet. Use `probe_objects_inv.py` first; fall back to `probe_api.py` only if the package is already in the venv.


---

### Symbol Verification: Live Probe (probe_api.py)

If a package is already installed, or if `objects.inv` is unavailable/inconclusive, use **live introspection** via `probe_api.py`. This uses Python's `importlib` and `inspect` on the actual installed package — Tier-0 ground truth.

**Prerequisite:** The package must be installed in the active venv (guaranteed by `uv sync` from `uv.lock`).

**Usage:**
```bash
# Verify a symbol exists
python scripts/probe_api.py --package sqlalchemy --symbol "ext.asyncio.AsyncSession.begin_nested"

# Get JSON output (for ledger)
python scripts/probe_api.py --package pydantic --symbol "BaseModel.model_validate_json" --json

# Probe a class to see public methods
python scripts/probe_api.py --package fastapi --symbol "FastAPI"
```

**What it returns:**
- `verdict: VERIFIED` — symbol exists, includes type, signature, docstring preview, source file
- `verdict: UNSUPPORTED` — symbol doesn't exist; includes which part of the path failed
- `verdict: UNSUPPORTED` — package not installed or not importable

**Anti-pattern:** Do not use `fetch_doc.py` to check symbol existence. Use `probe_api.py` for symbol probing and `fetch_doc.py` only for fetching documentation passages for context.

---

### Raw GitHub Docs (Markdown/RST at Tag)

For docs hosted on GitHub or buildable from source:

```
{repo_raw_url}/{tag}/docs/path/to/file.md
OR
{repo_raw_url}/{tag}/path/to/file.rst
```

**Example:**
```
https://raw.githubusercontent.com/sqlalchemy/sqlalchemy/rel_2_0_36/docs/build/orm/extensions/asyncio.rst
https://raw.githubusercontent.com/pydantic/pydantic/v2.5.0/docs/docs.md
```

**Advantages:**
- No rendering; plain text. Parseable with simple regex or markdown libraries.
- No JavaScript, no nav chrome — 10x lower token cost than rendered HTML.
- Exact version: the tag guarantees you're reading the right revision.

**How to find the docs path:**
1. Visit the repo's main branch, locate `docs/` or `documentation/`.
2. Note the structure: `docs/source/`, `docs/build/`, etc.
3. Swap `main` for your tag and fetch raw.

**Example discovery:**
```
https://github.com/sqlalchemy/sqlalchemy/blob/main/docs/build/orm/extensions/asyncio.rst
→ https://raw.githubusercontent.com/sqlalchemy/sqlalchemy/rel_2_0_36/docs/build/orm/extensions/asyncio.rst
```

**Anti-pattern:** Don't use `master` or `main` branch. Always use the release tag.

---

### HTML Docs with Versioned URLs

Many projects have docs hosted on their own domain with versioned paths:

```
https://docs.{package}.org/{version}/path/to/page.html
https://docs.{package}.dev/{version}/path/to/page.html
https://{package}.readthedocs.io/en/{version}/path/to/page.html
```

**Examples:**
- SQLAlchemy: `https://docs.sqlalchemy.org/20/orm/extensions/asyncio.html`
- Pydantic: `https://docs.pydantic.dev/2.5/api/base_model/`
- FastAPI: `https://fastapi.tiangolo.com/tutorial/first-steps/` (single version; check GitHub releases for versioning)
- Django: `https://docs.djangoproject.com/en/4.2/...` (major.minor versioning)
- Flask: `https://flask.palletsprojects.com/en/3.0/...`

**How to find the version URL:**
1. Check the project's official docs homepage.
2. Look for a version selector (dropdown, sidebar link to "other versions").
3. If it exists, construct the URL pattern: `{base}/{major}.{minor}/path`.
4. Validate by checking if `/objects.inv` exists at that base.

**Fetching HTML as plain text:**
- Use a tool like `html2text` or parse with `BeautifulSoup` to extract body text.
- Focus on the main content div, stripping navigation and ads.
- Result: 20–30% of the raw HTML size, semantic structure preserved.

**Anti-pattern:** Don't assume all versions exist. Older minor versions may have been deprecated and removed. Check the version selector first.

---

### ReadTheDocs-Hosted Projects

Many projects use ReadTheDocs (`*.readthedocs.io`).

**Version discovery:**
```
GET https://{project}.readthedocs.io/en/
  → Lists available versions in a dropdown or HTML list
GET https://{project}.readthedocs.io/json/
  → API endpoint that returns version metadata (not all RTD instances)
```

**Versioned URL pattern:**
```
https://{project}.readthedocs.io/en/{version}/page/path.html
```

**Example:**
```
https://django-docs.readthedocs.io/en/4.2/topics/async/
https://sqlalchemy.readthedocs.io/en/rel_2_0_36/orm/asyncio.html
```

**objects.inv location:**
```
https://{project}.readthedocs.io/en/{version}/objects.inv
```

**Anti-pattern:** Version names on RTD are not always `major.minor`. Some use `rel_{major}_{minor}_{patch}`, others use `latest-stable`. Check the version list first.

---

## Platform-Specific Recipes

### FastAPI

- **Docs:** `https://fastapi.tiangolo.com/` (single version; versioning by GitHub releases)
- **Discovery:** No object.inv. Use GitHub repo raw docs.
  ```
  https://raw.githubusercontent.com/tiangolo/fastapi/{tag}/docs/src/...
  ```
- **Fallback:** Query GitHub API for issue/discussion mentions of the feature.

### Django

- **Docs:** `https://docs.djangoproject.com/en/{major}.{minor}/...`
- **Version list:** https://docs.djangoproject.com/en/
- **objects.inv:** https://docs.djangoproject.com/en/{major}.{minor}/objects.inv
- **Example:** https://docs.djangoproject.com/en/4.2/topics/async/

### SQLAlchemy

- **Docs:** `https://docs.sqlalchemy.org/{major}.{minor}/...`
- **Version list:** https://docs.sqlalchemy.org/ (dropdown in top nav)
- **objects.inv:** https://docs.sqlalchemy.org/{major}.{minor}/objects.inv
- **Example:** https://docs.sqlalchemy.org/20/orm/extensions/asyncio.html
- **Note:** SQLAlchemy tags use `rel_{major}_{minor}_{patch}` format on GitHub.

### Pydantic

- **Docs:** `https://docs.pydantic.dev/{major}.{minor}/...` (recent versions)
- **Old versions:** `https://docs.pydantic.dev/latest/` (for 1.x, check GitHub raw)
- **objects.inv:** https://docs.pydantic.dev/{major}.{minor}/objects.inv
- **Example:** https://docs.pydantic.dev/2.5/api/base_model/

### Requests

- **Docs:** `https://requests.readthedocs.io/en/{version}/...`
- **Versions:** https://requests.readthedocs.io/en/ (see dropdown)
- **objects.inv:** https://requests.readthedocs.io/en/{version}/objects.inv
- **Note:** Requests is stable; older versions often still have docs.

---

## Special Cases: No Official Docs

For small, unmaintained, or minimalist packages:

### Option 1: Source Code Introspection (Tier-0 Ground Truth)

```python
import importlib
import inspect

# Install the exact version
# pip install package==version

module = importlib.import_module('package_name')
cls = getattr(module, 'ClassName')

# Get signature
sig = inspect.signature(cls.method_name)
print(sig)

# Get docstring
print(cls.method_name.__doc__)

# Get source file location
print(inspect.getfile(cls.method_name))
```

This is Tier-0 evidence. If the symbol is importable and has a signature, it exists. If the docstring exists, cite it.

### Option 2: GitHub Repo README

```
https://raw.githubusercontent.com/{owner}/{repo}/{tag}/README.md
```

Extract usage examples and API overview. Treat as Tier-1 (author-written, but not official docs).

### Option 3: Wheel Metadata

```
pip index versions package==version  # Lists available wheels
pip download package==version --no-binary :all: --no-deps
# Unpack .tar.gz, extract PKG-INFO, check METADATA fields
```

Wheel METADATA includes dependencies and version constraints. Can answer "does this wheel support Python 3.13?" without reading docs.

---

## Cache Strategy

After fetching, store locally:

```
.fact-check/cache/{claim_id}_{source_slug}_{version}.txt
```

**Example:**
```
.fact-check/cache/c007_sq_asyncsession_20.txt
.fact-check/cache/c012_pydantic_basemodel_25.txt
.fact-check/cache/c015_django_async_42.txt
```

**Content format:**
```
METADATA
--------
source_url: https://docs.sqlalchemy.org/20/orm/extensions/asyncio.html
retrieved: 2026-09-22T14:30:00Z
http_status: 200
content_type: text/html (converted to markdown)

CONTENT
-------
[Fetched and normalized content]

RELEVANCE_NOTE
--------------
[What part of this answers the claim?]
```

**Benefits:**
- Immutable audit trail. Reports are reproducible and diffable.
- Survives version updates. If the docs change next month, your report still cites what you saw today.
- Reduces redundant fetches. Agent sees cache hit and reuses result.

---

## Anti-Patterns (Do NOT Do)

1. **Never use `latest/` or `main/` branch docs.**
   - ❌ `https://docs.sqlalchemy.org/latest/...`
   - ✓ `https://docs.sqlalchemy.org/20/...`

2. **Never guess a URL.**
   - ❌ "I assume the docs are at `https://mypackage.readthedocs.io/en/{version}/`"
   - ✓ Query the version list, validate with `objects.inv`, then fetch.

3. **Never use rendered HTML when raw is available.**
   - ❌ Copy-pasting from a browser-rendered page.
   - ✓ Fetch raw markdown/rst from GitHub.

4. **Never assume `objects.inv` exists without checking.**
   - ❌ Assume every Sphinx site has it.
   - ✓ Probe for 404; fall back to sitemap or HTML if missing.

5. **Never forget the version in citations.**
   - ❌ "Docs say this feature exists" (which version?).
   - ✓ "Docs at {url} version {major.minor} say this feature exists."

6. **Never cite a page that requires authentication or JavaScript rendering.**
   - ❌ Fetching docs that redirect through a paywall or CDN load.
   - ✓ Official, public, static docs only.

7. **Never rely on a single source for load-bearing claims.**
   - ❌ Cite one blog post for a critical architectural decision.
   - ✓ Cite Tier-0 official docs, then cross-reference with Tier-1 maintainer statement or Tier-2 community consensus.

---

## Implementation Checklist for Agents

Before fetching a document:

- [ ] Is the URL versioned? (Contains major.minor, tag name, or version parameter)
- [ ] Is it from an official source? (Maintainer repo, official docs domain, PyPI, or GitHub)
- [ ] Do I have a cache hit? (Check `.fact-check/cache/` for same claim_id and version)
- [ ] Can I use a structured endpoint first? (PyPI JSON, objects.inv, GitHub tree API)
- [ ] If HTML, can I convert to plain text or extract the main content? (html2text, BeautifulSoup)
- [ ] Will I cache this result? (Prepare the cache file path)
- [ ] Can I validate the HTTP status and content type? (200 OK, text/html or text/plain)

---

## Tools & Libraries

### Python

**Built-in (stdlib):**
- `urllib.request` — Fetch HTTP resources.
- `json` — Parse PyPI JSON API.
- `re` — Extract anchors and version from URLs.

**Lightweight optional:**
- `html2text` — Convert HTML to markdown.
- `BeautifulSoup4` — Parse and extract main content from HTML.

### Command-line

```bash
# Verify a symbol in installed package
python scripts/probe_api.py --package sqlalchemy --symbol "ext.asyncio.AsyncSession.begin_nested"

# Full JSON output for ledger
python scripts/probe_api.py --package pydantic --symbol "BaseModel.model_validate_json" --json

# Raw GitHub fetch
curl -s https://raw.githubusercontent.com/sqlalchemy/sqlalchemy/rel_2_0_36/docs/build/orm/extensions/asyncio.rst

# PyPI metadata
curl -s https://pypi.org/pypi/sqlalchemy/2.0.36/json | jq .
```

---

## Glossary

| Term | Definition |
|------|-----------|
| **Version-specific URL** | A URL that includes the major.minor (or patch) version and will not redirect to a newer version. |
| **Tier-0 source** | Official documentation, source code at release tag, or structured APIs (PyPI JSON, `objects.inv`, `inspect` on installed source). |
| **objects.inv** | Sphinx documentation inventory; machine-readable index of symbols and anchors. Preferred pre-installation source. |
| **Live probe** | Running `probe_api.py` to introspect a symbol in an installed package using Python's `inspect` module. Tier-0 ground truth. |
| **Anchor** | Fragment identifier in a URL (e.g., `#sqlalchemy.ext.asyncio.AsyncSession.begin_nested`). |
| **Cache hit** | A previously fetched document already stored locally; reuse instead of re-fetching. |
| **Staleness** | A doc or source that predates the target package release; unreliable evidence for that version. |

