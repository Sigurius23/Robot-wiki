"""
vendor/pdf_extractor.py — PyMuPDF-based PDF text extraction.

Adapted from scholar-agent/src/scholar_agent/engine/academic/image_extractor.py.

Stripped:
  - @mcp.tool decorators and FastMCP imports
  - Knowledge-card and daily-workflow dependencies
  - Figure/image extraction logic

Retained:
  - fitz.open() page iteration and page.get_text() extraction
  - Whitespace normalisation (collapse 3+ non-newline whitespace, 3+ newlines)
  - Bibliography stripping (References / Bibliography / Works Cited headings)
"""

import re
import fitz  # PyMuPDF


# ---------------------------------------------------------------------------
# Regex patterns (compiled once at module load)
# ---------------------------------------------------------------------------

# Collapse 3 or more consecutive non-newline whitespace characters to one space.
_RE_WHITESPACE = re.compile(r"[^\S\n]{3,}")

# Collapse 3 or more consecutive newline characters to two newlines.
_RE_NEWLINES = re.compile(r"\n{3,}")

# Match a bibliography section heading on its own line (case-insensitive).
_RE_BIBLIOGRAPHY = re.compile(
    r"^\s*(References|Bibliography|Works\s+Cited)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_text(pdf_path: str) -> str:
    """
    Extract and clean text from all pages of a PDF file.

    Steps:
      1. Open ``pdf_path`` with ``fitz.open()``; re-raise any fitz exception
         as a ``RuntimeError`` with ``pdf_path`` in the message.
      2. Concatenate ``page.get_text()`` for all pages.
      3. Normalise whitespace: collapse runs of 3+ non-newline whitespace
         characters to a single space.
      4. Collapse runs of 3+ consecutive blank lines to one blank line.
      5. Strip bibliography: find the first line matching the heading pattern
         (References / Bibliography / Works Cited, case-insensitive) and
         truncate the text at that position.
      6. Return the cleaned text.

    Args:
        pdf_path: Absolute or relative path to the PDF file.

    Returns:
        Cleaned text string. May be empty if the PDF contains no extractable
        text.

    Raises:
        RuntimeError: If fitz raises during open or text extraction, re-raised
                      with ``pdf_path`` included in the message.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to open PDF '{pdf_path}': {exc}"
        ) from exc

    try:
        raw_pages = []
        for page in doc:
            try:
                raw_pages.append(page.get_text())
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to extract text from '{pdf_path}': {exc}"
                ) from exc
    finally:
        doc.close()

    text = "".join(raw_pages)
    return _clean_text(text)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """
    Apply whitespace normalisation and bibliography stripping to raw text.

    This function is intentionally exposed (not name-mangled) so that unit
    tests can exercise the cleaning logic independently of fitz.open().
    """
    # Step 1: Collapse 3+ non-newline whitespace to a single space.
    text = _RE_WHITESPACE.sub(" ", text)

    # Step 2: Collapse 3+ consecutive newlines to two newlines.
    text = _RE_NEWLINES.sub("\n\n", text)

    # Step 3: Strip bibliography section and everything after it.
    # To prevent early truncation of body text, only strip if the match occurs
    # in the second half of the document character length.
    match = _RE_BIBLIOGRAPHY.search(text)
    if match and match.start() > len(text) * 0.5:
        text = text[: match.start()]

    return text
