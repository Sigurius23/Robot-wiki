"""
tests/test_pdf_extractor.py — Tests for pdf_extractor.py and vendor/pdf_extractor.py.

Covers:
  - Property 6: Whitespace normalisation invariant
  - Property 7: Bibliography stripping removes all text from the first heading match
  - PyMuPDF exception re-raise includes pdf_path
  - Full-text return when no bibliography heading is present
  - Extraction with a minimal in-memory PDF fixture (or mock fitz.open)
"""

import re
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Ensure project root is on the path so imports work regardless of cwd.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vendor.pdf_extractor import _clean_text, _RE_WHITESPACE, _RE_NEWLINES, _RE_BIBLIOGRAPHY
from pdf_extractor import extract_text


# ---------------------------------------------------------------------------
# Property 6: Whitespace normalisation invariant
# ---------------------------------------------------------------------------

# Feature: literature-review-pipeline, Property 6
@given(st.text())
@settings(max_examples=100)
def test_whitespace_normalisation_invariant(text: str) -> None:
    """
    **Validates: Requirements 3.2**

    After applying the two normalisation regex steps, the output must contain:
      - No run of 3+ consecutive non-newline whitespace characters.
      - No run of 3+ consecutive newline characters.
    """
    # Apply the same two normalisation steps used in _clean_text.
    normalised = _RE_WHITESPACE.sub(" ", text)
    normalised = _RE_NEWLINES.sub("\n\n", normalised)

    # Assert no run of 3+ non-newline whitespace chars remains.
    assert re.search(r"[^\S\n]{3,}", normalised) is None, (
        f"Found 3+ non-newline whitespace chars in normalised output: {normalised!r}"
    )

    # Assert no run of 3+ consecutive newlines remains.
    assert re.search(r"\n{3,}", normalised) is None, (
        f"Found 3+ consecutive newlines in normalised output: {normalised!r}"
    )


# ---------------------------------------------------------------------------
# Property 7: Bibliography stripping removes all text from the first heading match
# ---------------------------------------------------------------------------

# Heading variants used for generation.
_HEADINGS = ["References", "Bibliography", "Works Cited"]


def _build_text_with_heading(prefix: str, heading: str, suffix: str) -> str:
    """Construct a text string that contains a bibliography heading on its own line."""
    # Ensure the heading is on its own line (surrounded by newlines).
    return f"{prefix}\n{heading}\n{suffix}"


# Feature: literature-review-pipeline, Property 7
@given(
    prefix=st.text(),
    heading=st.sampled_from(_HEADINGS),
    suffix=st.text(),
)
@settings(max_examples=100)
def test_bibliography_stripping_removes_text_from_heading(
    prefix: str, heading: str, suffix: str
) -> None:
    """
    **Validates: Requirements 3.3**

    For any text containing at least one bibliography heading on its own line,
    the cleaned output must contain no characters at or after the heading position.
    """
    text = _build_text_with_heading(prefix, heading, suffix)

    # Find where the heading actually appears in the constructed text so we can
    # verify the output is truncated at or before that position.
    match = _RE_BIBLIOGRAPHY.search(text)
    # The heading must be present (our construction guarantees this).
    assert match is not None, (
        f"Test construction error: heading not found in text: {text!r}"
    )
    expected_cutoff = match.start()

    result = _clean_text(text)

    # The result must be a prefix of the original text up to the heading.
    assert len(result) <= expected_cutoff, (
        f"Result is longer than expected cutoff {expected_cutoff}. "
        f"Result length: {len(result)}, result: {result!r}"
    )

    # The heading itself must not appear in the result.
    assert _RE_BIBLIOGRAPHY.search(result) is None, (
        f"Bibliography heading still present in result: {result!r}"
    )


# ---------------------------------------------------------------------------
# 2.5 Unit tests for pdf_extractor.py
# ---------------------------------------------------------------------------

class TestExtractTextErrorHandling(unittest.TestCase):
    """Test that PyMuPDF exceptions are re-raised as RuntimeError with pdf_path."""

    def test_fitz_open_exception_reraised_as_runtime_error(self) -> None:
        """
        **Validates: Requirements 3.4**

        When fitz.open() raises any exception, extract_text must re-raise it
        as a RuntimeError whose message contains the pdf_path.
        """
        pdf_path = "/some/nonexistent/path/paper.pdf"

        with patch("vendor.pdf_extractor.fitz.open", side_effect=Exception("fitz error")):
            with self.assertRaises(RuntimeError) as ctx:
                extract_text(pdf_path)

        assert pdf_path in str(ctx.exception), (
            f"pdf_path not found in RuntimeError message: {ctx.exception}"
        )

    def test_fitz_open_exception_message_includes_pdf_path(self) -> None:
        """
        **Validates: Requirements 3.4**

        The RuntimeError message must include the exact pdf_path string.
        """
        pdf_path = "/tmp/my_special_paper.pdf"

        with patch("vendor.pdf_extractor.fitz.open", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError) as ctx:
                extract_text(pdf_path)

        assert pdf_path in str(ctx.exception), (
            f"Expected '{pdf_path}' in error message, got: {ctx.exception}"
        )


class TestExtractTextNoBibliography(unittest.TestCase):
    """Test that full text is returned when no bibliography heading is present."""

    def test_full_text_returned_when_no_bibliography(self) -> None:
        """
        **Validates: Requirements 3.5**

        When the extracted text contains no bibliography heading, the full
        (normalised) text must be returned.
        """
        raw_text = "Introduction\n\nThis is the body of the paper.\n\nConclusion\n\nFinal thoughts."

        mock_page = MagicMock()
        mock_page.get_text.return_value = raw_text

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.close = MagicMock()

        with patch("vendor.pdf_extractor.fitz.open", return_value=mock_doc):
            result = extract_text("/fake/path.pdf")

        # The result should contain the body text (no truncation).
        assert "Introduction" in result
        assert "Conclusion" in result
        assert "Final thoughts." in result

    def test_text_without_bibliography_heading_is_not_truncated(self) -> None:
        """
        **Validates: Requirements 3.5**

        Text that mentions 'references' in a non-heading context (e.g., mid-sentence)
        must not be truncated.
        """
        raw_text = "We use references to prior work throughout this paper.\n\nConclusion here."

        mock_page = MagicMock()
        mock_page.get_text.return_value = raw_text

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.close = MagicMock()

        with patch("vendor.pdf_extractor.fitz.open", return_value=mock_doc):
            result = extract_text("/fake/path.pdf")

        assert "Conclusion here." in result


class TestExtractTextWithMockedFitz(unittest.TestCase):
    """Test extraction with a mocked fitz.open."""

    def test_pages_are_concatenated(self) -> None:
        """
        **Validates: Requirements 3.4**

        Text from all pages must be concatenated in the result.
        """
        page1_text = "Page one content.\n"
        page2_text = "Page two content.\n"

        mock_page1 = MagicMock()
        mock_page1.get_text.return_value = page1_text

        mock_page2 = MagicMock()
        mock_page2.get_text.return_value = page2_text

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page1, mock_page2]))
        mock_doc.close = MagicMock()

        with patch("vendor.pdf_extractor.fitz.open", return_value=mock_doc):
            result = extract_text("/fake/multipage.pdf")

        assert "Page one content." in result
        assert "Page two content." in result

    def test_bibliography_section_is_stripped(self) -> None:
        """
        **Validates: Requirements 3.4, 3.5**

        Text after a bibliography heading must be stripped from the result.
        """
        raw_text = (
            "Abstract\n\nThis paper presents a novel approach.\n\n"
            "References\n\n"
            "[1] Smith, J. (2020). Some paper. Journal of Things.\n"
        )

        mock_page = MagicMock()
        mock_page.get_text.return_value = raw_text

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.close = MagicMock()

        with patch("vendor.pdf_extractor.fitz.open", return_value=mock_doc):
            result = extract_text("/fake/path.pdf")

        assert "Abstract" in result
        assert "novel approach" in result
        # The bibliography entry must not appear.
        assert "Smith, J." not in result

    def test_whitespace_is_normalised(self) -> None:
        """
        **Validates: Requirements 3.4**

        Runs of 3+ non-newline whitespace chars must be collapsed to a single space.
        """
        raw_text = "Word1   Word2    Word3\n"  # 3+ spaces between words

        mock_page = MagicMock()
        mock_page.get_text.return_value = raw_text

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.close = MagicMock()

        with patch("vendor.pdf_extractor.fitz.open", return_value=mock_doc):
            result = extract_text("/fake/path.pdf")

        assert re.search(r"[^\S\n]{3,}", result) is None, (
            f"Found 3+ non-newline whitespace in result: {result!r}"
        )

    def test_empty_pdf_returns_empty_string(self) -> None:
        """
        **Validates: Requirements 3.4**

        A PDF with no extractable text must return an empty string.
        """
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.close = MagicMock()

        with patch("vendor.pdf_extractor.fitz.open", return_value=mock_doc):
            result = extract_text("/fake/empty.pdf")

        assert result == ""
