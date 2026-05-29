"""
tests/test_llm_client.py — Tests for llm_client.py.

Covers:
  - Property 10: Prompt context contains all required metadata fields
  - Property 11: Pass 2 prompt contains all required context fields
  - Property 12: Output file path is correctly derived from cite-key
  - Property 13: File write is a UTF-8 round-trip
  - Property 14: Overwrite warning always contains the file path
  - Property 15: Missing API key error names the correct environment variable
  - Mock Anthropic and OpenAI SDK clients
  - Empty/whitespace response handling
  - OSError in _write_output
  - Directory creation before file write
  - PROMPT_A_TEMPLATE references the papers entity schema
  - PROMPT_B_TEMPLATE references the edges.yaml cross-reference vocabulary
"""

import io
import sys
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from llm_client import (
    PROMPT_A_TEMPLATE,
    PROMPT_B_TEMPLATE,
    _build_prompt_a,
    _build_prompt_b,
    _call_llm,
    _write_output,
    init_llm_client,
    generate_paper_profile,
    generate_crossref_note,
)


# ===========================================================================
# Property-Based Tests
# ===========================================================================


# ---------------------------------------------------------------------------
# Property 10: Prompt context contains all required metadata fields
# Feature: literature-review-pipeline, Property 10
# Validates: Requirements 5.2
# ---------------------------------------------------------------------------

# Feature: literature-review-pipeline, Property 10
@given(
    year=st.one_of(st.none(), st.integers(min_value=1900, max_value=2100)),
    venue=st.one_of(
        st.none(),
        st.text(
            max_size=50,
            alphabet=st.characters(
                min_codepoint=32, max_codepoint=126,
                blacklist_characters='\\"',
            ),
        ),
    ),
    citation_count=st.one_of(st.none(), st.integers(min_value=0, max_value=10000)),
    authors=st.lists(
        st.fixed_dictionaries({
            "name": st.text(
                min_size=1,
                max_size=30,
                alphabet=st.characters(
                    min_codepoint=32, max_codepoint=126,
                    blacklist_characters='\\"',
                ),
            ),
        }),
        max_size=5,
    ),
    trust_score=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=100)
def test_property10_prompt_contains_all_metadata(
    year, venue, citation_count, authors, trust_score
):
    """
    **Validates: Requirements 5.2**

    For any metadata dict with the five required fields, the constructed
    Pass 1 prompt string MUST contain each value as a substring.
    """
    metadata = {
        "year": year,
        "venue": venue,
        "citationCount": citation_count,
        "authors": authors,
        "baseline_trust_score": trust_score,
        "cite_key": "test-key",
        "title": "Test Title",
    }

    prompt = _build_prompt_a(metadata, "sample pdf text")

    # Year
    if year is not None:
        assert str(year) in prompt, f"Year {year!r} not found in prompt"
    else:
        assert "null" in prompt, "null not found for year=None"

    # Venue
    if venue is not None:
        assert venue in prompt, f"Venue {venue!r} not found in prompt"
    else:
        assert "null" in prompt, "null not found for venue=None"

    # Citation count
    if citation_count is not None:
        assert str(citation_count) in prompt, (
            f"citationCount {citation_count!r} not found in prompt"
        )
    else:
        assert "null" in prompt, "null not found for citationCount=None"

    # Authors — each author name must appear
    for author in authors:
        assert author["name"] in prompt, (
            f"Author name {author['name']!r} not found in prompt"
        )

    # Baseline trust score
    assert str(trust_score) in prompt, (
        f"Trust score {trust_score} not found in prompt"
    )


# ---------------------------------------------------------------------------
# Property 11: Pass 2 prompt contains all required context fields
# Feature: literature-review-pipeline, Property 11
# Validates: Requirements 6.2
# ---------------------------------------------------------------------------

# Feature: literature-review-pipeline, Property 11
@given(
    cite_key=st.text(min_size=1, max_size=50),
    paper_title=st.text(min_size=1, max_size=100),
    pdf_text=st.text(min_size=1, max_size=200),
)
@settings(max_examples=100)
def test_property11_pass2_prompt_contains_context(cite_key, paper_title, pdf_text):
    """
    **Validates: Requirements 6.2**

    For any cite_key, paper_title, and pdf_text, the constructed Pass 2
    prompt string MUST contain all three as substrings.
    """
    prompt = _build_prompt_b(cite_key, paper_title, pdf_text)

    assert cite_key in prompt, f"cite_key {cite_key!r} not found in prompt"
    assert paper_title in prompt, f"paper_title {paper_title!r} not found in prompt"
    assert pdf_text in prompt, f"pdf_text not found in prompt"


# ---------------------------------------------------------------------------
# Property 12: Output file path is correctly derived from cite-key
# Feature: literature-review-pipeline, Property 12
# Validates: Requirements 5.4, 6.4
# ---------------------------------------------------------------------------

# Feature: literature-review-pipeline, Property 12
@given(st.text(min_size=1, max_size=50))
@settings(max_examples=100)
def test_property12_output_path_from_cite_key(cite_key):
    """
    **Validates: Requirements 5.4, 6.4**

    For any cite-key, Pass 1 path MUST equal ``./wiki/papers/{cite_key}.md``
    and Pass 2 path MUST equal ``./wiki/implementation-decisions/{cite_key}-crossref.md``.
    """
    dummy_metadata = {
        "year": 2024,
        "venue": "Nature",
        "citationCount": 100,
        "authors": [{"name": "Alice"}],
        "baseline_trust_score": 8,
        "cite_key": cite_key,
        "title": "Test Title",
    }

    # --- Pass 1 ---
    with patch("llm_client._call_llm", return_value="Generated content"):
        with patch("llm_client._write_output") as mock_write:
            generate_paper_profile(
                MagicMock(), "anthropic", cite_key, dummy_metadata, "pdf text"
            )
            mock_write.assert_called_once()
            path = mock_write.call_args[0][0]
            assert path == f"./wiki/papers/{cite_key}.md", (
                f"Pass 1 path mismatch: expected ./wiki/papers/{cite_key}.md, got {path}"
            )

    # --- Pass 2 ---
    with patch("llm_client._call_llm", return_value="Generated content"):
        with patch("llm_client._write_output") as mock_write:
            generate_crossref_note(
                MagicMock(), "anthropic", cite_key, "pdf text", "Test Title"
            )
            mock_write.assert_called_once()
            path = mock_write.call_args[0][0]
            assert path == f"./wiki/implementation-decisions/{cite_key}-crossref.md", (
                f"Pass 2 path mismatch: expected "
                f"./wiki/implementation-decisions/{cite_key}-crossref.md, got {path}"
            )


# ---------------------------------------------------------------------------
# Property 13: File write is a UTF-8 round-trip
# Feature: literature-review-pipeline, Property 13
# Validates: Requirements 8.1
# ---------------------------------------------------------------------------

import tempfile


# Feature: literature-review-pipeline, Property 13
@given(st.text())
@settings(max_examples=100)
def test_property13_utf8_roundtrip(text):
    """
    **Validates: Requirements 8.1**

    For any Unicode string, writing it via _write_output and reading it back
    with UTF-8 MUST produce an identical string.
    """
    tmp_dir = Path(tempfile.mkdtemp())
    path = str(tmp_dir / "test_output.md")
    try:
        _write_output(path, text, "test-cite-key")
        # Use read_bytes + decode to avoid Python's universal newline
        # translation (which would turn \\r into \\n on read-back).
        written = Path(path).read_bytes().decode("utf-8")
        assert written == text, (
            f"UTF-8 round-trip failed: written text differs from original"
        )
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Property 14: Overwrite warning always contains the file path
# Feature: literature-review-pipeline, Property 14
# Validates: Requirements 8.2
# ---------------------------------------------------------------------------

# Feature: literature-review-pipeline, Property 14
@given(
    st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(
            min_codepoint=32,
            max_codepoint=126,
            blacklist_characters="/\\",
        ),
    ).filter(lambda s: s not in (".", "..")),
)
@settings(max_examples=100)
def test_property14_overwrite_warning_contains_file_path(path_stem):
    """
    **Validates: Requirements 8.2**

    When _write_output is called and a file already exists at that path,
    the warning printed to stderr MUST contain the file path as a substring.
    """
    tmp_dir = Path(tempfile.mkdtemp())
    path = str(tmp_dir / path_stem)
    try:
        # Pre-create the file.
        Path(path).write_text("existing content", encoding="utf-8")

        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            _write_output(path, "new content", "key")

        stderr_output = stderr_capture.getvalue()
        assert path in stderr_output, (
            f"File path {path!r} not found in overwrite warning: {stderr_output!r}"
        )
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Property 15: Missing API key error names the correct environment variable
# Feature: literature-review-pipeline, Property 15
# Validates: Requirements 7.6
# ---------------------------------------------------------------------------

# Feature: literature-review-pipeline, Property 15
@given(st.sampled_from(["anthropic", "openai"]))
@settings(max_examples=10)
def test_property15_missing_api_key_names_env_var(provider):
    """
    **Validates: Requirements 7.6**

    For each provider, when the API key is empty, the error message printed
    to stderr MUST contain ANTHROPIC_API_KEY or OPENAI_API_KEY respectively.
    """
    stderr_capture = io.StringIO()
    with redirect_stderr(stderr_capture):
        with pytest.raises(SystemExit) as exc_info:
            init_llm_client(provider, "")

    assert exc_info.value.code == 1, (
        f"Expected exit code 1, got {exc_info.value.code}"
    )

    stderr_output = stderr_capture.getvalue()

    if provider == "anthropic":
        assert "ANTHROPIC_API_KEY" in stderr_output, (
            f"'ANTHROPIC_API_KEY' not found in stderr: {stderr_output!r}"
        )
    else:
        assert "OPENAI_API_KEY" in stderr_output, (
            f"'OPENAI_API_KEY' not found in stderr: {stderr_output!r}"
        )


# ===========================================================================
# Unit Tests — Task 6.13
# Validates: Requirements 5.6, 5.7, 5.8, 6.6, 6.7, 8.3
# ===========================================================================


class TestPromptTemplatesSchemaReferences:
    """PROMPT_A_TEMPLATE and PROMPT_B_TEMPLATE reference the correct schemas."""

    def test_prompt_a_references_papers_schema(self):
        """Requirement 5.6: PROMPT_A_TEMPLATE references the papers entity schema."""
        assert "`papers` entity schema" in PROMPT_A_TEMPLATE, (
            f"PROMPT_A_TEMPLATE should reference the papers entity schema, "
            f"got: {PROMPT_A_TEMPLATE!r}"
        )

    def test_prompt_b_references_edges_schema(self):
        """Requirement 6.6: PROMPT_B_TEMPLATE references the edges.yaml schema."""
        assert "edges.yaml" in PROMPT_B_TEMPLATE.lower(), (
            f"PROMPT_B_TEMPLATE should reference edges.yaml, got: {PROMPT_B_TEMPLATE!r}"
        )


class TestInitLlmClientUnknownProvider:
    """Unknown provider name causes sys.exit(1)."""

    def test_unknown_provider_exits(self):
        """A completely unknown provider exits with code 1."""
        with pytest.raises(SystemExit) as exc_info:
            init_llm_client("some-random-provider", "key123")
        assert exc_info.value.code == 1

    def test_unknown_provider_prints_to_stderr(self):
        """Unknown provider prints an error to stderr."""
        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            with pytest.raises(SystemExit):
                init_llm_client("not-a-real-provider", "key123")
        assert "Unknown LLM provider" in stderr_capture.getvalue()

    def test_anthropic_case_insensitive(self):
        """Provider name is matched case-insensitively."""
        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            with pytest.raises(SystemExit):
                init_llm_client("AnThRoPiC", "")
        assert "ANTHROPIC_API_KEY" in stderr_capture.getvalue()

    def test_openai_case_insensitive(self):
        """Provider name is matched case-insensitively (OpenAI)."""
        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            with pytest.raises(SystemExit):
                init_llm_client("OpenAI", "")
        assert "OPENAI_API_KEY" in stderr_capture.getvalue()


class TestCallLlmAnthropic:
    """Mock Anthropic client for _call_llm."""

    def test_anthropic_calls_messages_create(self):
        """Anthropic provider dispatches to client.messages.create."""
        mock_client = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Response from Claude"
        mock_client.messages.create.return_value = MagicMock(
            content=[mock_content]
        )

        result = _call_llm(mock_client, "anthropic", "system prompt", "user prompt")

        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "system prompt"
        assert call_kwargs["messages"] == [{"role": "user", "content": "user prompt"}]
        assert "model" in call_kwargs
        assert call_kwargs["max_tokens"] == 4096
        assert result == "Response from Claude"

    def test_anthropic_case_insensitive(self):
        """Provider 'AnThRoPiC' is handled the same as 'anthropic'."""
        mock_client = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "OK"
        mock_client.messages.create.return_value = MagicMock(
            content=[mock_content]
        )

        result = _call_llm(mock_client, "AnThRoPiC", "sys", "user")
        mock_client.messages.create.assert_called_once()
        assert result == "OK"


class TestCallLlmOpenai:
    """Mock OpenAI client for _call_llm."""

    def test_openai_calls_chat_completions_create(self):
        """OpenAI provider dispatches to client.chat.completions.create."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Response from GPT"
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )

        result = _call_llm(mock_client, "openai", "system prompt", "user prompt")

        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["messages"] == [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "user prompt"},
        ]
        assert result == "Response from GPT"

    def test_openai_case_insensitive(self):
        """Provider 'OpenAI' is handled the same as 'openai'."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "OK"
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )

        result = _call_llm(mock_client, "OpenAI", "sys", "user")
        mock_client.chat.completions.create.assert_called_once()
        assert result == "OK"


class TestGeneratePaperProfileErrorHandling:
    """Error and empty-response handling for generate_paper_profile."""

    def dummy_metadata(self):
        return {
            "year": 2024,
            "venue": "Nature",
            "citationCount": 100,
            "authors": [{"name": "Alice"}],
            "baseline_trust_score": 8,
            "cite_key": "test-key",
            "title": "Test Title",
        }

    def test_llm_error_prints_to_stderr_and_skips_write(self):
        """API error prints warning to stderr and does NOT call _write_output."""
        with patch(
            "llm_client._call_llm",
            side_effect=RuntimeError("API down"),
        ), patch("llm_client._write_output") as mock_write:
            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                generate_paper_profile(
                    MagicMock(), "anthropic", "test-key",
                    self.dummy_metadata(), "pdf text"
                )

        mock_write.assert_not_called()
        assert "Error generating paper profile" in stderr_capture.getvalue()
        assert "test-key" in stderr_capture.getvalue()

    def test_empty_response_prints_warning_and_skips_write(self):
        """Empty LLM response prints warning to stderr and does NOT call _write_output."""
        with patch("llm_client._call_llm", return_value=""), \
             patch("llm_client._write_output") as mock_write:
            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                generate_paper_profile(
                    MagicMock(), "anthropic", "test-key",
                    self.dummy_metadata(), "pdf text"
                )

        mock_write.assert_not_called()
        assert "Empty response" in stderr_capture.getvalue()

    def test_whitespace_only_response_treated_as_empty(self):
        """A whitespace-only response is treated the same as empty."""
        with patch("llm_client._call_llm", return_value="   \n\t\n  "), \
             patch("llm_client._write_output") as mock_write:
            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                generate_paper_profile(
                    MagicMock(), "anthropic", "test-key",
                    self.dummy_metadata(), "pdf text"
                )

        mock_write.assert_not_called()
        assert "Empty response" in stderr_capture.getvalue()

    def test_successful_call_writes_output(self):
        """A successful, non-empty response calls _write_output."""
        with patch("llm_client._call_llm", return_value="Profile content"), \
             patch("llm_client._write_output") as mock_write:
            generate_paper_profile(
                MagicMock(), "anthropic", "test-key",
                self.dummy_metadata(), "pdf text"
            )

        mock_write.assert_called_once()
        assert mock_write.call_args[0][0] == "./wiki/papers/test-key.md"
        assert mock_write.call_args[0][1] == "Profile content"


class TestGenerateCrossrefNoteErrorHandling:
    """Error and empty-response handling for generate_crossref_note."""

    def test_llm_error_prints_to_stderr_and_skips_write(self):
        """API error prints warning to stderr and does NOT call _write_output."""
        with patch(
            "llm_client._call_llm",
            side_effect=RuntimeError("API down"),
        ), patch("llm_client._write_output") as mock_write:
            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                generate_crossref_note(
                    MagicMock(), "anthropic", "test-key", "pdf text", "Test Title"
                )

        mock_write.assert_not_called()
        assert "Error generating crossref note" in stderr_capture.getvalue()

    def test_empty_response_prints_warning_and_skips_write(self):
        """Empty LLM response prints warning and does NOT call _write_output."""
        with patch("llm_client._call_llm", return_value=""), \
             patch("llm_client._write_output") as mock_write:
            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                generate_crossref_note(
                    MagicMock(), "anthropic", "test-key", "pdf text", "Test Title"
                )

        mock_write.assert_not_called()
        assert "Empty response" in stderr_capture.getvalue()

    def test_whitespace_only_response_treated_as_empty(self):
        """Whitespace-only response treated as empty."""
        with patch("llm_client._call_llm", return_value="   \n  "), \
             patch("llm_client._write_output") as mock_write:
            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                generate_crossref_note(
                    MagicMock(), "anthropic", "test-key", "pdf text", "Test Title"
                )

        mock_write.assert_not_called()
        assert "Empty response" in stderr_capture.getvalue()

    def test_successful_call_writes_output(self):
        """Successful response calls _write_output with correct path."""
        with patch("llm_client._call_llm", return_value="Crossref content"), \
             patch("llm_client._write_output") as mock_write:
            generate_crossref_note(
                MagicMock(), "anthropic", "test-key", "pdf text", "Test Title"
            )

        mock_write.assert_called_once()
        assert mock_write.call_args[0][0] == (
            "./wiki/implementation-decisions/test-key-crossref.md"
        )
        assert mock_write.call_args[0][1] == "Crossref content"


class TestWriteOutput:
    """Unit tests for _write_output: dir creation, OSError, overwrite."""

    def test_creates_parent_directories(self, tmp_path):
        """Requirement 8.3: _write_output creates parent directories if needed."""
        nested_path = str(tmp_path / "deeply" / "nested" / "output.md")

        _write_output(nested_path, "content", "cite-key")

        assert Path(nested_path).exists()
        assert Path(nested_path).read_text(encoding="utf-8") == "content"

    def test_no_error_when_directory_already_exists(self, tmp_path):
        """Writing to an existing directory must not raise."""
        path = str(tmp_path / "existing_dir" / "output.md")
        Path(tmp_path / "existing_dir").mkdir()

        # Should not raise
        _write_output(path, "content", "key")
        assert Path(path).read_text(encoding="utf-8") == "content"

    def test_oserror_skips_write_and_prints_to_stderr(self, tmp_path):
        """OSError during write prints to stderr and does not crash."""
        path = str(tmp_path / "output.md")

        with patch.object(Path, "write_text", side_effect=OSError("Disk full")):
            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                _write_output(path, "content", "key")

        stderr_output = stderr_capture.getvalue()
        assert "Error writing" in stderr_output
        assert path in stderr_output
        assert "Disk full" in stderr_output

    def test_overwrite_warning_printed_to_stderr(self, tmp_path):
        """Overwriting an existing file prints a warning containing the path."""
        path = str(tmp_path / "existing.md")
        Path(path).write_text("old content", encoding="utf-8")

        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            _write_output(path, "new content", "key")

        stderr_output = stderr_capture.getvalue()
        assert "Warning: Overwriting existing file" in stderr_output
        assert path in stderr_output

        # File should still be overwritten
        assert Path(path).read_text(encoding="utf-8") == "new content"

    def test_overwrite_does_not_warn_when_file_absent(self, tmp_path):
        """No warning is printed when the file does not yet exist."""
        path = str(tmp_path / "nonexistent.md")

        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            _write_output(path, "content", "key")

        assert "Overwriting" not in stderr_capture.getvalue()
