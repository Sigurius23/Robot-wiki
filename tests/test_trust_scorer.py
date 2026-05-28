"""
tests/test_trust_scorer.py — Tests for trust_scorer.py and vendor/scoring.py.

Covers:
  - Property 8: Trust score is always a valid integer in [1, 10]
  - Property 9: Trust score tier matching is correct and priority-ordered
  - Tier 1-2 keywords (Nature, NeurIPS, ICML, PNAS) → base score 8
  - Tier 3 keywords (IEEE, Springer, Elsevier) → base score 6
  - Tier 4 / default (arXiv, SSRN, None, empty, unmatched) → base score 4
  - Tier 1-2 wins over Tier 3 when both keywords are present
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from trust_scorer import compute_baseline_trust_score, _classify_venue


# ---------------------------------------------------------------------------
# Unit tests — specific examples
# ---------------------------------------------------------------------------

class TestClassifyVenue:
    """Unit tests for the internal _classify_venue helper."""

    # Tier 1-2 venues
    def test_nature_returns_8(self):
        assert _classify_venue("Nature") == 8

    def test_neurips_returns_8(self):
        assert _classify_venue("NeurIPS 2023") == 8

    def test_icml_returns_8(self):
        assert _classify_venue("ICML") == 8

    def test_pnas_returns_8(self):
        assert _classify_venue("PNAS") == 8

    def test_nature_case_insensitive(self):
        assert _classify_venue("NATURE COMMUNICATIONS") == 8

    def test_neurips_lowercase(self):
        assert _classify_venue("neurips") == 8

    # Tier 3 venues
    def test_ieee_returns_6(self):
        assert _classify_venue("IEEE Transactions") == 6

    def test_springer_returns_6(self):
        assert _classify_venue("Springer") == 6

    def test_elsevier_returns_6(self):
        assert _classify_venue("Elsevier") == 6

    def test_ieee_case_insensitive(self):
        assert _classify_venue("ieee access") == 6

    # Tier 4 venues
    def test_arxiv_returns_4(self):
        assert _classify_venue("arXiv") == 4

    def test_ssrn_returns_4(self):
        assert _classify_venue("SSRN") == 4

    def test_arxiv_lowercase(self):
        assert _classify_venue("arxiv preprint") == 4

    # Default / unmatched
    def test_none_returns_4(self):
        assert _classify_venue(None) == 4

    def test_empty_string_returns_4(self):
        assert _classify_venue("") == 4

    def test_whitespace_only_returns_4(self):
        assert _classify_venue("   ") == 4

    def test_unmatched_venue_returns_4(self):
        assert _classify_venue("Journal of Unknown Studies") == 4

    # Priority: Tier 1-2 wins over Tier 3
    def test_tier1_wins_over_tier3(self):
        # A hypothetical venue containing both "Nature" and "IEEE"
        assert _classify_venue("Nature IEEE Hybrid Journal") == 8


class TestComputeBaselineTrustScore:
    """Unit tests for compute_baseline_trust_score."""

    def test_returns_integer(self):
        result = compute_baseline_trust_score("Nature", 2023, 100)
        assert isinstance(result, int)

    def test_tier1_venue_no_enrichment(self):
        # Nature base=8, year=None → recency=0.5, citations=None → citation=0.0
        # enrichment = 0.5*0.5 + 0.0*0.5 = 0.25 → raw = 8.25 → round = 8
        result = compute_baseline_trust_score("Nature", None, None)
        assert result == 8

    def test_tier3_venue_no_enrichment(self):
        # IEEE base=6, year=None → recency=0.5, citations=None → citation=0.0
        # enrichment = 0.25 → raw = 6.25 → round = 6
        result = compute_baseline_trust_score("IEEE Transactions", None, None)
        assert result == 6

    def test_default_venue_no_enrichment(self):
        # base=4, enrichment=0.25 → raw=4.25 → round=4
        result = compute_baseline_trust_score(None, None, None)
        assert result == 4

    def test_high_citations_adds_bonus(self):
        # arXiv base=4, year=None (recency=0.5), citations=1000 (citation=1.0)
        # enrichment = 0.5*0.5 + 1.0*0.5 = 0.75 → raw = 4 + 1.5 = 5.5 → round = 6
        result = compute_baseline_trust_score("arXiv", None, 1000)
        assert result == 6

    def test_recent_paper_adds_bonus(self):
        import datetime
        current_year = datetime.datetime.now().year
        # Nature base=8, current year (recency=1.0), no citations (citation=0.0)
        # enrichment = 1.0*0.5 + 0.0*0.5 = 0.5 → raw = 8 + 1.0 = 9.0 → round = 9
        result = compute_baseline_trust_score("Nature", current_year, None)
        assert result == 9

    def test_max_enrichment_capped_at_10(self):
        import datetime
        current_year = datetime.datetime.now().year
        # Nature base=8, current year (recency=1.0), 1000+ citations (citation=1.0)
        # enrichment = 1.0 → raw = 8 + 2.0 = 10.0 → round = 10
        result = compute_baseline_trust_score("Nature", current_year, 1000)
        assert result == 10

    def test_result_in_range_1_to_10(self):
        for venue in [None, "", "arXiv", "IEEE", "Nature", "Unknown"]:
            result = compute_baseline_trust_score(venue, None, None)
            assert 1 <= result <= 10, f"Score {result} out of range for venue={venue!r}"

    def test_none_venue_same_as_empty(self):
        assert compute_baseline_trust_score(None) == compute_baseline_trust_score("")

    def test_default_args_work(self):
        # year and citation_count default to None
        result = compute_baseline_trust_score("Nature")
        assert isinstance(result, int)
        assert 1 <= result <= 10


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------

# Feature: literature-review-pipeline, Property 8: Trust score is always a valid integer in [1, 10]
@given(
    venue=st.one_of(st.none(), st.text()),
    year=st.one_of(st.none(), st.integers(min_value=1000, max_value=2100)),
    citation_count=st.one_of(st.none(), st.integers(min_value=0, max_value=100_000)),
)
@settings(max_examples=100)
def test_property_8_score_always_in_range(venue, year, citation_count):
    """
    **Validates: Requirements 4.1**

    For any venue string (including None, empty, or arbitrary text),
    compute_baseline_trust_score SHALL return an integer in [1, 10].
    """
    result = compute_baseline_trust_score(venue, year, citation_count)
    assert isinstance(result, int)
    assert 1 <= result <= 10


# Feature: literature-review-pipeline, Property 9: Trust score tier matching is correct and priority-ordered
@given(
    suffix=st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=30),
    prefix=st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=30),
)
@settings(max_examples=100)
def test_property_9_tier1_keywords_return_8(suffix, prefix):
    """
    **Validates: Requirements 4.2, 4.3, 4.4, 4.5**

    For any venue string containing a Tier 1-2 keyword, the score SHALL be 8
    (assuming no Tier 1-2 keyword is already present in prefix/suffix that
    would change the tier — we test each keyword in isolation).
    """
    for keyword in ["Nature", "NeurIPS", "ICML", "PNAS"]:
        venue = prefix + keyword + suffix
        result = compute_baseline_trust_score(venue, None, None)
        assert result == 8, (
            f"Expected 8 for Tier 1-2 venue {venue!r}, got {result}"
        )


@given(
    suffix=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)), max_size=30
    ).filter(lambda s: not any(
        kw in s.lower() for kw in ["nature", "neurips", "icml", "pnas"]
    )),
    prefix=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)), max_size=30
    ).filter(lambda s: not any(
        kw in s.lower() for kw in ["nature", "neurips", "icml", "pnas"]
    )),
)
@settings(max_examples=100)
def test_property_9_tier3_keywords_return_6(suffix, prefix):
    """
    **Validates: Requirements 4.2, 4.3, 4.4, 4.5**

    For any venue string containing a Tier 3 keyword (and no Tier 1-2 keyword),
    the score SHALL be 6.
    """
    for keyword in ["IEEE", "Springer", "Elsevier"]:
        venue = prefix + keyword + suffix
        result = compute_baseline_trust_score(venue, None, None)
        assert result == 6, (
            f"Expected 6 for Tier 3 venue {venue!r}, got {result}"
        )


@given(venue=st.one_of(st.none(), st.just(""), st.just("   ")))
@settings(max_examples=20)
def test_property_9_null_or_empty_venue_returns_4(venue):
    """
    **Validates: Requirements 4.5**

    For null, empty, or whitespace-only venue, the score SHALL be 4 (default).
    """
    result = compute_baseline_trust_score(venue, None, None)
    assert result == 4, f"Expected 4 for venue={venue!r}, got {result}"
