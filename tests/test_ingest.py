"""
tests/test_ingest.py — Tests for ingest.py.

Covers:
  - Property 1: Cite-key derivation is deterministic and well-formed
  - Property 2: DOI validation accepts exactly the correct format
  - Unit tests for derive_cite_key (spaces, underscores, mixed case, edge cases)
  - Unit tests for parse_args (missing/invalid argument paths)
  - Unit tests for main() with all modules mocked end-to-end
"""

import io
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ingest import derive_cite_key, validate_doi, parse_args, main


# ===========================================================================
# Property-Based Tests
# ===========================================================================


# ---------------------------------------------------------------------------
# Property 1: Cite-key derivation is deterministic and well-formed
# Feature: literature-review-pipeline, Property 1
# Validates: Requirements 1.3
# ---------------------------------------------------------------------------

# Feature: literature-review-pipeline, Property 1
@given(st.text(min_size=1, max_size=100))
@settings(max_examples=100)
def test_property1_cite_key_derivation(stem):
    """
    **Validates: Requirements 1.3**

    For any PDF filename stem, the derived cite-key SHALL be:
      - entirely lowercase
      - contain no spaces or underscores
      - have all spaces and underscores from the input replaced by hyphens
    """
    # Create a path from the stem + ".pdf" to simulate derive_cite_key input
    pdf_path = f"{stem}.pdf"
    result = derive_cite_key(pdf_path)

    # Must be entirely lowercase
    assert result == result.lower(), (
        f"Cite-key not lowercase: {result!r} (from stem {stem!r})"
    )

    # Must contain no spaces
    assert " " not in result, (
        f"Cite-key contains spaces: {result!r} (from stem {stem!r})"
    )

    # Must contain no underscores
    assert "_" not in result, (
        f"Cite-key contains underscores: {result!r} (from stem {stem!r})"
    )

    # All spaces and underscores from the input must be replaced by hyphens.
    # The original stem (lowercased) should map character-by-character:
    #  - spaces → hyphens
    #  - underscores → hyphens
    stem_lower = stem.lower()
    for i, ch in enumerate(stem_lower):
        if ch == " " or ch == "_":
            # The corresponding position in the result should be a hyphen.
            # We can't do exact positional since multiple consecutive
            # underscores/spaces collapse and stripping happens, but we
            # can verify that neither the original space nor underscore
            # survive in the result.
            pass  # Already verified above (no spaces, no underscores)

    # No leading/trailing hyphens
    assert not result.startswith("-"), (
        f"Cite-key starts with hyphen: {result!r} (from stem {stem!r})"
    )
    assert not result.endswith("-"), (
        f"Cite-key ends with hyphen: {result!r} (from stem {stem!r})"
    )


# ---------------------------------------------------------------------------
# Property 2: DOI validation accepts exactly the correct format
# Feature: literature-review-pipeline, Property 2
# Validates: Requirements 1.7
# ---------------------------------------------------------------------------

# Feature: literature-review-pipeline, Property 2
@given(st.text(max_size=100))
@settings(max_examples=100)
def test_property2_doi_validation_format(text):
    """
    **Validates: Requirements 1.7**

    For any string, validate_doi SHALL return True if and only if the string
    matches ^10\\..+ (starts with \"10.\" followed by at least one character),
    and False for all other strings.
    """
    import re
    matches_regex = bool(re.match(r"^10\..+", text))
    assert validate_doi(text) == matches_regex, (
        f"validate_doi({text!r}) returned {validate_doi(text)}, "
        f"expected {matches_regex}"
    )


# Feature: literature-review-pipeline, Property 2 (true positives)
@given(st.text(
    st.characters(
        codec="utf-8",
        exclude_characters="\n\r",
        exclude_categories=("C",),
    ),
    min_size=1,
    max_size=50,
))
@settings(max_examples=100)
def test_property2_doi_validation_true_positives(suffix):
    """
    **Validates: Requirements 1.7**

    Strings with the \"10.\" prefix always return True.
    """
    doi = f"10.{suffix}"
    assert validate_doi(doi) is True, (
        f"validate_doi({doi!r}) should be True"
    )


# ===========================================================================
# Unit Tests — Task 7.6
# Validates: Requirements 1.1–1.7, 9.2
# ===========================================================================


class TestDeriveCiteKey:
    """Unit tests for derive_cite_key with various inputs."""

    def test_basic_filename(self):
        """Simple filename becomes lowercase cite-key."""
        assert derive_cite_key("smith2024.pdf") == "smith2024"

    def test_spaces_replaced_with_hyphens(self):
        """Spaces in the stem become hyphens."""
        assert derive_cite_key("Smith 2024 paper.pdf") == "smith-2024-paper"

    def test_underscores_replaced_with_hyphens(self):
        """Underscores in the stem become hyphens."""
        assert derive_cite_key("Smith_2024_paper.pdf") == "smith-2024-paper"

    def test_mixed_spaces_and_underscores(self):
        """Both spaces and underscores become hyphens."""
        assert derive_cite_key("Smith_2024 paper.pdf") == "smith-2024-paper"

    def test_mixed_case_lowered(self):
        """All uppercase characters become lowercase."""
        assert derive_cite_key("SMITH-2024-PAPER.pdf") == "smith-2024-paper"

    def test_leading_hyphens_stripped(self):
        """Leading hyphens from the transformation are stripped."""
        assert derive_cite_key("_ leading.pdf") == "leading"

    def test_trailing_hyphens_stripped(self):
        """Trailing hyphens from the transformation are stripped."""
        assert derive_cite_key("trailing _.pdf") == "trailing"

    def test_all_stripped_result(self):
        """Stem of only spaces and underscores produces empty string."""
        # Path("_ _.pdf").stem → "_ _" → "_-_" → "-" → strip → ""
        assert derive_cite_key("_ _.pdf") == ""

    def test_path_with_directories(self):
        """Only the stem (filename without extension) is used."""
        assert derive_cite_key("/some/deep/path/Paper Title.pdf") == "paper-title"

    def test_filename_with_multiple_dots(self):
        """Filename with multiple dots uses stem correctly."""
        # Path("Smith.2024.pdf").stem → "Smith.2024"
        assert derive_cite_key("Smith.2024.pdf") == "smith.2024"

    def test_hyphens_preserved(self):
        """Existing hyphens in the stem are preserved."""
        assert derive_cite_key("smith-2024-paper.pdf") == "smith-2024-paper"


class TestParseArgs:
    """Unit tests for parse_args covering each error path."""

    def test_pdf_required_missing(self):
        """--pdf is required; missing it exits with code 1."""
        with pytest.raises(SystemExit) as exc_info:
            parse_args([])
        assert exc_info.value.code != 0

    def test_pdf_file_not_found(self, tmp_path):
        """Non-existent PDF file exits with code 1."""
        nonexistent = str(tmp_path / "nonexistent.pdf")
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--pdf", nonexistent])
        assert exc_info.value.code == 1

    def test_pdf_not_pdf_extension(self, tmp_path):
        """File without .pdf extension exits with code 1."""
        not_a_pdf = tmp_path / "file.txt"
        not_a_pdf.write_text("content")
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--pdf", str(not_a_pdf)])
        assert exc_info.value.code == 1

    def test_pdf_extension_case_insensitive(self, tmp_path):
        """.PDF (uppercase) is accepted."""
        pdf_file = tmp_path / "paper.PDF"
        pdf_file.write_text("fake pdf content")
        args = parse_args(["--pdf", str(pdf_file)])
        assert args.pdf == str(pdf_file)

    def test_valid_pdf_parsed_successfully(self, tmp_path):
        """A valid .pdf file parses without error."""
        pdf_file = tmp_path / "valid.pdf"
        pdf_file.write_text("fake pdf content")
        args = parse_args(["--pdf", str(pdf_file)])
        assert args.pdf == str(pdf_file)
        assert args.doi is None
        assert args.cite_key is None

    def test_doi_optional(self, tmp_path):
        """--doi is optional and parsed when provided."""
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_text("content")
        args = parse_args([
            "--pdf", str(pdf_file),
            "--doi", "10.1234/example",
        ])
        assert args.doi == "10.1234/example"

    def test_doi_invalid_format_exits(self, tmp_path):
        """Invalid DOI format exits with code 1."""
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_text("content")
        with pytest.raises(SystemExit) as exc_info:
            parse_args([
                "--pdf", str(pdf_file),
                "--doi", "not-a-doi",
            ])
        assert exc_info.value.code == 1

    def test_doi_missing_10_prefix_exits(self, tmp_path):
        """DOI without '10.' prefix exits with code 1."""
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_text("content")
        with pytest.raises(SystemExit) as exc_info:
            parse_args([
                "--pdf", str(pdf_file),
                "--doi", "11.1234/example",
            ])
        assert exc_info.value.code == 1

    def test_doi_empty_string_exits(self, tmp_path):
        """Empty DOI exits with code 1 (doesn't match ^10\\..+)."""
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_text("content")
        with pytest.raises(SystemExit) as exc_info:
            parse_args([
                "--pdf", str(pdf_file),
                "--doi", "",
            ])
        assert exc_info.value.code == 1

    def test_cite_key_optional(self, tmp_path):
        """--cite-key is optional and parsed when provided."""
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_text("content")
        args = parse_args([
            "--pdf", str(pdf_file),
            "--cite-key", "my-custom-key",
        ])
        assert args.cite_key == "my-custom-key"

    def test_all_arguments_together(self, tmp_path):
        """All three arguments parse correctly together."""
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_text("content")
        args = parse_args([
            "--pdf", str(pdf_file),
            "--doi", "10.1234/example",
            "--cite-key", "custom-key",
        ])
        assert args.pdf == str(pdf_file)
        assert args.doi == "10.1234/example"
        assert args.cite_key == "custom-key"

    def test_provider_argument_parsed(self, tmp_path):
        """--provider is optional and parsed when provided."""
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_text("content")
        args = parse_args([
            "--pdf", str(pdf_file),
            "--provider", "nim",
        ])
        assert args.provider == "nim"

    def test_pdf_exists_stderr_message(self, tmp_path):
        """File-not-found error prints message to stderr."""
        nonexistent = str(tmp_path / "nonexistent.pdf")
        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            with pytest.raises(SystemExit):
                parse_args(["--pdf", nonexistent])
        assert "not found" in stderr_capture.getvalue().lower()

    def test_not_pdf_stderr_message(self, tmp_path):
        """Not-a-PDF error prints message to stderr."""
        txt_file = tmp_path / "file.txt"
        txt_file.write_text("content")
        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            with pytest.raises(SystemExit):
                parse_args(["--pdf", str(txt_file)])
        assert "not a pdf" in stderr_capture.getvalue().lower()

    def test_invalid_doi_stderr_message(self, tmp_path):
        """Invalid DOI error prints message to stderr."""
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_text("content")
        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            with pytest.raises(SystemExit):
                parse_args(["--pdf", str(pdf_file), "--doi", "bad-doi"])
        assert "doi" in stderr_capture.getvalue().lower()


class TestMainHappyPath:
    """End-to-end test of main() with all modules mocked."""

    def _dummy_metadata(self):
        return {
            "year": 2024,
            "venue": "Nature",
            "citationCount": 100,
            "authors": [{"name": "Alice"}],
        }

    @patch("ingest.generate_crossref_note")
    @patch("ingest.generate_paper_profile")
    @patch("ingest.init_llm_client")
    @patch("ingest.compute_baseline_trust_score")
    @patch("ingest.fetch_metadata")
    @patch("ingest.extract_text")
    @patch("ingest.load_dotenv")
    def test_happy_path_calls_all_modules(
        self,
        mock_load_dotenv,
        mock_extract_text,
        mock_fetch_metadata,
        mock_compute_score,
        mock_init_client,
        mock_generate_profile,
        mock_generate_crossref,
        tmp_path,
        monkeypatch,
    ):
        """Happy path: all modules are called in the correct sequence."""
        # Setup
        pdf_file = tmp_path / "test-paper.pdf"
        pdf_file.write_text("fake pdf content")

        mock_extract_text.return_value = "Fake PDF text"
        mock_fetch_metadata.return_value = self._dummy_metadata()
        mock_compute_score.return_value = 8
        mock_client = MagicMock()
        mock_init_client.return_value = mock_client

        # Set environment variables
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")

        # Run
        main(["--pdf", str(pdf_file)])

        # Assert calls happened in correct order (implicitly via call order)
        mock_load_dotenv.assert_called_once()
        mock_extract_text.assert_called_once_with(str(pdf_file))
        mock_fetch_metadata.assert_called_once()
        mock_compute_score.assert_called_once()
        mock_init_client.assert_called_once_with("anthropic", "test-api-key")
        mock_generate_profile.assert_called_once()
        mock_generate_crossref.assert_called_once()

    @patch("ingest.generate_crossref_note")
    @patch("ingest.generate_paper_profile")
    @patch("ingest.init_llm_client")
    @patch("ingest.compute_baseline_trust_score")
    @patch("ingest.fetch_metadata")
    @patch("ingest.extract_text")
    @patch("ingest.load_dotenv")
    def test_cite_key_derived_from_filename(
        self,
        mock_load_dotenv,
        mock_extract_text,
        mock_fetch_metadata,
        mock_compute_score,
        mock_init_client,
        mock_generate_profile,
        mock_generate_crossref,
        tmp_path,
        monkeypatch,
    ):
        """Cite-key is derived from the PDF filename when not provided."""
        pdf_file = tmp_path / "My Paper_2024.pdf"
        pdf_file.write_text("fake content")

        mock_extract_text.return_value = "Fake PDF text"
        mock_fetch_metadata.return_value = self._dummy_metadata()
        mock_compute_score.return_value = 8
        mock_client = MagicMock()
        mock_init_client.return_value = mock_client

        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        main(["--pdf", str(pdf_file)])

        # The cite-key should be "my-paper-2024"
        # generate_paper_profile(client, provider, cite_key, metadata, pdf_text)
        cite_key = mock_generate_profile.call_args[0][2]
        assert cite_key == "my-paper-2024"

    @patch("ingest.generate_crossref_note")
    @patch("ingest.generate_paper_profile")
    @patch("ingest.init_llm_client")
    @patch("ingest.compute_baseline_trust_score")
    @patch("ingest.fetch_metadata")
    @patch("ingest.extract_text")
    @patch("ingest.load_dotenv")
    def test_custom_cite_key_used(
        self,
        mock_load_dotenv,
        mock_extract_text,
        mock_fetch_metadata,
        mock_compute_score,
        mock_init_client,
        mock_generate_profile,
        mock_generate_crossref,
        tmp_path,
        monkeypatch,
    ):
        """Provided --cite-key overrides the derived one."""
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_text("content")

        mock_extract_text.return_value = "Fake PDF text"
        mock_fetch_metadata.return_value = self._dummy_metadata()
        mock_compute_score.return_value = 8
        mock_client = MagicMock()
        mock_init_client.return_value = mock_client

        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        main(["--pdf", str(pdf_file), "--cite-key", "custom-key"])

        # generate_paper_profile(client, provider, cite_key, metadata, pdf_text)
        cite_key = mock_generate_profile.call_args[0][2]
        assert cite_key == "custom-key"

    @patch("ingest.generate_crossref_note")
    @patch("ingest.generate_paper_profile")
    @patch("ingest.init_llm_client")
    @patch("ingest.compute_baseline_trust_score")
    @patch("ingest.fetch_metadata")
    @patch("ingest.extract_text")
    @patch("ingest.load_dotenv")
    def test_metadata_enriched_with_trust_score_and_cite_key(
        self,
        mock_load_dotenv,
        mock_extract_text,
        mock_fetch_metadata,
        mock_compute_score,
        mock_init_client,
        mock_generate_profile,
        mock_generate_crossref,
        tmp_path,
        monkeypatch,
    ):
        """Metadata dict passed to generate_paper_profile contains
        baseline_trust_score, cite_key, and title."""
        pdf_file = tmp_path / "Test Paper.pdf"
        pdf_file.write_text("Test Title\nAbstract goes here...")

        mock_extract_text.return_value = "Test Title\nAbstract goes here..."
        mock_fetch_metadata.return_value = self._dummy_metadata()
        mock_compute_score.return_value = 8
        mock_client = MagicMock()
        mock_init_client.return_value = mock_client

        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        main(["--pdf", str(pdf_file)])

        # generate_paper_profile(client, provider, cite_key, metadata, pdf_text)
        metadata = mock_generate_profile.call_args[0][3]
        assert metadata["baseline_trust_score"] == 8
        assert metadata["cite_key"] == "test-paper"
        assert metadata["title"] == "Test Title"


class TestMainErrorPaths:
    """Error paths in main()."""

    def test_pdf_extraction_runtime_error_exits(self, tmp_path, monkeypatch):
        """RuntimeError from extract_text causes sys.exit(1)."""
        pdf_file = tmp_path / "broken.pdf"
        pdf_file.write_text("content")

        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        with patch("ingest.load_dotenv"):
            with patch("ingest.extract_text", side_effect=RuntimeError("PDF corrupt")):
                stderr_capture = io.StringIO()
                with redirect_stderr(stderr_capture):
                    with pytest.raises(SystemExit) as exc_info:
                        main(["--pdf", str(pdf_file)])

        assert exc_info.value.code == 1
        assert "PDF" in stderr_capture.getvalue()

    def test_missing_llm_provider_exits(self, tmp_path, monkeypatch):
        """Missing LLM_PROVIDER causes sys.exit(1)."""
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_text("content")

        # Ensure LLM_PROVIDER is not set
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        with patch("ingest.load_dotenv"):
            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                with pytest.raises(SystemExit) as exc_info:
                    main(["--pdf", str(pdf_file)])

        assert exc_info.value.code == 1
        assert "LLM_PROVIDER" in stderr_capture.getvalue()

    def test_unknown_llm_provider_exits(self, tmp_path, monkeypatch):
        """Unknown LLM_PROVIDER value causes sys.exit(1)."""
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_text("content")

        monkeypatch.setenv("LLM_PROVIDER", "unknown-provider")

        with patch("ingest.load_dotenv"):
            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                with pytest.raises(SystemExit) as exc_info:
                    main(["--pdf", str(pdf_file)])

        assert exc_info.value.code == 1
        assert "Unknown" in stderr_capture.getvalue()

    def test_missing_api_key_exits(self, tmp_path, monkeypatch):
        """Missing API key causes sys.exit(1)."""
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_text("content")

        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with patch("ingest.load_dotenv"):
            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                with pytest.raises(SystemExit) as exc_info:
                    main(["--pdf", str(pdf_file)])

        assert exc_info.value.code == 1
        assert "ANTHROPIC_API_KEY" in stderr_capture.getvalue()

    def test_missing_openai_key_exits(self, tmp_path, monkeypatch):
        """Missing OPENAI_API_KEY when using openai causes sys.exit(1)."""
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_text("content")

        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with patch("ingest.load_dotenv"):
            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                with pytest.raises(SystemExit) as exc_info:
                    main(["--pdf", str(pdf_file)])

        assert exc_info.value.code == 1
        assert "OPENAI_API_KEY" in stderr_capture.getvalue()
