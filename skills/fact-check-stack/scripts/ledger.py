#!/usr/bin/env python3
"""
ledger.py: Manage claim ledger, validate claims, and generate feasibility reports.

Usage:
    python ledger.py --add-claim C-007 --verdict VERIFIED --blast-radius load-bearing --output ledger.json
    python ledger.py --load ledger.json --generate-report --output feasibility-report.md
    python ledger.py --validate ledger.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

def create_claim(claim_id: str, assertion: str, verdict: str, blast_radius: str,
                tier: int, source: str, caveat: str = '', mitigation: str = '') -> Dict:
    """
    Create a claim structure.
    
    Args:
        claim_id: Unique claim identifier (e.g., 'C-007')
        assertion: The claim being verified
        verdict: VERIFIED, REFUTED, PARTIAL, UNVERIFIABLE, UNSUPPORTED
        blast_radius: load-bearing, contained, reversible
        tier: Evidence tier (0, 1, 2, 3)
        source: Source URL or description
        caveat: Optional caveat text
        mitigation: Optional mitigation text
    
    Returns:
        Claim dictionary.
    """
    valid_verdicts = {'VERIFIED', 'REFUTED', 'PARTIAL', 'UNVERIFIABLE', 'UNSUPPORTED'}
    valid_radii = {'load-bearing', 'contained', 'reversible'}
    
    if verdict not in valid_verdicts:
        raise ValueError(f"Invalid verdict: {verdict}")
    if blast_radius not in valid_radii:
        raise ValueError(f"Invalid blast_radius: {blast_radius}")
    if tier not in (0, 1, 2, 3):
        raise ValueError(f"Invalid tier: {tier}")
    
    return {
        'claim_id': claim_id,
        'assertion': assertion,
        'verdict': verdict,
        'blast_radius': blast_radius,
        'tier': tier,
        'source': source,
        'caveat': caveat,
        'mitigation': mitigation,
        'recorded_at': datetime.now().isoformat() + 'Z'
    }

def load_ledger(path: str) -> Optional[Dict]:
    """Load a claim ledger."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Create new ledger
        return {'claims': [], 'created_at': datetime.now().isoformat() + 'Z'}
    except Exception as e:
        print(f"ERROR: Could not load ledger {path}: {e}", file=sys.stderr)
        return None

def save_ledger(ledger: Dict, path: str) -> bool:
    """Save a claim ledger."""
    try:
        with open(path, 'w') as f:
            json.dump(ledger, f, indent=2)
        return True
    except Exception as e:
        print(f"ERROR: Could not save ledger {path}: {e}", file=sys.stderr)
        return False

def add_claim_to_ledger(ledger: Dict, claim: Dict) -> None:
    """Add a claim to the ledger."""
    # Check for duplicate
    existing = [c for c in ledger['claims'] if c['claim_id'] == claim['claim_id']]
    if existing:
        # Replace existing
        ledger['claims'] = [c for c in ledger['claims'] if c['claim_id'] != claim['claim_id']]
    
    ledger['claims'].append(claim)

def validate_ledger(ledger: Dict) -> List[str]:
    """
    Validate a ledger for consistency.
    
    Returns:
        List of validation errors, or empty list if valid.
    """
    errors = []
    
    if 'claims' not in ledger:
        errors.append("Missing 'claims' key in ledger")
        return errors
    
    for i, claim in enumerate(ledger['claims']):
        required_keys = {'claim_id', 'assertion', 'verdict', 'blast_radius', 'tier', 'source'}
        missing = required_keys - set(claim.keys())
        if missing:
            errors.append(f"Claim {i}: Missing keys: {missing}")
        
        if claim.get('verdict') not in {'VERIFIED', 'REFUTED', 'PARTIAL', 'UNVERIFIABLE', 'UNSUPPORTED'}:
            errors.append(f"Claim {claim.get('claim_id')}: Invalid verdict: {claim.get('verdict')}")
        
        if claim.get('blast_radius') not in {'load-bearing', 'contained', 'reversible'}:
            errors.append(f"Claim {claim.get('claim_id')}: Invalid blast_radius: {claim.get('blast_radius')}")
        
        if claim.get('tier') not in (0, 1, 2, 3):
            errors.append(f"Claim {claim.get('claim_id')}: Invalid tier: {claim.get('tier')}")
    
    return errors

def compute_feasibility_statement(claims: List[Dict]) -> str:
    """
    Compute overall feasibility based on claims.
    
    Args:
        claims: List of claim dictionaries
    
    Returns:
        Feasibility statement: GO, GO-WITH-MITIGATION, or REVISE-ADR.
    """
    load_bearing = [c for c in claims if c['blast_radius'] == 'load-bearing']
    
    if not load_bearing:
        return 'GO'
    
    # Check load-bearing claims
    refuted = [c for c in load_bearing if c['verdict'] == 'REFUTED']
    blocked = [c for c in load_bearing if c['verdict'] == 'UNSUPPORTED']
    unverifiable = [c for c in load_bearing if c['verdict'] == 'UNVERIFIABLE']
    partial_with_miti = [c for c in load_bearing if c['verdict'] == 'PARTIAL' and c['mitigation']]
    
    if refuted or blocked:
        return 'REVISE-ADR'
    
    if unverifiable and not partial_with_miti:
        return 'REVISE-ADR'
    
    if partial_with_miti:
        return 'GO-WITH-MITIGATION'
    
    return 'GO'

def generate_markdown_report(ledger: Dict, adr_name: str = 'ADR-001') -> str:
    """
    Generate a feasibility report in Markdown.
    
    Args:
        ledger: Claim ledger
        adr_name: Name of the ADR being reviewed
    
    Returns:
        Markdown report string.
    """
    claims = ledger.get('claims', [])
    
    feasibility = compute_feasibility_statement(claims)
    
    report = f"""# Feasibility Report: {adr_name}

**Status:** `{feasibility}`

**Generated:** {datetime.now().isoformat()}Z

**Summary:**
- Total claims verified: {len(claims)}
- Load-bearing claims: {len([c for c in claims if c['blast_radius'] == 'load-bearing'])}
- Refuted claims: {len([c for c in claims if c['verdict'] == 'REFUTED'])}
- Unverifiable claims: {len([c for c in claims if c['verdict'] == 'UNVERIFIABLE'])}

**Recommendation:** {get_recommendation(feasibility)}

---

## Detailed Findings

"""
    
    # Group by verdict
    by_verdict = {}
    for claim in claims:
        verdict = claim['verdict']
        if verdict not in by_verdict:
            by_verdict[verdict] = []
        by_verdict[verdict].append(claim)
    
    for verdict in ['VERIFIED', 'REFUTED', 'PARTIAL', 'UNVERIFIABLE', 'UNSUPPORTED']:
        if verdict in by_verdict:
            report += f"### {verdict}\n\n"
            for claim in by_verdict[verdict]:
                report += f"**{claim['claim_id']}**: {claim['assertion']}\n\n"
                report += f"- **Blast radius:** {claim['blast_radius']}\n"
                report += f"- **Tier:** {claim['tier']}\n"
                report += f"- **Source:** {claim['source']}\n"
                if claim.get('caveat'):
                    report += f"- **Caveat:** {claim['caveat']}\n"
                if claim.get('mitigation'):
                    report += f"- **Mitigation:** {claim['mitigation']}\n"
                report += "\n"
    
    # Risk register
    report += "---\n\n## Risk Register\n\n"
    risks = [c for c in claims if c['verdict'] in ('REFUTED', 'PARTIAL', 'UNVERIFIABLE', 'UNSUPPORTED')]
    if risks:
        for risk in risks:
            report += f"- **{risk['claim_id']}** ({risk['verdict']}): {risk['assertion']}\n"
            if risk.get('mitigation'):
                report += f"  - Mitigation: {risk['mitigation']}\n"
    else:
        report += "No risks identified.\n"
    
    # Proposed amendments
    amendments = [c for c in claims if c['verdict'] in ('REFUTED', 'UNSUPPORTED') or (c['verdict'] == 'PARTIAL' and c.get('mitigation'))]
    if amendments:
        report += "\n---\n\n## Proposed ADR Amendments\n\n"
        for amendment in amendments:
            report += f"### {amendment['claim_id']}\n\n"
            report += f"**Original assertion:** {amendment['assertion']}\n\n"
            report += f"**Proposed change:**\n```\n{amendment.get('mitigation', 'N/A')}\n```\n\n"
    
    return report

def get_recommendation(feasibility: str) -> str:
    """Get a human-readable recommendation for feasibility status."""
    recommendations = {
        'GO': 'All load-bearing claims are verified. Proceed with confidence.',
        'GO-WITH-MITIGATION': 'Some load-bearing claims are partial or have mitigations. Proceed with documented mitigations.',
        'REVISE-ADR': 'One or more load-bearing claims are refuted or unverifiable. Update the ADR with an alternative approach and re-run from Phase 1.',
    }
    return recommendations.get(feasibility, 'Review claims and determine path forward.')

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Manage claim ledger and generate feasibility reports"
    )
    parser.add_argument('--load', help='Path to existing ledger')
    parser.add_argument('--add-claim', help='Claim ID to add')
    parser.add_argument('--assertion', help='Claim assertion text')
    parser.add_argument('--verdict', help='Claim verdict (VERIFIED, REFUTED, PARTIAL, UNVERIFIABLE, UNSUPPORTED)')
    parser.add_argument('--blast-radius', help='Blast radius (load-bearing, contained, reversible)')
    parser.add_argument('--tier', type=int, help='Evidence tier (0, 1, 2, 3)')
    parser.add_argument('--source', help='Source URL or description')
    parser.add_argument('--caveat', default='', help='Optional caveat text')
    parser.add_argument('--mitigation', default='', help='Optional mitigation text')
    parser.add_argument('--generate-report', action='store_true', help='Generate Markdown report')
    parser.add_argument('--validate', action='store_true', help='Validate ledger')
    parser.add_argument('--output', default='ledger.json', help='Output file path')
    parser.add_argument('--adr-name', default='ADR-001', help='ADR name for report')
    
    args = parser.parse_args()
    
    # Load or create ledger
    ledger_path = args.load or args.output
    ledger = load_ledger(ledger_path)
    if not ledger:
        sys.exit(1)
    
    # Add claim if provided
    if args.add_claim:
        if not all([args.assertion, args.verdict, args.blast_radius, args.tier is not None, args.source]):
            print("ERROR: --add-claim requires --assertion, --verdict, --blast-radius, --tier, --source", file=sys.stderr)
            sys.exit(1)
        
        claim = create_claim(
            args.add_claim,
            args.assertion,
            args.verdict,
            args.blast_radius,
            args.tier,
            args.source,
            args.caveat,
            args.mitigation
        )
        add_claim_to_ledger(ledger, claim)
        print(f"✓ Added claim {args.add_claim}", file=sys.stderr)
    
    # Validate ledger
    if args.validate:
        errors = validate_ledger(ledger)
        if errors:
            print("Validation errors:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)
        else:
            print("✓ Ledger is valid", file=sys.stderr)
    
    # Generate report
    if args.generate_report:
        report = generate_markdown_report(ledger, args.adr_name)
        report_path = args.output.replace('.json', '.md')
        try:
            with open(report_path, 'w') as f:
                f.write(report)
            print(f"✓ Report written to {report_path}", file=sys.stderr)
        except Exception as e:
            print(f"ERROR: Could not write report: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Save ledger
    if not save_ledger(ledger, args.output):
        sys.exit(1)
    
    print(f"✓ Ledger saved to {args.output}", file=sys.stderr)

if __name__ == '__main__':
    main()
