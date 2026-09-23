#!/usr/bin/env python3
"""
detect_hazards.py: Detect semantic hazard patterns and EOL packages.

Phase 1 (version resolution) is handled by uv. This script focuses on
what uv cannot do: semantic hazard patterns (async/sync boundary, session
lifecycle, event loop ownership, serialization contracts) and EOL signals.

NOTE: Version-range compatibility and Python version intersection are
intentionally NOT implemented here. Use `uv lock --all-platforms` for that.

If not using uv, first export to a requirements file and re-lock:
    uv export --format requirements-txt > requirements.txt
    uv lock

Usage:
    python detect_hazards.py --uv-lock uv.lock --output hazard-report.json
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------

def load_uv_lock(path: str) -> Optional[Dict]:
    """
    Parse a uv.lock file (TOML format) to extract the package name/version map.

    Returns a dict shaped like stack-lock.json's 'packages' field:
        { 'package-name': { 'version': '1.2.3' }, ... }

    Requires Python 3.11+ for tomllib (stdlib). Falls back to tomli if available.
    """
    try:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib  # pip install tomli
            except ImportError:
                print(
                    "ERROR: Parsing uv.lock requires tomllib (Python 3.11+) "
                    "or `pip install tomli`.",
                    file=sys.stderr,
                )
                return None

        with open(path, 'rb') as f:
            data = tomllib.load(f)

        packages = {}
        for pkg in data.get('package', []):
            name = pkg.get('name', '')
            version = pkg.get('version', '')
            if name and version:
                packages[name] = {'version': version}

        return {'packages': packages}

    except Exception as e:
        print(f"ERROR: Could not parse {path}: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Semantic hazard pattern detection
# ---------------------------------------------------------------------------

def detect_hazard_patterns(packages: Dict) -> Dict:
    """
    Detect known semantic hazard patterns in the package set.

    These are patterns that uv cannot detect because they are about runtime
    behavior and API contracts, not version ranges.

    See references/compatibility-patterns.md for the full hazard class catalog.

    Args:
        packages: { package_name: { 'version': ..., ... }, ... }

    Returns:
        Dictionary with detected hazards and warnings.
    """
    result = {
        'hazards_detected': [],
        'warnings': [],
        'mitigations': [],
    }

    pkg_set = set(p.lower() for p in packages.keys())

    # Hazard 1: Async/Sync Boundary
    # FastAPI is async; Flask is sync. Cannot share async libs between them.
    if 'fastapi' in pkg_set and 'flask' in pkg_set:
        result['hazards_detected'].append({
            'hazard_class': 'async_sync_boundary',
            'packages': ['fastapi', 'flask'],
            'description': (
                'FastAPI is async; Flask is sync. '
                'Async libraries used in FastAPI cannot be called from Flask handlers.'
            ),
            'mitigation': (
                'Use FastAPI exclusively for async code. '
                'If both are required, isolate them in separate processes.'
            ),
            'blast_radius': 'load-bearing',
            'reference': 'references/compatibility-patterns.md §1',
        })

    # Hazard 2: Session Lifecycle Mismatch
    # SQLAlchemy sessions are request-scoped; Celery tasks run in a separate context.
    if 'sqlalchemy' in pkg_set and 'celery' in pkg_set:
        result['hazards_detected'].append({
            'hazard_class': 'session_lifecycle_mismatch',
            'packages': ['sqlalchemy', 'celery'],
            'description': (
                'SQLAlchemy sessions are request-scoped; '
                'Celery tasks run in a separate process/context. '
                'Passing a session instance to a Celery task will cause '
                '"session already closed" or orphaned transaction errors.'
            ),
            'mitigation': (
                'Pass a session factory to Celery tasks, not a session instance. '
                'Each task must own its session lifecycle.'
            ),
            'blast_radius': 'load-bearing',
            'reference': 'references/compatibility-patterns.md §2',
        })

    # Hazard 3: Event Loop Ownership — multiple async HTTP clients
    if 'aiohttp' in pkg_set and 'httpx' in pkg_set:
        result['warnings'].append({
            'hazard_class': 'event_loop_ownership',
            'packages': ['aiohttp', 'httpx'],
            'warning': (
                'Both aiohttp and httpx are async HTTP clients. '
                'They can coexist, but managing two client lifecycles '
                'increases the risk of event loop conflicts.'
            ),
            'recommendation': (
                'Choose one HTTP client. httpx is preferred for FastAPI/Starlette stacks.'
            ),
            'blast_radius': 'contained',
            'reference': 'references/compatibility-patterns.md §3',
        })

    # Hazard 4: Serialization Contract Mismatch — Pydantic → Redis
    if 'pydantic' in pkg_set and 'redis' in pkg_set:
        result['warnings'].append({
            'hazard_class': 'serialization_contract',
            'packages': ['pydantic', 'redis'],
            'warning': (
                'Pydantic models do not auto-serialize to Redis. '
                'Pydantic.model_dump_json() produces a JSON string; '
                'Redis stores bytes/strings but does not validate the schema.'
            ),
            'recommendation': (
                'Explicitly serialize with pydantic_model.model_dump_json() before caching. '
                'Deserialize with MyModel.model_validate_json(redis.get(key)).'
            ),
            'blast_radius': 'contained',
            'reference': 'references/compatibility-patterns.md §4',
        })

    # Hazard 5: protobuf 4.x and older grpcio versions
    for pkg_name, pkg_info in packages.items():
        if pkg_name.lower() == 'protobuf':
            version = pkg_info.get('version', '')
            if version.startswith('4') or version.startswith('5'):
                for other_pkg in packages:
                    if 'grpc' in other_pkg.lower():
                        result['warnings'].append({
                            'hazard_class': 'dependency_version_conflict',
                            'packages': ['protobuf', other_pkg],
                            'warning': (
                                f'protobuf {version} may conflict with older grpcio versions. '
                                'protobuf 4.x introduced breaking changes to the Python API.'
                            ),
                            'recommendation': (
                                f'Ensure {other_pkg} explicitly supports protobuf {version}. '
                                'Check the grpcio changelog for compatibility matrix.'
                            ),
                            'blast_radius': 'load-bearing',
                            'reference': 'references/compatibility-patterns.md §5',
                        })

    return result


# ---------------------------------------------------------------------------
# EOL detection
# ---------------------------------------------------------------------------

def check_eol_packages(packages: Dict) -> Dict:
    """
    Check for yanked versions and known EOL packages.

    Version-range resolution is uv's responsibility. This function only
    checks for signals in the uv.lock metadata: yanked flag and
    known EOL dates for major packages.

    Args:
        packages: { package_name: { 'version': ..., 'yanked': bool, ... } }

    Returns:
        Dictionary with EOL and yanked warnings.
    """
    result = {
        'eol_packages': [],
        'yanked_packages': [],
        'warnings': [],
    }

    # Known EOL versions (extend as needed)
    eol_map = {
        'django': {
            '2.2': '2024-04-01',
            '3.2': '2024-04-01',
            '4.1': '2023-12-01',
        },
    }

    # Known EOL Python versions (referenced in requires_python checks)
    python_eol = {
        '3.7': '2023-06-27',
        '3.8': '2024-10-07',
    }

    for pkg_name, pkg_info in packages.items():
        version = pkg_info.get('version', '')
        yanked = pkg_info.get('yanked', False)

        # Flag yanked versions
        if yanked:
            result['yanked_packages'].append({
                'package': pkg_name,
                'version': version,
                'message': (
                    f'{pkg_name}=={version} was yanked from PyPI. '
                    'This version is considered unsafe or deprecated by the maintainer.'
                ),
                'blast_radius': 'load-bearing',
            })

        # Flag known EOL package versions
        pkg_key = pkg_name.lower()
        if pkg_key in eol_map:
            for eol_prefix, eol_date in eol_map[pkg_key].items():
                if version.startswith(eol_prefix):
                    result['eol_packages'].append({
                        'package': pkg_name,
                        'version': version,
                        'eol_date': eol_date,
                        'message': f'{pkg_name} {eol_prefix}.x reached EOL on {eol_date}.',
                        'blast_radius': 'contained',
                    })

    return result


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(hazards: Dict, eol: Dict, packages: Dict) -> Dict:
    """
    Combine hazard and EOL findings into a single hazard report.

    Args:
        hazards: Output of detect_hazard_patterns()
        eol: Output of check_eol_packages()
        packages: Original package dict (for metadata)

    Returns:
        Hazard report dict.
    """
    all_blocking = (
        hazards['hazards_detected']
        + eol['yanked_packages']
        + eol['eol_packages']
    )
    all_warnings = hazards['warnings']

    status = 'OK'
    recommendation = 'No semantic hazards detected. Proceed to Phase 3 (claim verification).'

    if all_blocking:
        status = 'HAZARDS_DETECTED'
        recommendation = (
            'Review hazards before proceeding to codegen. '
            'Load-bearing hazards should be documented in ADR §Risk Assumptions.'
        )
    elif all_warnings:
        status = 'WARNINGS'
        recommendation = (
            'Warnings detected. Review and document mitigations in ADR §Risk Assumptions.'
        )

    return {
        'summary': {
            'status': status,
            'packages_checked': len(packages),
            'hazards': len(all_blocking),
            'warnings': len(all_warnings),
            'recommendation': recommendation,
        },
        'hazards_detected': hazards['hazards_detected'],
        'warnings': all_warnings,
        'yanked_packages': eol['yanked_packages'],
        'eol_packages': eol['eol_packages'],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Detect semantic hazard patterns and EOL packages. "
            "Version-range resolution is delegated to uv (see references/uv-integration.md)."
        )
    )

    input_group = parser.add_argument(
        '--uv-lock',
        required=True,
        help='Path to uv.lock (requires Python 3.11+ or tomli). Run `uv lock --all-platforms` first.',
    )

    parser.add_argument(
        '--output',
        default='hazard-report.json',
        help='Output report path (default: hazard-report.json)',
    )

    args = parser.parse_args()

    # Load packages
    data = load_uv_lock(args.uv_lock)

    if not data:
        sys.exit(1)

    packages = data.get('packages', {})
    if not packages:
        print("ERROR: No packages found in input file.", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {len(packages)} packages for semantic hazards...", file=sys.stderr)

    # Run checks
    hazards = detect_hazard_patterns(packages)
    eol = check_eol_packages(packages)
    report = generate_report(hazards, eol, packages)

    # Write output
    try:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"✓ Hazard report written to {args.output}", file=sys.stderr)
        print(f"  Status: {report['summary']['status']}", file=sys.stderr)
        print(f"  Hazards: {report['summary']['hazards']}", file=sys.stderr)
        print(f"  Warnings: {report['summary']['warnings']}", file=sys.stderr)
        print(f"  Recommendation: {report['summary']['recommendation']}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: Could not write report: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
