# Compatibility Patterns: Hazard Classes & Probes

When multiple packages interact, certain patterns reliably cause problems. This catalog describes each hazard class, why it matters, how to detect it, and what evidence to look for.

## How to Read This File

Each hazard section contains **two distinct types of code blocks** — do not confuse them:

| Block heading | Intent | Machine-readable? |
|---|---|---|
| **Detection Probe** | Code patterns to *search for in the ADR or target codebase* — signs the hazard may be present. | ✅ Use as a search pattern / grep target. |
| **Probe Script** | Illustrative template showing reasoning logic. **Not an executable probe** — uses hardcoded lookup dicts, not live package introspection. | ⚠️ Use as a reasoning template or adapt into a real script. |

For **executable** symbol and API probes, use the scripts in `scripts/`:
- `scripts/probe_objects_inv.py` — pre-installation: query remote Sphinx `objects.inv`.
- `scripts/probe_api.py` — post-installation: live import + `inspect` on installed packages.

For **version and dependency conflict detection**, delegate to `uv lock --all-platforms` (see `references/uv-integration.md`). Do not re-implement what uv already does.

---
## 1. Async/Sync Boundary Violations

### Hazard Description

A sync context (e.g., Flask request handler, Django ORM query, ThreadPoolExecutor task) tries to call an async function or library without a running event loop.

**Why it breaks:**
- Async functions require `asyncio.run()` or an active event loop to execute.
- Mixing sync and async code in the same stack frame causes deadlocks or "RuntimeError: no running event loop."

### Common Instances

| A (Sync) | B (Async) | Problem |
|----------|-----------|---------|
| Flask request handler | asyncpg query | `asyncpg` can't run in sync context; need async handler. |
| Django ORM transaction | SQLAlchemy async session | Sync ORM doesn't support async sub-contexts. |
| Celery task (sync by default) | httpx AsyncClient | Can't make async HTTP call in sync Celery task. |
| pytest fixture (sync) | async API probe | Fixture doesn't have event loop; test fails. |

### Detection Probe

**Code pattern to look for:**
```python
# BAD: Sync calling async without bridge
def sync_handler():
    result = await async_function()  # SyntaxError if not in async function

# BAD: Async function called from sync without asyncio.run()
def sync_handler():
    asyncio_lib.run(async_function())  # This is the workaround, but often forgotten
```

**Verification questions:**
1. Does package A provide a sync interface to package B's async API? (e.g., SQLAlchemy `create_engine` for SQLAlchemy async)
2. If not, is there a bridge library? (e.g., `starlette.concurrency.run_in_threadpool`)
3. Does the framework document async handler support? (e.g., FastAPI has async route handlers; Django added async views in 3.1)

### Evidence Tier-0 Sources

- Framework docs: "Async Views" in Django docs, "Route Handlers" in FastAPI docs.
- Library docs: "Sync API" vs. "Async API" sections (SQLAlchemy has both).
- Type hints: `async def` in function signature = requires async context.

### Evidence Tier-2 Sources

- Stack Overflow: "How to use asyncpg in a Flask app?" (will reveal the mismatch).
- GitHub issues: "RuntimeError: no running event loop" + the library combo.

### Probe Script

```python
# ILLUSTRATIVE PATTERN — not an executable probe.
# This is a reasoning template showing what to look for.
# For real symbol existence checks, use scripts/probe_objects_inv.py (pre-install)
# or scripts/probe_api.py (post-install).
import inspect

def check_async_mismatch(sync_caller_module, async_callee):
    """
    Check if a sync function tries to call an async function.
    
    Args:
        sync_caller_module: Module where the sync function is defined
        async_callee: The async function/class being called
    
    Returns:
        bool: True if mismatch detected
    """
    # Check if async_callee is actually async
    if inspect.iscoroutinefunction(async_callee) or \
       inspect.isasyncgenfunction(async_callee):
        # Check if sync_caller_module has any sync-only imports
        # that would prevent async usage
        return True
    return False

# Example
import asyncpg
from flask import Flask

app = Flask(__name__)

# Probe: Does Flask route handler allow async?
@app.route('/test')
async def test_route():  # Flask doesn't natively support async handlers
    async with asyncpg.create_pool() as pool:
        pass

# Result: Flask doesn't support async route handlers natively.
# Verdict: INCOMPATIBLE. Workaround: Use Quart or add async support.
```

### Mitigation Strategies

1. **Use a framework that supports async natively** (FastAPI, Quart, async Django views).
2. **Wrap async in a sync bridge** (e.g., `asyncio.run()`, thread pool executor).
3. **Pin a wrapper library** that bridges the two (e.g., `SQLAlchemy.sync_session_factory` for sync-to-async delegation).

---

## 2. Session/Context Lifecycle Mismatches

### Hazard Description

Two libraries manage state (session, transaction, context) with different lifecycles, and they can't coexist in the same scope.

**Why it breaks:**
- ORM session lifetime is scoped to a request, transaction, or explicit context.
- If another library expects to own the same session or context, both will try to close/commit it.
- Results in "session already closed," double-commit, or orphaned transactions.

### Common Instances

| Library A | Library B | Mismatch |
|-----------|-----------|----------|
| SQLAlchemy session (request-scoped) | Celery task (job-scoped) | Task outlives request; session is closed. |
| Django ORM (transaction per request) | Huey task queue (custom scopes) | Task runs outside request; can't access ORM. |
| asyncpg pool (event-loop-scoped) | Multiple concurrent tasks (share one pool) | Pool state is per-loop; sharing across threads breaks. |

### Detection Probe

**Code pattern to look for:**
```python
# BAD: Session created in request handler, used in background task
@app.route('/create')
def create(db: Session):
    task.delay(db)  # Session passed to task running in another process/loop

# GOOD: Task creates its own session
@celery_app.task
def process():
    with SessionLocal() as db:
        # Task owns the session lifecycle
        pass
```

**Verification questions:**
1. Who owns the lifecycle? (Is one library responsible for creation/destruction?)
2. Can both libraries coexist in the same scope? (Request, transaction, async task, thread)
3. Does one library's scope outlive the other's?

### Evidence Tier-0 Sources

- SQLAlchemy docs on "Scoped Session" and "session.begin_nested()" for nesting.
- Django docs on "Database Access in Asynchronous Code" (scope warnings).
- Celery docs on "Using SQLAlchemy" (explains session passing vs. recreation).

### Evidence Tier-2 Sources

- Stack Overflow: "SQLAlchemy session closed when used in Celery task."
- GitHub issues: "asyncpg pool not thread-safe" or "Huey task can't access Django ORM."

### Probe Script

```python
# ILLUSTRATIVE PATTERN — not an executable probe.
# This template shows the lifecycle reasoning; it uses hardcoded scope labels,
# not live package introspection. Adapt for your specific library pair.
def check_lifecycle_mismatch(lib_a, lib_b, scope_a, scope_b):
    """
    Check if two libraries' lifecycles conflict.
    
    Args:
        lib_a, lib_b: Library names
        scope_a, scope_b: Scope where each library manages state
                         (request, task, transaction, event_loop, thread, etc.)
    
    Returns:
        str: Mismatch type or "COMPATIBLE"
    """
    lifecycle_hierarchy = {
        'process': 0,
        'thread': 1,
        'event_loop': 2,
        'task': 3,
        'transaction': 4,
        'request': 5,
    }
    
    if lifecycle_hierarchy[scope_a] != lifecycle_hierarchy[scope_b]:
        return f"SCOPE_MISMATCH: {lib_a} at {scope_a}, {lib_b} at {scope_b}"
    
    return "COMPATIBLE"

# Example
print(check_lifecycle_mismatch(
    'SQLAlchemy', 'Celery',
    'request', 'task'
))
# Result: SCOPE_MISMATCH: SQLAlchemy at request, Celery at task
```

### Mitigation Strategies

1. **Align scopes.** Make both libraries share the same lifecycle (e.g., task creates and owns the session).
2. **Use a connection pool.** Let both libraries draw from a shared, thread-safe pool (e.g., asyncpg pool).
3. **Escalate session ownership.** Pass a session factory, not a session instance, to the second library.

---

## 3. Event Loop Ownership Conflicts

### Hazard Description

Two libraries or frameworks each expect to own the asyncio event loop, leading to conflicts when both are used in the same process.

**Why it breaks:**
- `asyncio.run()` creates a new event loop; running it twice in the same process fails.
- If library A runs the loop and library B tries to start its own, you get "RuntimeError: asyncio.run() cannot be called from a running event loop."
- Common with async web frameworks (FastAPI, Starlette) + async client libraries + test runners.

### Common Instances

| A (Controls Loop) | B (Wants to Control Loop) | Problem |
|-------------------|--------------------------|---------|
| FastAPI (uvicorn) | pytest-asyncio (test runner) | Both try to manage event loop; fixtures conflict. |
| asyncio.run() in main | httpx.AsyncClient in library | Library can't create its own loop inside running loop. |
| Celery worker (has event loop) | Async task function | Task function tries to await; conflict with worker's loop. |

### Detection Probe

**Code pattern to look for:**
```python
# BAD: Two asyncio.run() calls in the same process
asyncio.run(main())  # First call
asyncio.run(other_main())  # RuntimeError: cannot be called from running loop

# BAD: Nested event loop starts
async def outer():
    async def inner():
        pass
    asyncio.run(inner())  # RuntimeError: already inside a loop

# GOOD: Single event loop owner, all tasks added to it
async def main():
    await task_a()
    await task_b()
    await task_c()
```

**Verification questions:**
1. How does library A manage the event loop? (Owns it, shares it, or agnostic?)
2. How does library B expect to use the event loop? (Create its own, use existing, or agnostic?)
3. Are both running in the same process/thread?

### Evidence Tier-0 Sources

- asyncio docs: "asyncio.run()" and "Getting the Running Loop."
- FastAPI docs: "Running Applications" (shows single event loop per process).
- pytest-asyncio docs: Fixture scope and event loop management.

### Evidence Tier-2 Sources

- Stack Overflow: "RuntimeError: asyncio.run() cannot be called from a running event loop."
- GitHub issues: Library A + Library B + test runner = event loop conflict.

### Probe Script

```python
# ILLUSTRATIVE PATTERN — not an executable probe.
# This template shows the event-loop model reasoning using a hardcoded dict.
# Actual detection requires reading each library's documentation.
import asyncio
import inspect

def check_event_loop_conflict(lib_a, lib_b):
    """
    Check if two libraries have conflicting event loop ownership models.
    
    Args:
        lib_a, lib_b: Library/framework names
    
    Returns:
        str: Conflict type or "COMPATIBLE"
    """
    loop_models = {
        'FastAPI': 'owned_by_framework',
        'asyncio': 'owned_by_user_run',
        'asyncpg': 'agnostic',
        'httpx': 'agnostic',
        'pytest-asyncio': 'owned_by_runner',
    }
    
    model_a = loop_models.get(lib_a, 'unknown')
    model_b = loop_models.get(lib_b, 'unknown')
    
    if model_a == 'owned_by_framework' and model_b == 'owned_by_framework':
        return "CONFLICT: Both want to own event loop."
    if model_a == 'owned_by_user_run' and model_b == 'owned_by_runner':
        return "CONFLICT: Nested asyncio.run() attempted."
    
    return "COMPATIBLE"

# Example
print(check_event_loop_conflict('FastAPI', 'pytest-asyncio'))
# Result: COMPATIBLE (FastAPI's loop is managed by uvicorn; pytest-asyncio is aware)
```

### Mitigation Strategies

1. **Single event loop owner.** Designate one library to own the loop (e.g., FastAPI/uvicorn in production, pytest-asyncio in tests).
2. **Explicit loop passing.** Pass the running loop to libraries that need it (e.g., `asyncpg.create_pool()`).
3. **Async context management.** Use `async with` for libraries that support explicit lifecycle management.

---

## 4. Serialization Contract Mismatches

### Hazard Description

Two libraries expect different serialization formats or contracts for the same data, leading to type errors or silent data corruption.

**Why it breaks:**
- Library A (e.g., Pydantic) validates and serializes to JSON.
- Library B (e.g., Redis) expects a different format (e.g., pickle, MessagePack).
- If they don't agree on the format, deserialization fails or silently creates wrong objects.

### Common Instances

| A (Serializer) | B (Consumer) | Mismatch |
|---|---|---|
| Pydantic JSON schema | DynamoDB item serializer | Schema validation vs. DynamoDB AttributeValue format. |
| FastAPI response JSON | Redis cache (pickle) | FastAPI returns JSON; Redis stores pickle; deserialization fails. |
| SQLAlchemy ORM (Python objects) | Celery task arg (pickle) | Pickle may fail on custom ORM classes. |

### Detection Probe

**Code pattern to look for:**
```python
# BAD: Inconsistent serialization
data = pydantic_model.model_dump_json()  # JSON string
redis.set('key', data)  # Stored as string
loaded = json.loads(redis.get('key'))  # Loaded correctly
obj = MyModel(**loaded)  # May fail if schema changed

# GOOD: Explicit serialization contract
data = pydantic_model.model_dump()  # Python dict
serialized = orjson.dumps(data)  # JSON bytes, fast
redis.set('key', serialized)
loaded = orjson.loads(redis.get('key'))
obj = MyModel(**loaded)  # Schema and format are explicit
```

**Verification questions:**
1. What serialization format does library A produce? (JSON, pickle, MessagePack, protobuf)
2. What serialization format does library B expect? (Same as A?)
3. Is there a schema evolution path? (Versioning, backward compatibility)

### Evidence Tier-0 Sources

- Pydantic docs: `model_dump()` vs. `model_dump_json()` contracts.
- Redis docs: Data types and serialization (strings, hashes, etc.).
- Celery docs: Serialization options (JSON, pickle, msgpack).

### Evidence Tier-2 Sources

- Stack Overflow: "Pydantic model to Redis," "Celery serialization error."
- GitHub issues: "Pickle fails on ORM model in Celery task."

### Probe Script

```python
# ILLUSTRATIVE PATTERN — not an executable probe.
# This template shows serialization format reasoning using a hardcoded dict.
# Actual detection requires reading each library's serialization docs.
def check_serialization_contract(producer, consumer):
    """
    Check if producer and consumer serialization formats match.
    
    Args:
        producer: Library name (e.g., 'Pydantic')
        consumer: Library name (e.g., 'Redis')
    
    Returns:
        str: Compatibility note or error
    """
    formats = {
        'Pydantic': ['json', 'python_dict'],
        'Redis': ['string', 'bytes'],
        'Celery': ['json', 'pickle', 'msgpack'],
        'DynamoDB': ['attribute_value'],
    }
    
    prod_formats = formats.get(producer, [])
    cons_formats = formats.get(consumer, [])
    
    common = set(prod_formats) & set(cons_formats)
    if common:
        return f"COMPATIBLE: Both support {common}"
    else:
        return f"INCOMPATIBLE: {producer} produces {prod_formats}, {consumer} expects {cons_formats}"

# Example
print(check_serialization_contract('Pydantic', 'DynamoDB'))
# Result: INCOMPATIBLE: Pydantic produces ['json', 'python_dict'], DynamoDB expects ['attribute_value']
```

### Mitigation Strategies

1. **Align formats.** Use a common serialization format (JSON for most use cases).
2. **Explicit converters.** Write a serialization layer that converts between formats.
3. **Version your schema.** Include version metadata in serialized data for backward compatibility.

---

## 5. Dependency Conflicts & Version Constraints

### Hazard Description

Two libraries require different versions of a shared transitive dependency, and their constraints can't be satisfied simultaneously.

**Why it breaks:**
- Library A needs `shared_lib>=2.0`.
- Library B needs `shared_lib<2.0`.
- Installer can't resolve: either A or B fails.

### Common Instances

| A | B | Conflict |
|---|---|----------|
| numpy>=1.20 | scipy<1.10 (needs numpy<1.20) | Transitive conflict. |
| pydantic-core>=2.0 | old_lib (needs pydantic-core<2.0) | Core lib mismatch. |
| protobuf>=4.0 | some_grpc_version (needs protobuf<4.0) | Framework version bound. |

### Detection Probe

### Delegation: `uv lock --all-platforms`

> **This hazard class is fully handled by `uv` in Phase 1. Do not re-implement.**

`uv lock --all-platforms` runs the PubGrub solver, which handles transitive dependency constraints across all platform markers. If a conflict exists, it will be reported as a resolution error at lock time — before any package is installed.

**If `uv lock` succeeds:** versions are co-installable. Proceed.
**If `uv lock` fails:** report `REVISE-ADR` and include the resolver error message as the evidence.

```bash
# Phase 1 command (run this, not pip --dry-run)
uv lock --all-platforms

# On failure, the output will contain the conflict:
# error: Because package-a==1.0 depends on shared-lib>=2.0
#   and package-b==1.0 depends on shared-lib<2.0,
#   we can conclude that package-a==1.0 and package-b==1.0 are incompatible.
```

See `references/uv-integration.md` for lockfile parsing and Phase 1 workflow.

### Evidence Tier-0 Sources

- PyPI JSON API: `requires_dist` field lists all dependency constraints.
- Lockfile (poetry.lock, requirements.txt): Explicit versions.

### Evidence Tier-2 Sources

- GitHub issues: "Dependency conflict with X and Y."
- Dependency resolver error messages: "pip's dependency resolver..."

### Mitigation Strategies

1. **Pin earlier version.** Use a version of A or B that relaxes the constraint.
2. **Wait for releases.** One library may update to support newer transitive deps soon.
3. **Find a replacement.** Use an alternative library that doesn't have the conflict.

---

## 6. Python Version Incompatibility

### Hazard Description

One or more libraries require Python versions that don't overlap.

**Why it breaks:**
- Library A requires `python>=3.11`.
- Library B requires `python<3.11`.
- Only one can be installed in the same environment.

### Detection Probe

### Delegation: `uv lock --all-platforms`

> **This hazard class is fully handled by `uv` in Phase 1. Do not re-implement.**

`uv lock` automatically checks `requires_python` for every package in the dependency graph and rejects combinations where the Python version ranges don't intersect. The result is surfaced in the lock failure message.

```bash
# Phase 1 command — uv checks Python version compat automatically
uv lock --all-platforms

# On failure, the message will include:
# error: The requested Python version 3.10 is not supported by package-a>=2.0
#   (which requires Python>=3.11)
```

If you need to verify `requires_python` for a specific package before running `uv lock`, use the PyPI JSON API:

```bash
curl -s https://pypi.org/pypi/asyncpg/0.29.0/json | jq '.info.requires_python'
# Output: ">=3.8.0"
```

See `references/uv-integration.md` for lockfile parsing and Phase 1 workflow.

### Evidence Tier-0 Sources

- PyPI JSON API: `requires_python` field.
- Official docs: Python version support matrix.

### Mitigation Strategies

1. **Upgrade/downgrade one package.** Find a version that supports your Python version.
2. **Use conditional dependencies.** Pin different versions based on Python version (e.g., in `setup.py`).
3. **Update Python.** If all packages require Python 3.12+ and you're on 3.10, upgrade Python.

---

## Hazard Class Checklist

When reviewing a multi-package ADR, systematically check for these hazard classes:

- [ ] **Async/Sync boundary:** Are there sync-to-async or async-to-sync calls? Does the framework support them?
- [ ] **Session lifecycle:** Do multiple libraries manage state that outlive each other?
- [ ] **Event loop ownership:** Can two async libraries coexist in the same process?
- [ ] **Serialization contract:** Do the libraries agree on data format (JSON, pickle, etc.)?
- [ ] **Version conflicts:** Do transitive dependencies have non-overlapping constraints?
- [ ] **Python version:** Do all packages support the target Python version?

If any hazard is detected, flag it as a load-bearing or contained claim and escalate to Tier-2 verification or mitigation design.

