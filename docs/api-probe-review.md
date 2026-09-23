## What probe_api.py Does

It answers one question: **"Does symbol X exist in package Y version Z?"**

For example:
- "Does `sqlalchemy.AsyncSession.begin_nested()` exist in sqlalchemy 2.0.36?" → VERIFIED
- "Does `fastapi.on_event()` exist in fastapi 0.120.0?" → UNSUPPORTED (removed in 0.100.0)
- "Does `pydantic.BaseModel.model_validate_json()` exist in pydantic 2.5.0?" → VERIFIED

### Two Approaches in the Script

**Approach 1: objects.inv (Sphinx docs inventory)**
```python
# Fetch https://docs.sqlalchemy.org/20/objects.inv
# Parse the zlib-compressed binary file
# Look up "AsyncSession.begin_nested" in the inventory
# Return: "exists at URL /orm/extensions/asyncio.html#..."
```
- **Tier-0 evidence** (official documentation)
- Only works for Sphinx-documented packages
- Fragile (requires knowing docs URL structure)
- Can't handle deprecation warnings or undocumented features well

**Approach 2: Live import with inspect (ground truth)**
```python
import sqlalchemy.ext.asyncio
obj = sqlalchemy.ext.asyncio.AsyncSession
if hasattr(obj, 'begin_nested'):
    sig = inspect.signature(obj.begin_nested)
    print(f"Exists with signature: {sig}")
```
- **Tier-0 ground truth** (what actually exists in the code)
- Requires package to be installed
- Gets signature, docstring, source location
- Catches removed methods, private APIs, undocumented features

---

## Is It Still Needed? **YES, but with a caveat.**

### Why It's Critical

uv.lock solves **"what versions can coexist?"** but NOT **"does this feature actually exist in that version?"**

**Example:**
```
uv.lock says: fastapi==0.120.0 is installable
Fact-check-stack must verify: Does on_event() exist in 0.120.0?
Answer: NO. It was removed in 0.100.0.
Verdict: REFUTED → REVISE-ADR
```

**uv can't catch this.** It only knows version ranges and transitive deps. It doesn't know which methods were added/removed/deprecated between versions.

### The Real Problem With probe_api.py

The script as written is **overengineered**:

1. **objects.inv parsing is brittle.** It requires:
   - Knowing the exact docs URL structure per package (`docs.sqlalchemy.org/20/` vs `docs.sqlalchemy.org/rel_2_0_36/`)
   - Handling zlib decompression and Sphinx binary format
   - Dealing with packages that don't use Sphinx (FastAPI, for example)

2. **The live import approach is simpler and more reliable.** It just needs the package installed.

*Clarification on objects.inv:* While the brittle custom parser was removed from `probe_api.py`, `objects.inv` remains highly valuable Tier-0 evidence. Because fact-checking often happens during the planning phase *before* heavy packages are installed, IDE coding agents should query the remote `objects.inv` directly (e.g., via a `sphinx.ext.intersphinx` scratch script) rather than downloading the whole package just to probe one symbol. `probe_api.py` should be used as a fallback if the package is already installed.

---

## Refactored probe_api.py (v2.0)

Given that uv.lock already exists,evaluate and implement a simpler version:

```python
#!/usr/bin/env python3
"""
probe_api.py v2.0: Verify symbol existence in an installed package.

MUCH simpler: skip objects.inv parsing. Just test against installed code.

Usage:
    python probe_api.py --package sqlalchemy --symbol "AsyncSession.begin_nested"
    python probe_api.py --package fastapi --symbol "on_event"
"""

import json
import sys
import importlib
import inspect
from typing import Optional, Dict

def probe_symbol(package: str, symbol_path: str) -> Dict:
    """
    Check if a symbol exists in an installed package.
    
    Args:
        package: Package name (e.g., 'sqlalchemy')
        symbol_path: Dot-separated path (e.g., 'ext.asyncio.AsyncSession.begin_nested')
    
    Returns:
        Dictionary with verdict and details.
    """
    result = {
        'package': package,
        'symbol': symbol_path,
        'exists': False,
        'verdict': 'UNSUPPORTED',
        'tier': 0,  # Tier-0 ground truth: actual source code
        'details': {}
    }
    
    try:
        # Import base module
        module = importlib.import_module(package)
        result['details']['module_version'] = getattr(module, '__version__', 'unknown')
        
        # Traverse symbol path
        obj = module
        path_parts = symbol_path.split('.')
        traversed = [package]
        
        for part in path_parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
                traversed.append(part)
            else:
                # Symbol not found
                result['details']['traversed'] = '.'.join(traversed)
                result['details']['failed_at_part'] = part
                return result
        
        # Symbol exists!
        result['exists'] = True
        result['verdict'] = 'VERIFIED'
        result['details']['full_path'] = '.'.join(traversed)
        
        # Extract metadata
        result['details']['type'] = type(obj).__name__
        
        if callable(obj):
            try:
                sig = inspect.signature(obj)
                result['details']['signature'] = str(sig)
            except:
                result['details']['signature'] = '(unable to determine)'
        
        if inspect.isclass(obj):
            result['details']['is_class'] = True
            methods = [m for m in dir(obj) if not m.startswith('_')]
            result['details']['public_methods_count'] = len(methods)
        
        # Docstring
        doc = inspect.getdoc(obj)
        if doc:
            result['details']['docstring_preview'] = doc[:200]
        
        # Source location
        try:
            source_file = inspect.getfile(obj)
            result['details']['source_file'] = source_file
        except:
            pass
        
        return result
    
    except ImportError as e:
        result['verdict'] = 'IMPORT_ERROR'
        result['details']['error'] = str(e)
        result['details']['message'] = f"Package {package} not installed or not importable"
        return result
    
    except Exception as e:
        result['verdict'] = 'ERROR'
        result['details']['error'] = str(e)
        return result

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Verify symbol existence in installed package (Tier-0 ground truth)"
    )
    parser.add_argument('--package', required=True, help='Package name (e.g., sqlalchemy)')
    parser.add_argument('--symbol', required=True, help='Symbol path (e.g., ext.asyncio.AsyncSession.begin_nested)')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    
    args = parser.parse_args()
    
    result = probe_symbol(args.package, args.symbol)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Human-readable output
        print(f"{args.package}::{args.symbol}")
        print(f"  Verdict: {result['verdict']}")
        if result['exists']:
            print(f"  Type: {result['details'].get('type', 'unknown')}")
            if 'signature' in result['details']:
                print(f"  Signature: {result['details']['signature']}")
            if 'source_file' in result['details']:
                print(f"  Source: {result['details']['source_file']}")
        else:
            print(f"  Traversed: {result['details'].get('traversed', 'N/A')}")
            print(f"  Failed at: {result['details'].get('failed_at_part', 'N/A')}")
    
    sys.exit(0 if result['exists'] else 1)

if __name__ == '__main__':
    main()
```

### Why This Version is Better

| Old probe_api.py | New probe_api.py |
|---|---|
| Parse objects.inv (complex, fragile) | Just use inspect (simple, reliable) |
| Requires knowing docs URL | Only requires package installed |
| Handles Sphinx sites only | Works with any Python package |
| Can't detect undocumented APIs | Catches everything in the code |
| 150+ lines | ~80 lines |

---

## Workflow Integration (With uv)

```bash
# Step 1: uv resolves versions
uv pip compile requirements.in --output-file requirements.lock

# Step 2: Install exact versions into venv
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.lock

# Step 3: Extract claims from ADR
# C-007: "SQLAlchemy 2.0.36 supports AsyncSession.begin_nested()"

# Step 4: Verify claims with probe_api.py (against installed packages)
python probe_api.py --package sqlalchemy --symbol "ext.asyncio.AsyncSession.begin_nested"
# → Verdict: VERIFIED (symbol exists in installed sqlalchemy)

# Step 5: Verify against docs (fetch_doc.py) for additional context
python fetch_doc.py --url "https://docs.sqlalchemy.org/20/..." --claim-id C-007 --keywords "begin_nested"
# → Confirms docs support it, adds context

#DEPRECATED Step 6: Detect hazards (check_compat.py, semantic only)
python check_compat.py --uv-lock uv.lock --hazard-patterns-only

# Step 7: Report
python ledger.py --load ledger.json --generate-report
```

---

## Evaluation Summary

| Aspect | Assessment |
|--------|-----------|
| **Is probe_api.py needed?** | **YES. Critical.** uv doesn't verify features, only versions. |
| **Is the current implementation good?** | **NO. Overengineered with objects.inv parsing.** |
| **Should it be refactored?** | **YES. Simplify to live import + inspect only.** |
| **How does it fit with uv?** | **Perfectly. uv resolves versions; probe_api verifies assumptions.** |
| **Is it Tier-0 evidence?** | **YES. inspect on actual source code is ground truth.** |

**Bottom line:** probe_api.py is not redundant—it's **essential**. But it should be much simpler: just answer "does this symbol exist in the installed package?" That's enough.