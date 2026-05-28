"""
vendor/ — Self-contained, adapted modules transplanted from reference codebases.

Modules:
  search_provider  — Semantic Scholar API client with HTTP 429 retry/backoff.
                     Adapted from scholar-agent/src/scholar_agent/engine/search_providers/.
  pdf_extractor    — PyMuPDF-based text extraction with whitespace normalisation
                     and bibliography stripping.
                     Adapted from scholar-agent/src/scholar_agent/engine/academic/image_extractor.py.
  scoring          — Recency and citation-count scoring dimensions.
                     Adapted from scholar-agent/src/scholar_agent/engine/academic/scoring.py.

All modules are self-contained — no imports from the original reference repos.
"""
