"""
tests/test_metadata_fetcher.py — Tests for metadata_fetcher.py and vendor/search_provider.py.

Covers:
  - Property 3: Title extraction returns the first non-empty line
  - Property 4: Metadata extraction preserves all four required fields
  - Property 5: HTTP error status code always appears in the warning message
  - Mock requests.get for DOI lookup, title search, 429 retry, and no-results path
  - _prompt_manual_entry with mocked input()
"""

import pytest
from metadata_fetcher import _extract_title_from_text


# ---------------------------------------------------------------------------
# Unit tests for _extract_title_from_text
# ---------------------------------------------------------------------------

class TestExtractTitleFromText:
    def test_returns_none_for_none_input(self):
        assert _extract_title_from_text(None) is None

    def test_returns_none_for_empty_string(self):
        assert _extract_title_from_text("") is None

    def test_returns_none_for_whitespace_only(self):
        assert _extract_title_from_text("   \n\t\n  ") is None

    def test_returns_first_line_of_simple_text(self):
        assert _extract_title_from_text("Hello World\nSecond line") == "Hello World"

    def test_skips_leading_blank_lines(self):
        text = "\n\n  \nActual Title\nBody text"
        assert _extract_title_from_text(text) == "Actual Title"

    def test_strips_whitespace_from_returned_line(self):
        text = "  Padded Title  \nSecond line"
        assert _extract_title_from_text(text) == "Padded Title"

    def test_single_non_empty_line(self):
        assert _extract_title_from_text("Only Line") == "Only Line"

    def test_single_line_with_surrounding_whitespace(self):
        assert _extract_title_from_text("  \n  Title  \n  ") == "Title"

    def test_returns_none_when_all_lines_are_whitespace(self):
        assert _extract_title_from_text("   \n   \n   ") is None

    def test_first_line_wins_over_subsequent_lines(self):
        text = "First Title\nSecond Title\nThird Title"
        assert _extract_title_from_text(text) == "First Title"

    def test_handles_windows_line_endings(self):
        text = "\r\nAttention Is All You Need\r\nAbstract..."
        assert _extract_title_from_text(text) == "Attention Is All You Need"

    def test_handles_tab_only_lines_as_blank(self):
        text = "\t\nReal Title\nBody"
        assert _extract_title_from_text(text) == "Real Title"


# ---------------------------------------------------------------------------
# Unit tests for _prompt_manual_entry
# ---------------------------------------------------------------------------

from unittest.mock import patch
from metadata_fetcher import _prompt_manual_entry


class TestPromptManualEntry:
    """Tests for _prompt_manual_entry() — mocks input() to avoid stdin interaction."""

    def _run(self, inputs: list[str]) -> dict:
        """Helper: run _prompt_manual_entry with a sequence of mocked input() responses."""
        with patch("builtins.input", side_effect=inputs):
            return _prompt_manual_entry()

    # --- Return structure ---

    def test_returns_dict_with_four_keys(self):
        result = self._run(["2024", "NeurIPS", "42", "Alice Smith"])
        assert set(result.keys()) == {"year", "venue", "citationCount", "authors"}

    # --- year ---

    def test_year_parsed_as_int(self):
        result = self._run(["2024", "", "", ""])
        assert result["year"] == 2024
        assert isinstance(result["year"], int)

    def test_year_empty_gives_none(self):
        result = self._run(["", "", "", ""])
        assert result["year"] is None

    # --- venue ---

    def test_venue_returned_as_string(self):
        result = self._run(["", "NeurIPS 2024", "", ""])
        assert result["venue"] == "NeurIPS 2024"

    def test_venue_empty_gives_none(self):
        result = self._run(["", "", "", ""])
        assert result["venue"] is None

    # --- citationCount ---

    def test_citation_count_parsed_as_int(self):
        result = self._run(["", "", "99", ""])
        assert result["citationCount"] == 99
        assert isinstance(result["citationCount"], int)

    def test_citation_count_empty_gives_none(self):
        result = self._run(["", "", "", ""])
        assert result["citationCount"] is None

    # --- authors ---

    def test_authors_empty_gives_empty_list(self):
        result = self._run(["", "", "", ""])
        assert result["authors"] == []

    def test_single_author_parsed_correctly(self):
        result = self._run(["", "", "", "Alice Smith"])
        assert result["authors"] == [{"name": "Alice Smith"}]

    def test_multiple_authors_parsed_correctly(self):
        result = self._run(["", "", "", "Alice Smith, Bob Jones, Carol White"])
        assert result["authors"] == [
            {"name": "Alice Smith"},
            {"name": "Bob Jones"},
            {"name": "Carol White"},
        ]

    def test_authors_whitespace_stripped(self):
        result = self._run(["", "", "", "  Alice Smith ,  Bob Jones  "])
        assert result["authors"] == [{"name": "Alice Smith"}, {"name": "Bob Jones"}]

    def test_authors_empty_segments_ignored(self):
        # Extra commas should not produce empty-name entries
        result = self._run(["", "", "", "Alice Smith,,Bob Jones"])
        assert result["authors"] == [{"name": "Alice Smith"}, {"name": "Bob Jones"}]

    # --- header printed to stderr ---

    def test_header_printed_to_stderr(self, capsys):
        self._run(["", "", "", ""])
        captured = capsys.readouterr()
        assert "Manual metadata entry required" in captured.err

    # --- full round-trip ---

    def test_full_entry_round_trip(self):
        result = self._run(["2023", "ICML", "150", "Jane Doe, John Smith"])
        assert result == {
            "year": 2023,
            "venue": "ICML",
            "citationCount": 150,
            "authors": [{"name": "Jane Doe"}, {"name": "John Smith"}],
        }


# ===========================================================================
# Property-Based Tests
# ===========================================================================

from hypothesis import given, settings
import hypothesis.strategies as st


# ---------------------------------------------------------------------------
# Property 3: Title extraction returns the first non-empty line
# Feature: literature-review-pipeline, Property 3
# Validates: Requirements 2.2, 2.7
# ---------------------------------------------------------------------------

# Feature: literature-review-pipeline, Property 3
@given(st.text())
@settings(max_examples=100)
def test_property3_title_extraction_first_non_empty_line(text):
    """
    **Validates: Requirements 2.2, 2.7**

    For any text string, _extract_title_from_text must return:
    - The first non-blank (non-whitespace-only) line, stripped of leading/trailing whitespace
    - None if all lines are blank/empty or the string is empty
    """
    result = _extract_title_from_text(text)

    lines = text.splitlines()
    non_blank_lines = [line for line in lines if line.strip()]

    if not non_blank_lines:
        # All lines blank or string is empty — must return None
        assert result is None, (
            f"Expected None for all-blank input, got {result!r}"
        )
    else:
        # Must return the first non-blank line, stripped
        expected = non_blank_lines[0].strip()
        assert result == expected, (
            f"Expected {expected!r}, got {result!r}"
        )


# ---------------------------------------------------------------------------
# Property 4: Metadata extraction preserves all four required fields
# Feature: literature-review-pipeline, Property 4
# Validates: Requirements 2.3
# ---------------------------------------------------------------------------

import io
import json
import requests
from contextlib import redirect_stderr
from unittest.mock import patch, MagicMock
from metadata_fetcher import fetch_metadata

# Strategy: generate arbitrary values for each of the four required fields
_year_strategy = st.one_of(st.none(), st.integers(min_value=1900, max_value=2100))
_venue_strategy = st.one_of(st.none(), st.text(max_size=100))
_citation_strategy = st.one_of(st.none(), st.integers(min_value=0, max_value=1_000_000))
_authors_strategy = st.lists(
    st.fixed_dictionaries({"name": st.text(max_size=50)}),
    max_size=10,
)


# Feature: literature-review-pipeline, Property 4
@given(
    year=_year_strategy,
    venue=_venue_strategy,
    citation_count=_citation_strategy,
    authors=_authors_strategy,
)
@settings(max_examples=100)
def test_property4_metadata_fields_preserved(year, venue, citation_count, authors):
    """
    **Validates: Requirements 2.3**

    For any dict containing year, venue, citationCount, authors returned by the
    Semantic Scholar API, fetch_metadata must return all four fields with their
    original values unchanged.
    """
    api_response = {
        "year": year,
        "venue": venue,
        "citationCount": citation_count,
        "authors": authors,
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = api_response

    with patch("vendor.search_provider.requests.get", return_value=mock_response):
        result = fetch_metadata(doi="10.1234/test", pdf_text="")

    assert "year" in result, "Missing 'year' field"
    assert "venue" in result, "Missing 'venue' field"
    assert "citationCount" in result, "Missing 'citationCount' field"
    assert "authors" in result, "Missing 'authors' field"

    assert result["year"] == year, f"year changed: expected {year!r}, got {result['year']!r}"
    assert result["venue"] == venue, f"venue changed: expected {venue!r}, got {result['venue']!r}"
    assert result["citationCount"] == citation_count, (
        f"citationCount changed: expected {citation_count!r}, got {result['citationCount']!r}"
    )
    assert result["authors"] == authors, (
        f"authors changed: expected {authors!r}, got {result['authors']!r}"
    )


# ---------------------------------------------------------------------------
# Property 5: HTTP error status code always appears in the warning message
# Feature: literature-review-pipeline, Property 5
# Validates: Requirements 2.5
# ---------------------------------------------------------------------------

# Feature: literature-review-pipeline, Property 5
@given(st.integers(min_value=400, max_value=599).filter(lambda x: x != 429))
@settings(max_examples=100)
def test_property5_http_error_status_in_warning(status_code):
    """
    **Validates: Requirements 2.5**

    For any non-429 HTTP error status code (400–599), when the Semantic Scholar
    API returns that code, the warning printed to stderr must contain the exact
    status code as a substring.
    """
    mock_response = MagicMock()
    mock_response.status_code = status_code
    # Make raise_for_status() raise an HTTPError with the response attached
    http_error = requests.HTTPError(response=mock_response)
    mock_response.raise_for_status.side_effect = http_error

    stderr_capture = io.StringIO()
    with patch("vendor.search_provider.requests.get", return_value=mock_response):
        with patch("builtins.input", return_value=""):
            with redirect_stderr(stderr_capture):
                fetch_metadata(doi="10.1234/test", pdf_text="")

    stderr_output = stderr_capture.getvalue()
    assert str(status_code) in stderr_output, (
        f"Status code {status_code} not found in stderr: {stderr_output!r}"
    )


# ===========================================================================
# Unit Tests for metadata_fetcher.py (Task 3.8)
# Validates: Requirements 2.1, 2.2, 2.4, 2.5, 2.6
# ===========================================================================

import time


class TestFetchMetadataDoiLookup:
    """Mock requests.get for DOI lookup success path."""

    def test_doi_lookup_success_returns_all_fields(self):
        """Requirement 2.1: DOI lookup returns year, venue, citationCount, authors."""
        api_response = {
            "year": 2023,
            "venue": "NeurIPS",
            "citationCount": 42,
            "authors": [{"name": "Alice"}, {"name": "Bob"}],
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = api_response

        with patch("vendor.search_provider.requests.get", return_value=mock_resp):
            result = fetch_metadata(doi="10.1234/abc", pdf_text="")

        assert result["year"] == 2023
        assert result["venue"] == "NeurIPS"
        assert result["citationCount"] == 42
        assert result["authors"] == [{"name": "Alice"}, {"name": "Bob"}]

    def test_doi_lookup_uses_doi_not_title(self):
        """When DOI is provided, the API is called with the DOI (not a title search)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "year": 2020, "venue": "ICML", "citationCount": 10, "authors": []
        }

        with patch("vendor.search_provider.requests.get", return_value=mock_resp) as mock_get:
            fetch_metadata(doi="10.9999/xyz", pdf_text="Some title\nBody text")

        called_url = mock_get.call_args[0][0]
        assert "10.9999/xyz" in called_url, f"DOI not in URL: {called_url}"
        assert "search" not in called_url, "Should not use title search when DOI is provided"


class TestFetchMetadataTitleSearch:
    """Mock requests.get for title search success path (no DOI)."""

    def test_title_search_uses_first_line_as_query(self):
        """Requirement 2.2: Title extracted from PDF text is used as search query."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{
                "year": 2021,
                "venue": "ICML",
                "citationCount": 5,
                "authors": [{"name": "Carol"}],
            }]
        }

        with patch("vendor.search_provider.requests.get", return_value=mock_resp) as mock_get:
            result = fetch_metadata(doi=None, pdf_text="Attention Is All You Need\nAbstract...")

        called_url = mock_get.call_args[0][0]
        assert "search" in called_url, "Should use title search endpoint"
        params = mock_get.call_args[1].get("params") or mock_get.call_args[0][1]
        assert "Attention Is All You Need" in params.get("query", "")

    def test_title_search_returns_correct_fields(self):
        """Requirement 2.3: Title search result fields are returned unchanged."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{
                "year": 2019,
                "venue": "ICLR",
                "citationCount": 100,
                "authors": [{"name": "Dave"}],
            }]
        }

        with patch("vendor.search_provider.requests.get", return_value=mock_resp):
            result = fetch_metadata(doi=None, pdf_text="BERT: Pre-training\nAbstract")

        assert result["year"] == 2019
        assert result["venue"] == "ICLR"
        assert result["citationCount"] == 100
        assert result["authors"] == [{"name": "Dave"}]

    def test_no_doi_empty_title_falls_back_to_manual(self, capsys):
        """Requirement 2.7: Empty PDF text triggers warning and manual fallback."""
        with patch("builtins.input", return_value=""):
            result = fetch_metadata(doi=None, pdf_text="   \n\t\n  ")

        captured = capsys.readouterr()
        assert "warning" in captured.err.lower() or "could not" in captured.err.lower()
        assert set(result.keys()) == {"year", "venue", "citationCount", "authors"}

    def test_no_results_falls_back_to_manual(self, capsys):
        """Requirement 2.4: No results from API triggers warning and manual fallback."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": []}

        with patch("vendor.search_provider.requests.get", return_value=mock_resp):
            with patch("builtins.input", return_value=""):
                result = fetch_metadata(doi=None, pdf_text="Some Paper Title\nBody")

        captured = capsys.readouterr()
        assert "no results" in captured.err.lower() or "warning" in captured.err.lower()
        assert set(result.keys()) == {"year", "venue", "citationCount", "authors"}


class TestFetchMetadata429Retry:
    """Mock requests.get to verify exactly 3 retries on HTTP 429."""

    def test_429_retries_exactly_three_times_then_falls_back(self, capsys):
        """
        Requirement 2.6: On HTTP 429, the fetcher retries up to 3 times (5s wait each),
        then falls back to manual entry.
        """
        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_resp_429

        with patch("vendor.search_provider.requests.get", side_effect=side_effect):
            with patch("vendor.search_provider.time.sleep") as mock_sleep:
                with patch("builtins.input", return_value=""):
                    result = fetch_metadata(doi="10.1234/rate-limited", pdf_text="")

        # Should have been called exactly _MAX_RETRIES (3) times
        assert call_count == 3, f"Expected 3 retries, got {call_count}"
        # Should have slept between retries: 2 sleeps for 3 attempts
        assert mock_sleep.call_count == 2, (
            f"Expected 2 sleep calls (between 3 attempts), got {mock_sleep.call_count}"
        )
        # Each sleep should be 5 seconds
        for call in mock_sleep.call_args_list:
            assert call[0][0] == 5, f"Expected 5s sleep, got {call[0][0]}s"
        # Should fall back to manual entry
        assert set(result.keys()) == {"year", "venue", "citationCount", "authors"}

    def test_429_then_success_returns_data(self):
        """After a 429 retry, a subsequent 200 response returns the data."""
        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429

        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200
        mock_resp_200.json.return_value = {
            "year": 2022, "venue": "CVPR", "citationCount": 77, "authors": []
        }

        responses = iter([mock_resp_429, mock_resp_200])

        with patch("vendor.search_provider.requests.get", side_effect=lambda *a, **kw: next(responses)):
            with patch("vendor.search_provider.time.sleep"):
                result = fetch_metadata(doi="10.1234/retry-success", pdf_text="")

        assert result["year"] == 2022
        assert result["venue"] == "CVPR"


class TestFetchMetadataHttpErrors:
    """Mock requests.get for non-429 HTTP error paths."""

    def test_http_error_prints_status_code_to_stderr(self, capsys):
        """Requirement 2.5: Non-429 HTTP error status code appears in stderr warning."""
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        http_error = requests.HTTPError(response=mock_resp)
        mock_resp.raise_for_status.side_effect = http_error

        with patch("vendor.search_provider.requests.get", return_value=mock_resp):
            with patch("builtins.input", return_value=""):
                fetch_metadata(doi="10.1234/error", pdf_text="")

        captured = capsys.readouterr()
        assert "503" in captured.err

    def test_http_error_falls_back_to_manual_entry(self):
        """Requirement 2.5: HTTP error triggers manual fallback with correct keys."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        http_error = requests.HTTPError(response=mock_resp)
        mock_resp.raise_for_status.side_effect = http_error

        with patch("vendor.search_provider.requests.get", return_value=mock_resp):
            with patch("builtins.input", return_value=""):
                result = fetch_metadata(doi="10.1234/notfound", pdf_text="")

        assert set(result.keys()) == {"year", "venue", "citationCount", "authors"}
