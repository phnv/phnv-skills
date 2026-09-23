#!/usr/bin/env python3
"""
probe_objects_inv.py: Query Sphinx objects.inv for symbol existence.

Designed for the planning phase of fact-check-stack, BEFORE packages are
installed. Fetches the remote objects.inv binary over HTTP, parses it, and
reports whether a symbol is documented.

Usage:
    python probe_objects_inv.py \\
        --url https://docs.sqlalchemy.org/20/objects.inv \\
        --symbol AsyncSession.begin_nested

    python probe_objects_inv.py \\
        --url https://docs.pydantic.dev/2.9/objects.inv \\
        --symbol BaseModel.model_validate_json \\
        --domain py --role method --json

Exit codes:
    0  Symbol found   (VERIFIED)
    1  Symbol missing (UNSUPPORTED)
    2  Fetch / parse error (UNVERIFIABLE)
"""

import json
import sys
import urllib.request
import urllib.error
import zlib
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Parser: stdlib only, correct Sphinx v2 format
# ---------------------------------------------------------------------------

def _parse_objects_inv_stdlib(data: bytes) -> Optional[Dict[str, Dict]]:
    """
    Parse a Sphinx objects.inv v2 binary payload.

    Format (Sphinx v2):
        Line 1: # Sphinx inventory version 2
        Line 2: # Project: <name>
        Line 3: # Version: <version>
        Line 4: # The remainder of this file is compressed using zlib.
        Remainder: zlib-compressed symbol lines

    Each decompressed symbol line:
        name domaintype:role priority uri anchor display_name

    Returns:
        Nested dict: {domain: {role: {name: {"url": str, "domain_type": str}}}}
        Or None if parsing fails.
    """
    try:
        lines = data.split(b"\n")

        # Validate 4-line header
        if len(lines) < 5:
            print("ERROR: objects.inv too short to have a valid header", file=sys.stderr)
            return None

        if not lines[0].startswith(b"# Sphinx inventory version 2"):
            print(
                f"ERROR: Not a Sphinx v2 objects.inv (first line: {lines[0][:60]!r})",
                file=sys.stderr,
            )
            return None

        # The zlib block starts on line 5 (index 4)
        # Rejoin keeping the original newlines
        zlib_payload = b"\n".join(lines[4:])
        decompressed = zlib.decompress(zlib_payload).decode("utf-8")

        inventory: Dict[str, Dict] = {}

        for line in decompressed.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Format: name domaintype:role priority uri anchor display_name
            parts = line.split(" ", 5)
            if len(parts) < 5:
                continue

            name = parts[0]
            domain_role = parts[1]        # e.g. "py:method"
            # parts[2] = priority
            uri_fragment = parts[3]       # e.g. "path/to.html#$" or "path/to.html#symbol"
            # parts[4] = display name (may be "-" for same as name)

            if ":" in domain_role:
                domain, role = domain_role.split(":", 1)
            else:
                domain, role = domain_role, ""

            if domain not in inventory:
                inventory[domain] = {}
            if role not in inventory[domain]:
                inventory[domain][role] = {}

            # Sphinx uses "$" as a shorthand for the symbol name in anchors
            url = uri_fragment.replace("$", name)

            inventory[domain][role][name] = {
                "url": url,
                "domain_type": domain_role,
            }

        return inventory

    except zlib.error as e:
        print(f"ERROR: zlib decompression failed: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: Parsing failed: {e}", file=sys.stderr)
        return None


def _parse_objects_inv_sphinx(url: str) -> Optional[Dict[str, Dict]]:
    """
    Optional: Parse using sphinx.ext.intersphinx.fetch_inventory if available.
    This is the canonical parser but requires sphinx to be installed.

    Returns same nested dict structure as _parse_objects_inv_stdlib, or None.
    """
    try:
        from sphinx.ext.intersphinx import fetch_inventory  # type: ignore
        import logging

        # fetch_inventory expects a logger; suppress noise
        logger = logging.getLogger("probe_objects_inv")

        raw = fetch_inventory(logger, "", url)
        # fetch_inventory returns {domain_role: {name: (project, version, url, display)}}
        # Convert to our nested format
        inventory: Dict[str, Dict] = {}
        for domain_role, entries in raw.items():
            if ":" in domain_role:
                domain, role = domain_role.split(":", 1)
            else:
                domain, role = domain_role, ""
            if domain not in inventory:
                inventory[domain] = {}
            if role not in inventory[domain]:
                inventory[domain][role] = {}
            for name, (_, _, entry_url, _) in entries.items():
                inventory[domain][role][name] = {
                    "url": entry_url,
                    "domain_type": domain_role,
                }
        return inventory

    except ImportError:
        return None
    except Exception as e:
        print(f"  sphinx fallback failed: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Fetch + parse pipeline
# ---------------------------------------------------------------------------

def fetch_and_parse(url: str) -> Optional[Dict[str, Dict]]:
    """
    Fetch and parse a remote objects.inv URL.

    Attempts stdlib parser first (no deps). Falls back to sphinx if available.

    Returns nested inventory dict, or None on failure.
    """
    print(f"Fetching {url} ...", file=sys.stderr)
    try:
        response = urllib.request.urlopen(url, timeout=15)
        data: bytes = response.read()
        print(f"  Received {len(data)} bytes", file=sys.stderr)
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code}: {e.reason}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"ERROR: URL error: {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: Fetch failed: {e}", file=sys.stderr)
        return None

    # Try stdlib parser
    inv = _parse_objects_inv_stdlib(data)
    if inv is not None:
        print(f"  Parsed {sum(len(r) for d in inv.values() for r in d.values())} symbols (stdlib parser)", file=sys.stderr)
        return inv

    # Fallback: sphinx (requires sphinx to be installed)
    print("  Stdlib parser failed, trying sphinx fallback...", file=sys.stderr)
    inv = _parse_objects_inv_sphinx(url)
    if inv is not None:
        print(f"  Parsed {sum(len(r) for d in inv.values() for r in d.values())} symbols (sphinx parser)", file=sys.stderr)
        return inv

    print("ERROR: Both parsers failed. objects.inv may be malformed or not v2 format.", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Symbol search
# ---------------------------------------------------------------------------

def search_symbol(
    inventory: Dict[str, Dict],
    symbol: str,
    domain: Optional[str] = None,
    role: Optional[str] = None,
) -> Dict:
    """
    Search an inventory for a symbol.

    Args:
        inventory:  Parsed inventory from fetch_and_parse().
        symbol:     Symbol name (e.g., 'AsyncSession.begin_nested').
        domain:     Optional filter (e.g., 'py'). If None, searches all domains.
        role:       Optional filter (e.g., 'method'). If None, searches all roles.

    Returns:
        Result dict with 'exists', 'match', 'similar' (on miss), and 'verdict'.
    """
    domains_to_search = [domain] if domain else list(inventory.keys())
    similar: List[str] = []

    for d in domains_to_search:
        if d not in inventory:
            continue
        roles_to_search = [role] if role else list(inventory[d].keys())
        for r in roles_to_search:
            if r not in inventory[d]:
                continue
            entries = inventory[d][r]
            if symbol in entries:
                return {
                    "exists": True,
                    "verdict": "VERIFIED",
                    "symbol": symbol,
                    "domain": d,
                    "role": r,
                    "url": entries[symbol]["url"],
                    "domain_type": entries[symbol]["domain_type"],
                    "similar": [],
                }
            # Collect partial matches for the 'similar' list
            similar.extend(
                name for name in entries
                if symbol.lower() in name.lower()
            )

    return {
        "exists": False,
        "verdict": "UNSUPPORTED",
        "symbol": symbol,
        "similar": sorted(set(similar))[:10],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Query a Sphinx objects.inv file for symbol existence. "
            "Works WITHOUT installing the target package (pre-installation, planning phase)."
        )
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Full URL to objects.inv (e.g., https://docs.sqlalchemy.org/20/objects.inv)",
    )
    parser.add_argument(
        "--symbol",
        required=True,
        help="Symbol name to look up (e.g., AsyncSession.begin_nested)",
    )
    parser.add_argument(
        "--domain",
        default=None,
        help="Sphinx domain to filter (default: all). Common values: py, c, cpp",
    )
    parser.add_argument(
        "--role",
        default=None,
        help="Sphinx role to filter (default: all). Common values: method, class, function, attribute",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output full result as JSON",
    )

    args = parser.parse_args()

    inventory = fetch_and_parse(args.url)
    if inventory is None:
        result = {
            "exists": False,
            "verdict": "UNVERIFIABLE",
            "symbol": args.symbol,
            "error": "Could not fetch or parse objects.inv",
        }
        if args.output_json:
            print(json.dumps(result, indent=2))
        else:
            print(f"✗ UNVERIFIABLE  {args.symbol}  (fetch/parse failed)")
        sys.exit(2)

    result = search_symbol(inventory, args.symbol, domain=args.domain, role=args.role)

    if args.output_json:
        print(json.dumps(result, indent=2))
    else:
        status = "✓ VERIFIED" if result["exists"] else "✗ UNSUPPORTED"
        print(f"{status}  {args.symbol}")
        if result["exists"]:
            print(f"  Domain/Role: {result.get('domain_type', 'unknown')}")
            print(f"  URL:         {result.get('url', 'unknown')}")
        elif result.get("similar"):
            print(f"  Similar symbols found:")
            for s in result["similar"]:
                print(f"    - {s}")

    sys.exit(0 if result["exists"] else 1)


if __name__ == "__main__":
    main()
