"""
trust_scorer.py — Baseline trust score calculation.

Classifies the venue string into a tier, enriches with citation-count and
recency signals from vendor/scoring.py, and returns a final baseline integer
score in [1, 10].

Vendor source: adapted from
  scholar-agent/src/scholar_agent/engine/academic/scoring.py
  (recency and citation-count dimensions only)
"""

from vendor.scoring import recency_score, citation_score


# ---------------------------------------------------------------------------
# Tier keyword lists (checked in priority order: Tier 1-2 first)
# ---------------------------------------------------------------------------

_TIER_1_2_KEYWORDS = ["nature", "neurips", "icml", "pnas"]
_TIER_3_KEYWORDS = ["ieee", "springer", "elsevier"]
_TIER_4_KEYWORDS = ["arxiv", "ssrn"]

_TIER_1_2_BASE = 8
_TIER_3_BASE = 6
_TIER_4_BASE = 4
_DEFAULT_BASE = 4


def compute_baseline_trust_score(
    venue: str | None,
    year: int | None = None,
    citation_count: int | None = None,
) -> int:
    """
    Compute a baseline trust score (1–10) from venue, year, and citation count.

    Venue-tier heuristic (case-insensitive substring matching, priority order):
      Tier 1–2 (Nature, NeurIPS, ICML, PNAS)   → base score 8
      Tier 3   (IEEE, Springer, Elsevier)        → base score 6
      Tier 4   (arXiv, SSRN)                     → base score 4
      Default  (null, empty, unmatched)           → base score 4

    Enrichment formula:
      enrichment = recency_score(year) * 0.5 + citation_score(citation_count) * 0.5
      raw_score  = venue_base + enrichment * 2
      final      = max(1, min(10, round(raw_score)))

    Args:
        venue:          Publication venue string, or None if unknown.
        year:           Four-digit publication year, or None if unknown.
        citation_count: Number of citations, or None if unknown.

    Returns:
        Integer in the inclusive range [1, 10].
    """
    # Determine venue base score
    venue_base = _classify_venue(venue)

    # Compute enrichment from recency and citation signals (each in [0.0, 1.0])
    enrichment = recency_score(year) * 0.5 + citation_score(citation_count) * 0.5

    # Combine: venue_base + up to 2 bonus points from enrichment
    raw_score = venue_base + enrichment * 2

    # Clamp and round to integer in [1, 10]
    return max(1, min(10, round(raw_score)))


def _classify_venue(venue: str | None) -> int:
    """
    Return the base score for the given venue string.

    Tier matching is case-insensitive substring search, checked in priority
    order so that higher tiers always win over lower tiers.

    Args:
        venue: Publication venue string, or None.

    Returns:
        Integer base score: 8, 6, or 4.
    """
    if not venue or not venue.strip():
        return _DEFAULT_BASE

    lowered = venue.lower()

    # Tier 1–2 checked first (highest priority)
    if any(kw in lowered for kw in _TIER_1_2_KEYWORDS):
        return _TIER_1_2_BASE

    if any(kw in lowered for kw in _TIER_3_KEYWORDS):
        return _TIER_3_BASE

    if any(kw in lowered for kw in _TIER_4_KEYWORDS):
        return _TIER_4_BASE

    return _DEFAULT_BASE
