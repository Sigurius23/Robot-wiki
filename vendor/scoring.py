"""
vendor/scoring.py — Recency and citation-count scoring dimensions.

Adapted from scholar-agent/src/scholar_agent/engine/academic/scoring.py.

Stripped:
  - BM25 relevance dimension (requires local index)
  - LLM-call quality dimension (requires API key at scoring time)
  - Relevance and quality dimension functions
  - All MCP decorators and FastMCP imports

Retained:
  - Recency dimension: year-based score normalised to [0.0, 1.0]
  - Citation-count dimension: log-scaled score normalised to [0.0, 1.0]

These two dimensions are used by trust_scorer.py to enrich the venue-tier
baseline score.
"""

import math
import datetime


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Papers published this year or later receive the maximum recency score.
_CURRENT_YEAR: int = datetime.datetime.now().year

# Papers older than this many years receive the minimum recency score.
_MAX_AGE_YEARS: int = 10

# Citation count at which the citation score saturates (reaches 1.0).
_CITATION_SATURATION: int = 1000


# ---------------------------------------------------------------------------
# Public scoring dimensions
# ---------------------------------------------------------------------------

def recency_score(year: int | None) -> float:
    """
    Compute a recency score in [0.0, 1.0] based on publication year.

    Scoring logic:
      - year is None or in the future → 0.5 (neutral / unknown)
      - year >= current year          → 1.0 (maximum recency)
      - year <= current year - _MAX_AGE_YEARS → 0.0 (minimum recency)
      - otherwise                     → linear interpolation between 0.0 and 1.0

    Args:
        year: Four-digit publication year, or None if unknown.

    Returns:
        Float in [0.0, 1.0].
    """
    if year is None:
        return 0.5

    age = _CURRENT_YEAR - year
    if age <= 0:
        return 1.0
    if age >= _MAX_AGE_YEARS:
        return 0.0

    return 1.0 - (age / _MAX_AGE_YEARS)


def citation_score(citation_count: int | None) -> float:
    """
    Compute a citation-count score in [0.0, 1.0] using logarithmic scaling.

    Scoring logic:
      - citation_count is None or <= 0 → 0.0
      - citation_count >= _CITATION_SATURATION → 1.0
      - otherwise → log(citation_count + 1) / log(_CITATION_SATURATION + 1)

    The logarithmic scale prevents highly-cited papers from dominating while
    still rewarding papers with moderate citation counts.

    Args:
        citation_count: Number of citations, or None if unknown.

    Returns:
        Float in [0.0, 1.0].
    """
    if citation_count is None or citation_count <= 0:
        return 0.0

    if citation_count >= _CITATION_SATURATION:
        return 1.0

    return math.log(citation_count + 1) / math.log(_CITATION_SATURATION + 1)
