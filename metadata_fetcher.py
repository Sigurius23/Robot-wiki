"""
metadata_fetcher.py — Semantic Scholar metadata retrieval wrapper.

Thin wrapper over vendor/search_provider.py. Exposes ``fetch_metadata``
to the pipeline and owns the manual fallback prompt logic.

Vendor source: adapted from
  scholar-agent/src/scholar_agent/engine/search_providers/
  (Semantic Scholar provider)
"""

import re
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
      - arXiv ID (converted to DOI format: 10.48550/arXiv.XXXX.XXXXX)

    Searches in the first 3000 and last 1000 characters of the PDF text
    where DOIs and arXiv IDs typically appear.
    """
    # Search in first 3000 chars where DOI/arXiv usually appears (header/footer)
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

    # Match arXiv ID and convert to DOI format for Semantic Scholar lookup.
    # arXiv IDs on Semantic Scholar are resolvable via DOI:10.48550/arXiv.{id}
    # Matches: arXiv:2401.01735v1, arXiv:2401.01735, arxiv.org/abs/2401.01735
    arxiv_pattern = re.search(
        r'(?:arXiv:|arxiv\.org/abs/)(\d{4}\.\d{4,})(?:v\d+)?',
        search_text,
        re.IGNORECASE,
    )
    if arxiv_pattern:
        arxiv_id = arxiv_pattern.group(1)
        return f"10.48550/arXiv.{arxiv_id}"

    return None


def _build_search_queries(title: str | None, pdf_text: str) -> list[str]:
    """
    Build a list of progressively simpler search queries to try in order.

    1. Full extracted title
    2. First 6 words of title
    3. First 4 words of title
    4. First substantial sentence from the abstract (after "ABSTRACT" heading)
    5. First 8 words from a non-header PDF body line
    """
    queries = []

    if title:
        queries.append(title)
        words = title.split()
        if len(words) > 6:
            queries.append(" ".join(words[:6]))
        if len(words) > 4:
            queries.append(" ".join(words[:4]))

    # Try extracting text from after the ABSTRACT heading for a better fallback.
    # This avoids picking up author/affiliation lines as search queries.
    if pdf_text:
        abstract_match = re.search(
            r'\bABSTRACT\b[\s:—–-]*\n*((?:.{20,}\n)+)',
            pdf_text[:5000],
            re.IGNORECASE,
        )
        if abstract_match:
            abstract_text = abstract_match.group(1).strip()
            # Take first meaningful sentence (up to 12 words)
            first_sentence = abstract_text.split(".")[0].strip()
            words = first_sentence.split()
            if len(words) >= 4:
                candidate = " ".join(words[:12])
                if candidate and candidate not in queries:
                    queries.append(candidate)

        # Generic fallback: first substantial non-header line from PDF body
        lines = [l.strip() for l in pdf_text.splitlines() if len(l.strip()) > 30]
        for line in lines[:15]:
            # Skip lines that look like metadata (contain @, arXiv, DOI, URLs)
            if re.search(r'[@]|arXiv:|doi\.org|https?://|^\d+\s', line, re.IGNORECASE):
                continue
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
    Return the paper title extracted from the PDF text.

    Skips known non-title lines commonly found at the top of academic PDFs:
      - arXiv watermarks ("Preview")
      - Conference labels ("Published as a conference paper at...")
      - arXiv ID lines ("arXiv:2401.01735v1  [cs.GT]  ...")
      - Section headers ("ABSTRACT", "Introduction")
      - Author / affiliation lines
      - Very short lines likely to be metadata labels (< 8 chars)

    Returns None if pdf_text is empty or no title-like line is found.
    """
    if not pdf_text or not pdf_text.strip():
        return None

    # Combined pattern for known non-title lines
    _NON_TITLE = re.compile(
        r'^Preview$|'                          # arXiv watermark
        r'^Published as a conference paper at|' # conference label
        r'^arXiv:\d{4}\.\d{4,}|'               # arXiv ID line
        r'^ABSTRACT$|'                          # section header
        r'^arxiv\.org/abs/|'                    # arXiv URL
        r'^https?://|'                           # URL line
        r'^doi\.org/',                           # DOI URL
        re.IGNORECASE,
    )

    # Author lines typically contain email addresses
    _AUTHOR = re.compile(r'.+@.+\.\w+')
    # Affiliation lines: start with a digit followed by institution indicators
    _AFFILIATION = re.compile(
        r'^\d+\s*'
        r'(University|Institute|College|Laboratory|School|Department|'
        r'Centre|Center|Inc\.|Ltd\.|Lab|Corp\.|'
        r'Tencent|Google|Microsoft|OpenAI|DeepMind|Meta|Amazon|IBM|'
        r'Chinese|Beijing|Shanghai|Shenzhen|'
        r'ETH|NUS|MIT|CMU|Stanford)',
        re.IGNORECASE,
    )

    lines = [l.strip() for l in pdf_text.splitlines()]

    for line in lines:
        if not line:
            continue

        # Skip very short lines (likely labels, page numbers, etc.)
        if len(line) < 8:
            continue

        # Skip known non-title patterns
        if _NON_TITLE.match(line):
            continue

        # Skip author/affiliation lines
        if _AUTHOR.search(line) or _AFFILIATION.match(line):
            continue

        # First plausible title line found
        return line

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
