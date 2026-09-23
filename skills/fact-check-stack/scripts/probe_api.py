#!/usr/bin/env python3
"""
probe_api.py v2.0: Verify symbol existence in an installed Python package.

Uses live import + inspect (Tier-0 ground truth: actual source code).
Version resolution is uv's job; this script verifies features, not versions.

Usage:
    python probe_api.py --package sqlalchemy --symbol "ext.asyncio.AsyncSession.begin_nested"
    python probe_api.py --package fastapi --symbol "on_event"
    python probe_api.py --package pydantic --symbol "BaseModel.model_validate_json" --json

Exit codes:
    0  Symbol exists (VERIFIED)
    1  Symbol does not exist (UNSUPPORTED / IMPORT_ERROR / ERROR)
"""

import importlib
import inspect
import json
import sys
from typing import Dict, Optional


def probe_live_symbol(package: str, version: str, symbol_path: str) -> Optional[Dict]:
    """
    Check whether a symbol exists in an installed package via live import.

    This is Tier-0 ground truth: it inspects the actual source code in the
    active environment. The `version` parameter is accepted for compatibility
    but not used (version is guaranteed by the uv.lock-managed venv).

    Args:
        package:     Import name of the package (e.g., 'sqlalchemy').
        version:     Package version string — kept for call-site compat,
                     not used internally.
        symbol_path: Dot-separated attribute path from the package root
                     (e.g., 'ext.asyncio.AsyncSession.begin_nested').

    Returns:
        Dictionary with symbol details, or None if symbol not found
        or package not importable.
    """
    return _probe_symbol_internal(package, symbol_path)


def probe_symbol(package: str, symbol_path: str) -> Dict:
    """
    Verify symbol existence and extract metadata.

    Args:
        package:     Import name of the package (e.g., 'sqlalchemy').
        symbol_path: Dot-separated attribute path (e.g., 'AsyncSession.begin_nested').

    Returns:
        Dictionary with verdict and details. Never returns None.
    """
    result = _probe_symbol_internal(package, symbol_path)
    if result is None:
        return {
            'package': package,
            'symbol': symbol_path,
            'exists': False,
            'verdict': 'UNSUPPORTED',
            'tier': 0,
            'details': {
                'message': f"Symbol '{symbol_path}' not found in package '{package}'",
            },
        }
    result['package'] = package
    result['verdict'] = 'VERIFIED'
    result['tier'] = 0
    return result


def _probe_symbol_internal(package: str, symbol_path: str) -> Optional[Dict]:
    """
    Core probe logic: import package and traverse symbol_path.

    Returns a result dict on success, None on symbol-not-found.
    Raises nothing (all exceptions are caught and returned as None or dicts).
    """
    try:
        module = importlib.import_module(package)
        module_version = getattr(module, '__version__', 'unknown')

        obj = module
        path_parts = symbol_path.split('.')
        traversed = [package]

        for part in path_parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
                traversed.append(part)
            else:
                # Symbol not found at this step
                print(
                    f"  ✗ '{part}' not found in '{'.'.join(traversed)}'",
                    file=sys.stderr,
                )
                return None

        # Symbol found — collect metadata
        result: Dict = {
            'symbol': symbol_path,
            'exists': True,
            'module_version': module_version,
            'type': type(obj).__name__,
        }

        if callable(obj):
            try:
                result['signature'] = str(inspect.signature(obj))
            except (ValueError, TypeError):
                result['signature'] = '(unable to determine)'

        if inspect.isclass(obj):
            result['is_class'] = True
            result['public_methods'] = [m for m in dir(obj) if not m.startswith('_')][:10]

        doc = inspect.getdoc(obj)
        if doc:
            result['docstring'] = doc[:200]

        try:
            result['source_file'] = inspect.getfile(obj)
        except (TypeError, OSError):
            pass

        return result

    except ImportError as e:
        print(f"  ✗ Import error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}", file=sys.stderr)
        return None


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Verify symbol existence in installed package (Tier-0 ground truth). "
            "Version resolution is handled by uv; this script verifies features."
        )
    )
    parser.add_argument(
        '--package',
        required=True,
        help='Package import name (e.g., sqlalchemy)',
    )
    parser.add_argument(
        '--symbol',
        required=True,
        help='Symbol path (e.g., ext.asyncio.AsyncSession.begin_nested)',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        dest='output_json',
        help='Output full result as JSON (default: human-readable)',
    )

    args = parser.parse_args()

    print(f"Probing {args.package}::{args.symbol}...", file=sys.stderr)
    result = probe_symbol(args.package, args.symbol)

    if args.output_json:
        print(json.dumps(result, indent=2))
    else:
        status = "✓ VERIFIED" if result['exists'] else "✗ UNSUPPORTED"
        print(f"{status}  {args.package}::{args.symbol}")
        if result['exists']:
            details = result.get('details', result)
            print(f"  Type:    {details.get('type', result.get('type', 'unknown'))}")
            sig = details.get('signature', result.get('signature'))
            if sig:
                print(f"  Sig:     {sig}")
            src = details.get('source_file', result.get('source_file'))
            if src:
                print(f"  Source:  {src}")
            ver = details.get('module_version', result.get('module_version'))
            if ver:
                print(f"  Version: {ver}")
        else:
            details = result.get('details', {})
            print(f"  {details.get('message', 'Symbol not found')}")

    sys.exit(0 if result['exists'] else 1)


if __name__ == '__main__':
    main()
