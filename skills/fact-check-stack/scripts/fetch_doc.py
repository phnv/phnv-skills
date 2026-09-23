#!/usr/bin/env python3
"""
fetch_doc.py: Fetch and cache versioned documentation.

Usage:
    python fetch_doc.py --url "https://docs.sqlalchemy.org/20/..." --claim-id C-007 --output-dir .fact-check/cache
    python fetch_doc.py --url "..." --cache-hit [returns cached content if exists]
"""

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

def sanitize_filename(url: str) -> str:
    """Convert URL to a safe filename."""
    # Remove protocol
    name = re.sub(r'^https?://', '', url)
    # Replace non-alphanumeric with underscore
    name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
    # Truncate to reasonable length
    return name[:100]

def build_cache_path(claim_id: str, url: str, version: str = '', cache_dir: str = '.fact-check/cache') -> Path:
    """
    Build a cache file path from claim ID and URL.
    
    Args:
        claim_id: Claim identifier (e.g., 'C-007')
        url: Document URL
        version: Package version (optional, for clarity)
        cache_dir: Cache directory path
    
    Returns:
        Path object for the cache file.
    """
    url_slug = sanitize_filename(url)[:40]
    version_slug = version.replace('.', '_') if version else 'unknown'
    filename = f"{claim_id}_{url_slug}_{version_slug}.txt"
    return Path(cache_dir) / filename

def fetch_document(url: str, timeout: int = 10) -> Optional[Tuple[str, int, str]]:
    """
    Fetch a document from URL.
    
    Args:
        url: Full URL to fetch
        timeout: Timeout in seconds
    
    Returns:
        Tuple of (content, http_status, content_type) or None if fetch fails.
    """
    try:
        request = urllib.request.Request(
            url,
            headers={'User-Agent': 'fact-check-stack/1.0 (+https://anthropic.com)'}
        )
        response = urllib.request.urlopen(request, timeout=timeout)
        
        content_type = response.headers.get('Content-Type', 'text/html')
        http_status = response.status
        content = response.read().decode('utf-8', errors='replace')
        
        return content, http_status, content_type
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason} for {url}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason} for {url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None

def normalize_html_to_text(html: str) -> str:
    """
    Convert HTML to plain text (very basic).
    
    Args:
        html: HTML content
    
    Returns:
        Plain text extracted from HTML.
    """
    import re
    
    # Remove script and style tags
    text = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '\n', text)
    
    # Decode entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&amp;', '&')
    
    # Clean up whitespace
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    text = '\n'.join(lines)
    
    return text

def write_cache(cache_path: Path, url: str, content: str, http_status: int, content_type: str, claim_id: str = ''):
    """
    Write content to cache file with metadata.
    
    Args:
        cache_path: Path to write cache to
        url: Source URL
        content: Document content
        http_status: HTTP status code
        content_type: Content-Type header
        claim_id: Claim ID (for the header)
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    header = f"""METADATA
--------
source_url: {url}
retrieved: {datetime.now().isoformat()}Z
http_status: {http_status}
content_type: {content_type}
claim_id: {claim_id}

CONTENT
-------
"""
    
    with open(cache_path, 'w') as f:
        f.write(header)
        f.write(content)
        f.write('\n\nCACHE_FOOTER\n')
        f.write(f"Cache written at {datetime.now().isoformat()}Z\n")

def read_cache(cache_path: Path) -> Optional[Dict]:
    """
    Read cached document.
    
    Args:
        cache_path: Path to cache file
    
    Returns:
        Dictionary with metadata and content, or None if file doesn't exist.
    """
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, 'r') as f:
            text = f.read()
        
        # Parse metadata section
        metadata = {}
        if 'METADATA' in text and 'CONTENT' in text:
            meta_section = text.split('CONTENT')[0].split('METADATA')[1].strip()
            for line in meta_section.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()
            
            # Extract content
            content = text.split('CONTENT')[1].split('CACHE_FOOTER')[0].strip()
            
            return {
                'metadata': metadata,
                'content': content
            }
    except Exception as e:
        print(f"Warning: Could not read cache {cache_path}: {e}", file=sys.stderr)
    
    return None

def extract_relevant_passage(content: str, keywords: List[str], context_lines: int = 5) -> str:
    """
    Extract passages from content that match keywords.
    
    Args:
        content: Full document content
        keywords: Search terms
        context_lines: Lines of context around match
    
    Returns:
        Extracted passages or original content if no match.
    """
    lines = content.split('\n')
    relevant_lines = set()
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        for i, line in enumerate(lines):
            if keyword_lower in line.lower():
                # Add this line and context
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                for j in range(start, end):
                    relevant_lines.add(j)
    
    if relevant_lines:
        # Return relevant section(s)
        indices = sorted(relevant_lines)
        return '\n'.join(lines[i] for i in indices)
    else:
        # No match; return first N lines as summary
        return '\n'.join(lines[:50])

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fetch and cache versioned documentation"
    )
    parser.add_argument('--url', required=True, help='Full URL to fetch')
    parser.add_argument('--claim-id', required=True, help='Claim ID (e.g., C-007)')
    parser.add_argument('--version', default='', help='Package version (optional)')
    parser.add_argument('--cache-dir', default='.fact-check/cache', help='Cache directory')
    parser.add_argument('--keywords', nargs='+', help='Keywords to extract')
    parser.add_argument('--check-cache-only', action='store_true', help='Only check cache, do not fetch')
    
    args = parser.parse_args()
    
    # Determine cache path
    cache_path = build_cache_path(args.claim_id, args.url, args.version, args.cache_dir)
    
    # Check cache first
    cached = read_cache(cache_path)
    if cached:
        print(f"✓ Cache hit: {cache_path}")
        print(f"  Retrieved: {cached['metadata'].get('retrieved', 'unknown')}")
        
        # If keywords provided, extract relevant passages
        if args.keywords:
            passage = extract_relevant_passage(cached['content'], args.keywords)
            print(f"\n[Extracted passages for: {', '.join(args.keywords)}]\n")
            print(passage)
        else:
            print(f"  Content length: {len(cached['content'])} bytes")
        
        # Output JSON for machine parsing
        print(json.dumps({
            'status': 'cache_hit',
            'claim_id': args.claim_id,
            'cache_path': str(cache_path),
            'metadata': cached['metadata'],
            'content_length': len(cached['content']),
        }))
        return
    
    if args.check_cache_only:
        print(f"✗ Cache miss: {cache_path}")
        sys.exit(1)
    
    # Fetch from URL
    print(f"Fetching: {args.url}", file=sys.stderr)
    result = fetch_document(args.url)
    
    if not result:
        print("ERROR: Could not fetch document", file=sys.stderr)
        sys.exit(1)
    
    content, http_status, content_type = result
    
    # Normalize HTML if needed
    if 'html' in content_type.lower():
        content = normalize_html_to_text(content)
    
    # Write cache
    write_cache(cache_path, args.url, content, http_status, content_type, args.claim_id)
    print(f"✓ Cached: {cache_path}", file=sys.stderr)
    
    # Extract relevant passages if keywords provided
    if args.keywords:
        passage = extract_relevant_passage(content, args.keywords)
        print(f"\n[Extracted passages for: {', '.join(args.keywords)}]\n")
        print(passage)
    
    # Output JSON for machine parsing
    print(json.dumps({
        'status': 'fetched',
        'claim_id': args.claim_id,
        'url': args.url,
        'cache_path': str(cache_path),
        'http_status': http_status,
        'content_type': content_type,
        'content_length': len(content),
    }))

if __name__ == '__main__':
    main()
