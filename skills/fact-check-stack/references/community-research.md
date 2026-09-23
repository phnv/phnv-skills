# Community Research: Tier-2 Evidence Standards

Tier-2 sources are high-signal community contributions that can validate, contextualize, or flag caveats to Tier-0 documentation. They **cannot promote a claim to VERIFIED**, but they can surface real-world implementation hazards, known bugs, and workarounds that official docs don't mention.

## Trusted Sources

### Stack Overflow

**Signal indicators:**
- Answer has a green checkmark (accepted by question author).
- Answer has high upvotes (10+) relative to question date.
- Answer includes code example, explicit version mention, and date-tested statement.
- Answerer has high reputation and history of quality answers on the tag.

**Query strategy:**
```
[package-name] [version] [feature-or-problem]
site:stackoverflow.com
```

**Example:**
```
sqlalchemy asyncsession nested transactions
site:stackoverflow.com
```

**Red flags:**
- High upvotes but **posted before the feature existed.** Always check post date vs. package release date.
- Answer contradicts Tier-0 docs but has no version or date context.
- Multiple answers contradict each other; no consensus. (Escalate to human review.)
- Answer is from 5+ years ago on a rapidly-evolving package. (Likely stale.)

**Validation checklist:**
- [ ] Post date is after target package release? (If not, answer is about a different or older version.)
- [ ] Answerer explicitly states what version they tested? (Or infer from post date ± 1 month.)
- [ ] Is the code example self-contained and reproducible?
- [ ] Does it contradict Tier-0, and if so, does it explain why?

**Example extract (good):**
```
Q: "Can asyncpg connection pool be shared across coroutines?"
A: "Yes, but only within a single event loop. Tested on asyncpg==0.27.0 (Python 3.11). 
   If you try to share the same pool across threads, use a Lock."
```

**Example extract (red flag):**
```
Q: "Does FastAPI support WebSocket?"
A: "Yes! It's fully async. Posted 2019-03-15"
(Target version: fastapi==0.120.0, released 2024-11. Five-year-old answer.)
```

---

### GitHub Discussions & Issues

**Signal indicators:**
- Comment from package maintainer (look for repo owner in GitHub profile or contributor badge).
- High-upvote comment in a GitHub Discussion (✅ if marked as answer).
- Closed issue with a resolution or workaround in the final comments.
- Linked PR that documents why the issue was resolved or won't be fixed.

**Query strategy:**
```
repo:{owner}/{repo} is:issue|discussion "{feature or problem}"
```

**GitHub API query:**
```
curl -s "https://api.github.com/search/issues?q=repo:sqlalchemy/sqlalchemy+is:issue+AsyncSession+begin_nested" | jq
```

**Red flags:**
- Issue is still open, unsolved, and marked "wontfix."
- Comment is from a user with no repo affiliation. (Treat as community opinion, not authority.)
- Issue was closed > 2 major versions ago. (Feature may have changed since.)
- Linked PR is from `main` branch, not a release tag. (Feature not yet released.)

**Validation checklist:**
- [ ] Is the commenter a repo maintainer? (Check contributor status or GitHub profile.)
- [ ] Is the issue/discussion specific to the target version?
- [ ] If a fix is proposed, is it in a released version (not just main)?
- [ ] Date: is the resolution post-dated the target package release?

**Example extract (good):**
```
Issue: asyncpg#1234 "Connection pool thread-safety"
Comment from maintainer (@magicstack, 2024-06):
"The pool is designed for single-event-loop use. Sharing across threads 
requires external synchronization. See #1234 for a WorkaroundA."
(Target asyncpg==0.29.0, released 2024-05. Maintainer comment is current.)
```

---

### Official Community Forums & Mailing Lists

Examples:
- [Discuss.sqlalchemy.org](https://discuss.sqlalchemy.org)
- [Django Forum](https://forum.djangoproject.com)
- [Pydantic Discussions](https://github.com/pydantic/pydantic/discussions)
- Python mailing lists (`python-dev`, `numpy-discussion`, etc.)

**Signal indicators:**
- Post is from package maintainer or known contributor.
- Thread resolves with a clear explanation and version context.
- High engagement and quality discussion (multiple knowledgeable participants).

**Query strategy:**
```
site:{forum_domain} {package} {version} {feature}
```

**Validation checklist:**
- [ ] Is the author a known contributor or maintainer?
- [ ] Is the discussion specific to the target version?
- [ ] Is there a clear resolution, or is it speculative?

---

### High-Quality Blog Posts

Blogs by known community members, maintainers, or conference speakers carry more weight than random tutorials.

**Signal indicators:**
- Author is listed as a maintainer or core contributor on the project.
- Post is dated within 6 months of the target package release.
- Post includes version number and tested environment.
- Post links to official docs and code examples.

**Red flags:**
- Generic tutorial with no version context. (Likely stale.)
- Post contradicts official docs but doesn't explain why or when.
- Author has no repository affiliation or community recognition. (Escalate to Tier-3.)

**Examples of trusted sources:**
- Posts on `realpython.com` or `fullstackpython.com` (curated, usually reviewed).
- Blog posts by package maintainers (e.g., David Beazley on asyncio, Guido on typing).
- Conference talk write-ups by known speakers.

**Examples of untrusted sources:**
- Medium posts with sensational titles and no version context.
- Corporate marketing blogs promoting their own tool (bias).
- AI-generated tutorials without explicit author or review.

---

### Known-Bug Registries & Issue Trackers

Some packages maintain a "Known Issues" document or GitHub wiki.

**Examples:**
- Django's [Known Issues page](https://docs.djangoproject.com/en/stable/known_issues/)
- SQLAlchemy [SQLAlchemy 1.4 Deprecation Guide](https://docs.sqlalchemy.org/14/changelog/index.html)
- FastAPI [GitHub Issues with "bug" label](https://github.com/tiangolo/fastapi/issues?q=label:bug)

**Use case:** Validate that a claim's caveat is a known limitation or bug. Example:

*Claim:* "FastAPI on_event('shutdown') is available in 0.100.0"
*Tier-0 finding:* Method does not exist (UNSUPPORTED)
*Tier-2 validation:* GitHub issue #7661 "Deprecate on_event in favor of lifespan" explains the change. Confirmed.

---

## Query Strategy

### General Formula

```
{package-name} {version} {feature-or-symptom} -site:twitter.com -site:reddit.com
```

Exclude low-signal sources (Twitter, Reddit) unless explicitly seeking community opinion.

### Example Queries

**Capability question:**
```
pydantic 2.9 computed_field async support
```

**Bug report:**
```
sqlalchemy 2.0 AsyncSession transaction isolation level
```

**Integration question:**
```
fastapi 0.120 redis cache async compatibility
```

**Performance question:**
```
asyncpg connection pool vs sqlalchemy async performance benchmarks
```

### Tools

**Python script:**
```python
import urllib.parse

def build_query(package, version, feature, exclude_sites=None):
    """Generate a community search query."""
    exclude_sites = exclude_sites or ["twitter.com", "reddit.com", "medium.com"]
    base = f"{package} {version} {feature}"
    for site in exclude_sites:
        base += f" -site:{site}"
    return base

# Result: "sqlalchemy 2.0 AsyncSession -site:twitter.com -site:reddit.com"
```

**Search with GitHub API:**
```python
import json
import urllib.request

query = "repo:sqlalchemy/sqlalchemy is:issue AsyncSession begin_nested"
url = f"https://api.github.com/search/issues?q={urllib.parse.quote(query)}&sort=updated&order=desc"
response = urllib.request.urlopen(url)
results = json.load(response)
for issue in results['items'][:5]:
    print(f"{issue['number']}: {issue['title']} ({issue['updated_at']})")
```

---

## Staleness Validation

### Rule: Post Date vs. Package Release Date

A Tier-2 source is reliable only if it was written after the target package was released.

**Why:** If the post predates the package release, the author couldn't have tested it.

**Example:**
```
Target: pydantic==2.5.0 (released 2024-08-15)
Source: Blog post "Pydantic 2.5 is out!" (published 2024-08-14)
Status: STALE. Post is from before release; can't have been tested on 2.5.0.

Target: pydantic==2.5.0
Source: Stack Overflow answer (posted 2024-09-01, "tested on pydantic 2.5.0")
Status: FRESH. Posted after release; author could have tested.
```

### Rule: Feature Deprecation & Version Churn

If the target package had major changes between the post date and release, the post is unreliable.

**Example:**
```
Target: fastapi==0.120.0 (2024-11)
Source: Stack Overflow answer about on_event() (2023-06)
Check: Did on_event() exist in 0.120.0? NO (removed in 0.100.0, 2024-01)
Status: STALE & INCOMPATIBLE. Post is about a feature that no longer exists.
```

### Validation Algorithm

```python
from datetime import datetime, timedelta
import urllib.request
import json

def validate_staleness(package, target_version, post_date):
    """Check if a post is stale relative to a package version."""
    
    # Fetch package release date from PyPI
    url = f"https://pypi.org/pypi/{package}/{target_version}/json"
    response = urllib.request.urlopen(url)
    data = json.load(response)
    release_date_str = data['releases'][target_version][0]['upload_time_iso_8601']
    release_date = datetime.fromisoformat(release_date_str)
    
    # Parse post date
    post_datetime = datetime.fromisoformat(post_date)
    
    # Staleness rules
    if post_datetime < release_date:
        return "STALE: Post predates package release. Author couldn't have tested it."
    
    days_old = (datetime.now() - post_datetime).days
    if days_old > 365:
        return "POTENTIALLY_STALE: Post is >1 year old. Check for version churn."
    
    return "FRESH"

# Example
print(validate_staleness("pydantic", "2.5.0", "2024-09-01T10:30:00Z"))
# → "FRESH"
```

---

## Consensus Building (Multiple Tier-2 Sources)

If multiple Tier-2 sources confirm a finding, it carries more weight than a single source.

**Example:**
```
Claim: "Redis 5.0+ breaks with asyncio in Python 3.10 under high concurrency"

Finding 1: Stack Overflow answer (accepted, 15 upvotes)
  "Experienced this with redis==5.0.0 and Python 3.10. 
   Race condition in connection pooling. Fixed in redis==5.1.0."
  (Posted 2024-03, tested on versions mentioned)

Finding 2: GitHub issue #1234 in redis-py
  Closed by maintainer: "This was a known issue in 5.0 and fixed in 5.1.
   Update your redis dependency."
  (Closed 2024-04)

Finding 3: Real Python blog post
  "redis 5.0 asyncio compatibility matrix"
  (Posted 2024-05, version-specific, recent)

Verdict: CONSENSUS. Three independent sources confirm the caveat.
Mitigation: "Pin redis>=5.1.0 to avoid race condition in high-concurrency workloads."
```

---

## Red Flags & Dismissal Criteria

Dismiss or flag Tier-2 sources that match:

| Red Flag | Action |
|----------|--------|
| Post date < package release date | STALE; do not cite. |
| Post mentions version X but target is Y and X → Y had breaking changes | INCOMPATIBLE; do not cite. |
| Multiple sources directly contradict each other with no consensus | UNRESOLVED; note disagreement in report. Escalate to human. |
| Source is from AI chatbot or LLM (ChatGPT, Claude, etc.) without human verification | DO NOT CITE. Treat as Tier-3 and verify answer against Tier-0. |
| Answer contradicts Tier-0 docs but provides no explanation or workaround | SUSPICIOUS; investigate further. May be bug or misunderstanding. |
| Author has reputation < 100 on the platform and answer has contradictions | LOW SIGNAL; deprioritize. |
| Blog post or tutorial has no author name, date, or version context | ANONYMOUS; do not cite for evidence. |
| Stack Overflow answer is marked as disputed or downvoted heavily | LIKELY WRONG; skip. |

---

## Caveat Types & Examples

### Known Bug with Workaround

```json
{
  "type": "known_bug",
  "package": "asyncpg",
  "version_range": "0.27.0–0.28.x",
  "symptom": "Connection pool leaks file descriptors under high load",
  "discovered": "2024-03",
  "references": ["GitHub issue #1234", "SO answer #12345"],
  "workaround": "Upgrade to asyncpg>=0.29.0 or manually close pool with pool.close()",
  "tier": 2,
  "blast_radius": "contained"
}
```

### Undocumented Behavior

```json
{
  "type": "undocumented_behavior",
  "package": "sqlalchemy",
  "feature": "AsyncSession.sync_session_class attribute",
  "description": "Not in official docs but accessible. Provides access to sync session for edge cases.",
  "references": ["GitHub discussion #7890", "SO answer #54321"],
  "stability": "unofficial; may change",
  "tier": 2,
  "blast_radius": "reversible"
}
```

### Performance Caveat

```json
{
  "type": "perf_caveat",
  "package": "pydantic",
  "feature": "model_validate() with complex nested schemas",
  "description": "Official docs don't mention performance cost. Community reports show 10–30% overhead vs. direct assignment on large models.",
  "references": ["Blog post on pydantic performance", "GitHub discussion #6789"],
  "recommendation": "Benchmark on your schema before adopting in hot paths.",
  "tier": 2,
  "blast_radius": "reversible"
}
```

---

## Workflow for Field Sweep Agents

1. **Extract the unresolved claim** from Phase 3 (UNVERIFIABLE or PARTIAL).
2. **Identify hazard class** from `references/compatibility-patterns.md` if applicable.
3. **Build query** using the formula above: `package version feature`.
4. **Search Tier-2 sources in order:**
   - Stack Overflow (accepted answers first).
   - GitHub issues/discussions (maintainer comments first).
   - Official forums.
   - Trusted blogs (real python, official project blogs).
5. **Validate staleness** for each source found.
6. **Aggregate findings:**
   - If consensus (2+ sources agree), elev to mitigation/caveat entry.
   - If disagreement, note and escalate.
   - If none found and claim is load-bearing, mark UNVERIFIABLE.
7. **Stop after 5 total field-sweep claims** or **10 total Tier-2 fetches**, whichever comes first.

---

## Tools & Scripts

### Python: GitHub Search Client

```python
import json
import urllib.request
import urllib.parse

def search_github_issues(repo, query, limit=5):
    """Search GitHub issues by query."""
    q = f"repo:{repo} {query}"
    url = f"https://api.github.com/search/issues?q={urllib.parse.quote(q)}&sort=updated&order=desc&per_page={limit}"
    response = urllib.request.urlopen(url)
    return json.load(response)['items']

# Example
issues = search_github_issues("sqlalchemy/sqlalchemy", "AsyncSession begin_nested")
for issue in issues:
    print(f"{issue['number']}: {issue['title']}\n  {issue['html_url']}\n")
```

### Manual Verification Checklist

Before citing a Tier-2 source in the report:

- [ ] Post date is after or within 2 weeks of target package release?
- [ ] Author explicitly states the version they tested?
- [ ] Does the post contradict Tier-0? If yes, can I explain why (bug, deprecation, new feature)?
- [ ] Is the source from a recognized community member or maintainer?
- [ ] Can I find a second source confirming the same finding?
- [ ] Does this caveat affect the blast_radius of my claim?

