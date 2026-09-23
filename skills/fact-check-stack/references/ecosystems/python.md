# Python Ecosystem Guide

Default ecosystem for fact-check-stack. Covers package management, version resolution, and introspection.

## Package Management: PyPI

### Version Resolution

Python packages are distributed via PyPI and installed via `pip`, `uv`, `poetry`, or `pipenv`.

**Version specifier formats:**
```
package==1.2.3           # Exact version
package>=1.2.3           # At least this version
package>=1.2.3,<2.0      # Range
package>=1.2.3;python_requires=">=3.8" # Conditional
```

**Resolution algorithm:**
1. Parse all requirements and their version specifiers.
2. Recursively fetch each package's dependencies (from PyPI JSON API).
3. Find a version set that satisfies all constraints.
4. If no solution exists, resolution fails.

### PyPI JSON API

**Endpoint:**
```
GET https://pypi.org/pypi/{package}/{version}/json
GET https://pypi.org/pypi/{package}/json  # Latest version
```

**Key fields:**
```json
{
  "info": {
    "version": "2.0.36",
    "requires_python": ">=3.7",
    "requires_dist": [
      "greenlet (!=0.4.17,<2.0) ; python_version >= '3.11'",
      "importlib-metadata (>=4.6.1) ; python_version < '3.10'",
      "typing-extensions (>=4.2.0)"
    ],
    "home_page": "https://www.sqlalchemy.org",
    "docs_url": "https://docs.sqlalchemy.org",
    "yanked": false,
    "yanked_reason": null
  },
  "releases": {
    "2.0.36": [
      {
        "filename": "SQLAlchemy-2.0.36.tar.gz",
        "url": "...",
        "upload_time_iso_8601": "2024-09-17T10:30:00Z",
        "yanked": false
      },
      {
        "filename": "SQLAlchemy-2.0.36-py3-none-any.whl",
        "url": "...",
        "yanked": false
      }
    ]
  }
}
```

**Fields of interest:**
- `requires_python`: Version constraint for Python interpreter.
- `requires_dist`: Transitive dependencies with version specs and optional markers.
- `yanked`: Boolean; if true, the version is deprecated/unsafe.
- `releases[version]`: List of distributions (wheels, source) for that version.

### Check Release Date

```python
def get_release_date(package, version):
    """Fetch the release date of a package version from PyPI."""
    import urllib.request
    import json
    from datetime import datetime
    
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    response = urllib.request.urlopen(url)
    data = json.load(response)
    
    # First release of this version
    first_release = data['releases'][version][0]
    date_str = first_release['upload_time_iso_8601']
    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))

# Example
from datetime import datetime
date = get_release_date('sqlalchemy', '2.0.36')
print(f"Released: {date.date()}")
```

---

## Wheel Metadata: Platform Compatibility

Wheels are the primary distribution format for Python packages. A wheel filename encodes:

```
{distribution}-{version}(-{build})?-{python}-{abi}-{platform}.whl
```

**Example:**
```
SQLAlchemy-2.0.36-py3-none-any.whl
  → distribution: SQLAlchemy
  → version: 2.0.36
  → python: py3 (Python 3.x, any minor version)
  → abi: none (no C extension ABI pinning)
  → platform: any (all platforms)

numpy-1.26.0-cp313-cp313-win_amd64.whl
  → python: cp313 (CPython 3.13)
  → abi: cp313 (CPython 3.13 ABI)
  → platform: win_amd64 (Windows x86_64)
```

**Tags:**
- `py3`, `py2.py3`: Universal wheels, support multiple Python versions.
- `cp38`, `cp39`, etc.: CPython version-specific.
- `pp38`: PyPy version-specific.
- `manylinux2014`: Binary wheel compatible with manylinux2014 (glibc 2.17+).
- `win_amd64`, `macosx_10_9_x86_64`, `linux_x86_64`: Platform-specific.

### Compatibility Check

```python
def check_wheel_compatibility(package, version, python_version, platform):
    """
    Check if a package wheel is available for the target Python/platform.
    
    Args:
        package: Package name
        version: Package version
        python_version: 'cp38', 'cp311', 'pp39', etc.
        platform: 'win_amd64', 'manylinux2014_x86_64', 'macosx_11_0_x86_64'
    
    Returns:
        bool: True if a compatible wheel exists
    """
    import urllib.request
    import json
    
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    response = urllib.request.urlopen(url)
    data = json.load(response)
    
    # Check all available wheels
    for release in data['releases'][version]:
        filename = release['filename']
        if filename.endswith('.whl'):
            # Parse wheel filename
            parts = filename.split('-')
            if len(parts) >= 5:
                wheel_python = parts[3]
                wheel_platform = parts[5].replace('.whl', '')
                
                # Check if it matches
                if (wheel_python in ('py3', 'py2.py3') or wheel_python == python_version) and \
                   (wheel_platform == 'any' or wheel_platform == platform):
                    return True
    
    return False

# Example
compatible = check_wheel_compatibility('numpy', '1.26.0', 'cp313', 'win_amd64')
print(f"numpy 1.26.0 supports Python 3.13 on Windows x86_64: {compatible}")
```

---

## Symbol Introspection: Pre-installation (objects.inv)

During the planning phase, packages may not be installed yet. The best way to verify symbol existence *before* installing a package is to query its remote `objects.inv` file (if it uses Sphinx).

### Sphinx objects.inv

Most Python packages document with Sphinx. The `objects.inv` file is a binary inventory of every documented symbol.

**Location pattern:**
```
{docs_base}/objects.inv
```

**Parsing via Scratch Script (using Sphinx):**
If `sphinx` is available in the environment, you can run a scratch script to parse it:

```python
# scratch.py
from sphinx.ext.intersphinx import fetch_inventory

uri = 'https://docs.sqlalchemy.org/20/objects.inv'
inv = fetch_inventory(uri)

# Structure: inv[domain][role][name] = (project, version, url, display_name)
# Example:
if 'py' in inv and 'method' in inv['py']:
    methods = inv['py']['method']
    if 'AsyncSession.begin_nested' in methods:
        url = methods['AsyncSession.begin_nested'][2]
        print(f"Found at: {url}")
```

---

## Symbol Introspection: Live Probe

If a package is already installed (or you choose to `uv pip install` it), symbol verification via **live import + inspect** using `probe_api.py` is the most robust method. This is Tier-0 ground truth: it inspects the actual installed source code.

### Using probe_api.py (Recommended)

```bash
# Verify a symbol
python scripts/probe_api.py --package sqlalchemy --symbol "ext.asyncio.AsyncSession.begin_nested"

# JSON output for ledger integration
python scripts/probe_api.py --package sqlalchemy --symbol "ext.asyncio.AsyncSession.begin_nested" --json
```

### Live Introspection: inspect Module

For direct Python scripting or ad-hoc checks:

```python
import importlib
import inspect

# Import the package
module = importlib.import_module('sqlalchemy.ext.asyncio')

# Get a class
cls = getattr(module, 'AsyncSession')

# Check if a method exists
if hasattr(cls, 'begin_nested'):
    method = getattr(cls, 'begin_nested')
    sig = inspect.signature(method)
    print(f"AsyncSession.begin_nested{sig}")
    # Output: (*, savepoint_name: str | None = None) -> AsyncTransaction
else:
    print("Method does not exist")

# Get docstring
print(inspect.getdoc(method))

# Get source file and line number
print(f"Defined at: {inspect.getfile(method)}:{inspect.getsourcelines(method)[1]}")
```

**Verdict:** If `inspect` finds the symbol, it exists (Tier-0 ground truth). If not found, the symbol doesn't exist in the installed version.

---

## Dependency Resolution: Manual Algorithm

When checking cross-package compatibility, resolve all dependencies:

```python
def resolve_dependencies(package, version, python_version='3.11'):
    """
    Recursively resolve all dependencies for a package.
    
    Args:
        package: Top-level package name
        version: Version to resolve
        python_version: Python version for conditional dependencies (e.g., '3.11')
    
    Returns:
        dict: {package: version, ...} for all resolved packages
    """
    import urllib.request
    import json
    from packaging.markers import Marker
    from packaging.specifiers import SpecifierSet
    
    resolved = {}
    to_process = [(package, version)]
    processed = set()
    
    while to_process:
        pkg, ver = to_process.pop(0)
        
        if (pkg, ver) in processed:
            continue
        processed.add((pkg, ver))
        resolved[pkg] = ver
        
        # Fetch package metadata
        url = f"https://pypi.org/pypi/{pkg}/{ver}/json"
        try:
            response = urllib.request.urlopen(url)
            data = json.load(response)
        except:
            print(f"Warning: Could not fetch {pkg}=={ver}")
            continue
        
        # Parse dependencies
        requires_dist = data['info'].get('requires_dist', [])
        for req in requires_dist:
            # Parse requirement: "name (spec) ; marker"
            # Example: "greenlet (!=0.4.17,<2.0) ; python_version >= '3.11'"
            
            if ' ; ' in req:
                dep_part, marker_part = req.split(' ; ', 1)
                marker = Marker(marker_part)
                # Check if marker applies to our Python version
                if not marker.evaluate({'python_version': python_version}):
                    continue
            else:
                dep_part = req
            
            # Extract package name and version spec
            dep_parts = dep_part.split(' ')
            dep_name = dep_parts[0].strip()
            if len(dep_parts) > 1:
                # Remove parentheses
                spec = ' '.join(dep_parts[1:]).strip('()')
            else:
                spec = '*'
            
            # For simplicity, resolve to the latest matching version
            # (In production, implement proper version pinning logic)
            to_process.append((dep_name, 'latest'))  # Placeholder
    
    return resolved

# Example
deps = resolve_dependencies('sqlalchemy', '2.0.36', python_version='3.11')
print(f"Dependencies: {deps}")
```

---

## Version Constraint Intersection

When two packages require different versions of a shared dependency:

```python
from packaging.specifiers import SpecifierSet

def check_version_intersection(constraints):
    """
    Check if a set of version constraints can be satisfied.
    
    Args:
        constraints: Dict of {package: [version_specs]}
                    E.g., {'numpy': ['>=1.20', '<2.0'], 'scipy': ['<1.10']}
    
    Returns:
        dict: {'compatible': bool, 'possible_versions': [...]}
    """
    # For each package, compute the intersection of all specifier sets
    intersections = {}
    for pkg, specs in constraints.items():
        spec_set = SpecifierSet(','.join(specs))
        intersections[pkg] = spec_set
    
    # Brute-force check: test versions 0-20 (in real code, fetch from PyPI)
    compatible_versions = {}
    for major in range(0, 10):
        for minor in range(0, 20):
            version = f"{major}.{minor}.0"
            all_match = True
            for pkg, spec_set in intersections.items():
                if version not in spec_set:
                    all_match = False
                    break
            if all_match:
                compatible_versions[version] = True
    
    return {
        'compatible': len(compatible_versions) > 0,
        'possible_versions': list(compatible_versions.keys())
    }

# Example: Check if numpy>=1.20 and scipy<1.10 (which needs numpy<1.20) can coexist
result = check_version_intersection({
    'numpy': ['>=1.20'],
    'scipy': ['<1.10']  # scipy<1.10 requires numpy<1.20
})
print(result)
# → {'compatible': False, 'possible_versions': []}
```

---

## End-of-Life (EOL) Check

Monitor Python version EOL to warn about outdated Python versions:

```python
def check_python_eol(python_version):
    """Check if a Python version is EOL."""
    from datetime import datetime
    
    eol_dates = {
        '3.7': '2023-06-27',
        '3.8': '2024-10-07',
        '3.9': '2025-10-05',
        '3.10': '2026-10-04',
        '3.11': '2027-10-24',
        '3.12': '2028-10-02',
    }
    
    eol_date_str = eol_dates.get(python_version)
    if eol_date_str:
        eol_date = datetime.fromisoformat(eol_date_str)
        now = datetime.now()
        if now > eol_date:
            return f"Python {python_version} reached EOL on {eol_date_str}"
        else:
            days_left = (eol_date - now).days
            return f"Python {python_version} will reach EOL in {days_left} days"
    
    return "Unknown EOL status"

# Example
print(check_python_eol('3.8'))
```

---

## Environment Isolation: Virtual Environments

Always resolve and test in an isolated virtual environment:

```bash
# Create a temporary virtual environment for testing
python3.11 -m venv /tmp/test_env

# Activate
source /tmp/test_env/bin/activate  # Linux/macOS
# or
/tmp/test_env/Scripts/activate  # Windows

# Dry-run install
pip install --dry-run package_a package_b

# Check version resolution
pip install --dry-run package_a package_b --verbose

# Install and introspect
pip install package_a package_b
python -c "import package_a; print(package_a.__version__)"

# Clean up
deactivate
rm -rf /tmp/test_env
```

---

## Tools & Standard Scripts

### Lightweight Tools (No Dependencies)

- **`urllib`, `json`:** PyPI API queries.
- **`packaging`:** Version specifiers and markers (standard in pip environments).
- **`inspect`:** Live introspection (stdlib).

### Optional Libraries (Lightweight)

- **`sphinx`:** Parse `objects.inv` officially.
- **`beautifulsoup4`:** Parse HTML docs.
- **`html2text`:** Convert HTML to markdown.

### Command-Line Shortcuts

```bash
# Check if a package/version exists
python -m pip index versions sqlalchemy | grep "2.0.36"

# Dry-run resolution
pip install --dry-run sqlalchemy==2.0.36 pydantic==2.5.0

# List installed packages and versions
pip list

# Show package metadata
pip show sqlalchemy

# Search PyPI for recent versions
python -c "import urllib.request, json; \
  r = urllib.request.urlopen('https://pypi.org/pypi/sqlalchemy/json'); \
  data = json.load(r); \
  print('\n'.join(sorted(data['releases'].keys())[-10:]))"
```

---

## Glossary

| Term | Definition |
|------|-----------|
| **PyPI** | Python Package Index; central repository for Python packages. |
| **Wheel** | Binary distribution format (.whl); faster than source. |
| **Egg** | Legacy distribution format; obsolete. |
| **Specifier** | Version constraint syntax (e.g., `>=1.2.0,<2.0`). |
| **Marker** | Conditional dependency syntax (e.g., `python_version >= '3.8'`). |
| **objects.inv** | Sphinx documentation inventory; machine-readable symbol index. |
| **Requires-dist** | List of transitive dependencies in package metadata. |
| **Yanked** | Version marked as unsafe/deprecated on PyPI; not installed by default. |
| **EOL** | End-of-Life; Python or package version no longer supported. |

