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

    Returns a dict with keys: year, venue, citationCount, authors.
    Falls back to manual entry on API failure or no results.

    Args:
        doi:      DOI string if provided by user, else None.
        pdf_text: Extracted PDF text; first page used for title extraction
                  when doi is None.
    """
    if doi is not None:
        try:
            result = _query_by_doi(doi)
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            print(
                f"Warning: Semantic Scholar API returned HTTP {status_code} for DOI '{doi}'.",
                file=sys.stderr,
            )
            return _prompt_manual_entry()
        except RuntimeError as exc:
            print(
                f"Warning: Network error while fetching metadata for DOI '{doi}': {exc}",
                file=sys.stderr,
            )
            return _prompt_manual_entry()

        if result is None:
            print(
                f"Warning: Semantic Scholar rate limit exhausted for DOI '{doi}'.",
                file=sys.stderr,
            )
            return _prompt_manual_entry()

        return result

    # No DOI — fall back to title-based search.
    title = _extract_title_from_text(pdf_text)
    if title is None:
        print(
            "Warning: Could not extract title from PDF text; falling back to manual entry.",
            file=sys.stderr,
        )
        return _prompt_manual_entry()

    try:
        result = _query_by_title(title)
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        print(
            f"Warning: Semantic Scholar API returned HTTP {status_code} for title query '{title}'.",
            file=sys.stderr,
        )
        return _prompt_manual_entry()
    except RuntimeError as exc:
        print(
            f"Warning: Network error while fetching metadata for title '{title}': {exc}",
            file=sys.stderr,
        )
        return _prompt_manual_entry()

    if result is None:
        print(
            f"Warning: No results found for title query '{title}'.",
            file=sys.stderr,
        )
        return _prompt_manual_entry()

    return result


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
    Return the first non-empty, non-whitespace line of pdf_text,
    treated as the paper title. Returns None if pdf_text is empty
    or whitespace-only.
    """
    if not pdf_text or not pdf_text.strip():
        return None

    for line in pdf_text.splitlines():
        if line.strip():
            return line.strip()

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
