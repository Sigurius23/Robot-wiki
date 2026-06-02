"""
metadata_fetcher.py — Semantic Scholar metadata retrieval wrapper.

Thin wrapper over vendor/search_provider.py. Exposes ``fetch_metadata``
to the pipeline and owns the manual fallback prompt logic.

Vendor source: adapted from
  scholar-agent/src/scholar_agent/engine/search_providers/
  (Semantic Scholar provider)
"""

import sys

import requests

import vendor.search_provider as search_provider


def fetch_metadata(doi: str | None, pdf_text: str) -> dict:
    """
    Fetch paper metadata from Semantic Scholar.

    Lookup strategy:
      1. DOI from CLI argument (if provided)
      2. DOI extracted from PDF text (https://doi.org/... or bare 10.xxx/...)
      3. Title-based search (full, then shortened)
      4. Synthetic metadata from PDF text (no manual entry)
    """
    # --- Strategy 1: CLI-provided DOI ---
    if doi is not None:
        result = _try_doi_lookup(doi)
        if result is not None:
            return result
        print("Warning: DOI lookup failed, falling back to PDF DOI extraction.", file=sys.stderr)

    # --- Strategy 2: DOI extracted from PDF text ---
    pdf_doi = _extract_doi_from_text(pdf_text)
    if pdf_doi and pdf_doi != doi:
        print(f"→  Found DOI in PDF text: {pdf_doi}", file=sys.stderr)
        print(f"→  Looking up DOI on Semantic Scholar ...", file=sys.stderr)
        result = _try_doi_lookup(pdf_doi)
        if result is not None:
            print(f"✓  DOI lookup succeeded", file=sys.stderr)
            return result
        print("Warning: PDF DOI lookup failed, falling back to title search.", file=sys.stderr)

    # --- Strategy 3: Title-based search ---
    title = _extract_title_from_text(pdf_text)
    print(f"→  Trying title search ...", file=sys.stderr)
    queries = _build_search_queries(title, pdf_text)

    for query in queries:
        if not query:
            continue
        try:
            result = _query_by_title(query)
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            print(
                f"Warning: Semantic Scholar API returned HTTP {status_code} for query '{query}'.",
                file=sys.stderr,
            )
            continue
        except RuntimeError as exc:
            print(f"Warning: Network error for query '{query}': {exc}", file=sys.stderr)
            continue

        if result is not None:
            return result
        print(f"Warning: No results for query '{query}', trying next fallback...", file=sys.stderr)

    # --- Strategy 4: Extract from PDF text ---
    print(
        "Warning: All Semantic Scholar queries failed. Extracting metadata from PDF text.",
        file=sys.stderr,
    )
    return _extract_metadata_from_pdf(pdf_text)


def _try_doi_lookup(doi: str) -> dict | None:
    """Attempt a DOI lookup, returning None on any failure."""
    try:
        return _query_by_doi(doi)
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        print(f"Warning: Semantic Scholar API returned HTTP {status_code} for DOI '{doi}'.", file=sys.stderr)
        return None
    except RuntimeError as exc:
        print(f"Warning: Network error for DOI '{doi}': {exc}", file=sys.stderr)
        return None


def _extract_doi_from_text(pdf_text: str) -> str | None:
    """
    Extract the first DOI found in the PDF text.

    Looks for:
      - https://doi.org/10.xxxxx
      - http://doi.org/10.xxxxx
      - doi.org/10.xxxxx
      - bare 10.xxxxx/xxxxx pattern near common DOI context words
    """
    import re

    # Search in first 3000 chars where DOI usually appears (header/footer)
    search_text = pdf_text[:3000] + pdf_text[-1000:]

    # Match https://doi.org/10.xxxx/xxxx or doi.org/10.xxxx/xxxx
    url_pattern = re.search(
        r'(?:https?://)?doi\.org/(10\.\d{4,}/\S+)',
        search_text,
        re.IGNORECASE,
    )
    if url_pattern:
        doi = url_pattern.group(1).rstrip('.,;)')
        return doi

    # Match bare DOI: 10.xxxx/xxxx (must have a slash after the prefix)
    bare_pattern = re.search(
        r'\b(10\.\d{4,}/[^\s,;>]+)',
        search_text,
    )
    if bare_pattern:
        doi = bare_pattern.group(1).rstrip('.,;)')
        return doi

    return None


def _build_search_queries(title: str | None, pdf_text: str) -> list[str]:
    """
    Build a list of progressively simpler search queries to try in order.

    1. Full extracted title
    2. First 6 words of title
    3. First 4 words of title
    4. First 8 words from the PDF body (skip headers)
    """
    queries = []

    if title:
        queries.append(title)
        words = title.split()
        if len(words) > 6:
            queries.append(" ".join(words[:6]))
        if len(words) > 4:
            queries.append(" ".join(words[:4]))

    # Try pulling a longer phrase from the first few lines of the PDF
    if pdf_text:
        lines = [l.strip() for l in pdf_text.splitlines() if len(l.strip()) > 20]
        for line in lines[:10]:
            words = line.split()
            candidate = " ".join(words[:8])
            if candidate and candidate not in queries:
                queries.append(candidate)
                break

    return queries


def _extract_metadata_from_pdf(pdf_text: str) -> dict:
    """
    Extract best-effort metadata from PDF text without any API call.

    Looks for year patterns (4-digit numbers 1900-2099) and author-like
    patterns. Returns a dict with the same keys as the API response,
    with None/[] for fields that can't be extracted.
    """
    import re

    # Try to find a year (4-digit number in plausible range)
    year = None
    year_match = re.search(r'\b(19[5-9]\d|20[0-2]\d)\b', pdf_text[:2000])
    if year_match:
        year = int(year_match.group(1))

    # Use the best title candidate we can find
    title = _extract_title_from_text(pdf_text)

    print(
        f"  → Using PDF-extracted metadata: year={year}, title={title!r}",
        file=sys.stderr,
    )

    return {
        "year": year,
        "venue": None,
        "citationCount": None,
        "authors": [],
        "title": title,
    }


def _query_by_doi(doi: str) -> dict | None:
    """
    GET https://api.semanticscholar.org/graph/v1/paper/{doi}
    ?fields=year,venue,citationCount,authors
    Returns parsed JSON dict or None on no-result / 429-exhausted.

    Raises:
        requests.HTTPError: on non-429 HTTP error responses.
        RuntimeError: on network-level failures.
    """
    return search_provider.query_by_doi(doi)


def _query_by_title(title: str) -> dict | None:
    """
    GET https://api.semanticscholar.org/graph/v1/paper/search
    ?query={title}&fields=year,venue,citationCount,authors&limit=1
    Returns first result dict or None on no results / 429-exhausted.

    Raises:
        requests.HTTPError: on non-429 HTTP error responses.
        RuntimeError: on network-level failures.
    """
    return search_provider.query_by_title(title)


def _extract_title_from_text(pdf_text: str) -> str | None:
    """
    Return the first plausible title line from pdf_text.

    A plausible title line:
      - Is not empty or whitespace-only
      - Is longer than 10 characters (filters out section labels like "ARTICLES")
      - Is not all-uppercase with fewer than 4 words (filters out journal headers)
      - Does not look like a page number or URL

    Returns None if pdf_text is empty/whitespace-only or no plausible line found.
    """
    if not pdf_text or not pdf_text.strip():
        return None

    for line in pdf_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Too short to be a title
        if len(stripped) <= 10:
            continue
        # All-caps single-word or short phrase (e.g. "ARTICLES", "RESEARCH")
        words = stripped.split()
        if stripped.isupper() and len(words) <= 4:
            continue
        # Looks like a URL
        if stripped.startswith("http://") or stripped.startswith("https://"):
            continue
        # Looks like a page number or DOI only
        if stripped.startswith("10.") and len(words) == 1:
            continue
        return stripped

    return None


def _prompt_manual_entry() -> dict:
    """
    Prompt the user via stdin for year, venue, citationCount, authors.
    Returns a dict with those four keys.
    """
    import sys

    print(
        "\n--- Manual metadata entry required ---\n"
        "The Semantic Scholar API did not return results. "
        "Please enter the paper metadata manually.\n"
        "(Press Enter to leave a field empty.)",
        file=sys.stderr,
    )

    # year
    raw_year = input("Year (e.g. 2024): ").strip()
    year: int | None = int(raw_year) if raw_year else None

    # venue
    raw_venue = input("Venue (e.g. NeurIPS 2024): ").strip()
    venue: str | None = raw_venue if raw_venue else None

    # citationCount
    raw_citations = input("Citation count: ").strip()
    citation_count: int | None = int(raw_citations) if raw_citations else None

    # authors — comma-separated names → list of {"name": ...} dicts
    raw_authors = input("Authors (comma-separated, e.g. Alice Smith, Bob Jones): ").strip()
    if raw_authors:
        authors = [{"name": name.strip()} for name in raw_authors.split(",") if name.strip()]
    else:
        authors = []

    return {
        "year": year,
        "venue": venue,
        "citationCount": citation_count,
        "authors": authors,
    }
