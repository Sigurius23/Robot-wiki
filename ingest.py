"""
ingest.py — CLI entry point and pipeline orchestrator.

Usage:
    python ingest.py --pdf ./raw_papers/smith2024.pdf [--doi 10.1234/abc] [--cite-key smith2024]

Produces:
    ./wiki/papers/<cite-key>.md
    ./wiki/implementation-decisions/<cite-key>-crossref.md

This module is a thin orchestrator. All data transformation, validation,
scoring, prompt construction, and external API/LLM call logic lives in the
dedicated pipeline modules (pdf_extractor, metadata_fetcher, trust_scorer,
llm_client).
"""

import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

from pdf_extractor import extract_text
from metadata_fetcher import fetch_metadata, _extract_title_from_text
from trust_scorer import compute_baseline_trust_score
from llm_client import init_llm_client, generate_paper_profile, generate_crossref_note


# ---------------------------------------------------------------------------
# Cite-key derivation
# ---------------------------------------------------------------------------

def derive_cite_key(pdf_path: str) -> str:
    """
    Derive cite-key from PDF filename stem.

    Algorithm:
      1. Take ``Path(pdf_path).stem`` (filename without extension).
      2. Lowercase the result.
      3. Replace all underscores (``_``) and spaces (`` ``) with hyphens (``-``).
      4. Strip leading / trailing hyphens.

    Example:
        ``"Smith_2024 paper.pdf"`` → ``"smith-2024-paper"``

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Lowercase, hyphen-separated cite-key string.
    """
    stem = Path(pdf_path).stem
    key = stem.lower()
    key = key.replace("_", "-").replace(" ", "-")
    return key.strip("-")


# ---------------------------------------------------------------------------
# DOI validation
# ---------------------------------------------------------------------------

_DOI_PATTERN = re.compile(r"^10\..+")

def validate_doi(doi: str) -> bool:
    """
    Return ``True`` if *doi* starts with ``10.`` followed by one or more
    characters, ``False`` otherwise.

    Args:
        doi: The DOI string to validate.

    Returns:
        ``True`` if the DOI matches the expected format.
    """
    if not doi:
        return False
    return bool(_DOI_PATTERN.match(doi))


# ---------------------------------------------------------------------------
# Argument parsing & CLI validation
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Parse and validate CLI arguments.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Parsed namespace with ``pdf``, ``doi``, and ``cite_key`` attributes.

    Raises:
        SystemExit: on any validation failure (code 1).
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Ingest an academic PDF into the Obsidian wiki.",
    )
    parser.add_argument(
        "--pdf",
        required=True,
        help="Path to the PDF file to ingest.",
    )
    parser.add_argument(
        "--doi",
        default=None,
        help="DOI of the paper (optional).",
    )
    parser.add_argument(
        "--cite-key",
        default=None,
        help="Cite-key for the output notes (optional; derived from filename if omitted).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model name override (optional). "
            "Defaults: anthropic=claude-sonnet-4-20250514, "
            "openai=gpt-4o, nim=deepseek-ai/deepseek-v4-pro."
        ),
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="LLM provider override (optional). Must be 'anthropic', 'openai', or 'nim'.",
    )
    parser.add_argument(
        "--subfolder",
        default=None,
        help="Subfolder relative to the wiki root under which notes should be written.",
    )

    args = parser.parse_args(argv)

    # --pdf: file must exist
    if not os.path.isfile(args.pdf):
        print(f"Error: PDF file not found: {args.pdf}", file=sys.stderr)
        sys.exit(1)

    # --pdf: must have .pdf extension (case-insensitive)
    if not args.pdf.lower().endswith(".pdf"):
        print(f"Error: Not a PDF file: {args.pdf}", file=sys.stderr)
        sys.exit(1)

    # --doi: validate format if provided
    if args.doi is not None and not validate_doi(args.doi):
        print(
            f"Error: DOI format is invalid: '{args.doi}'. "
            f"Must start with '10.'.",
            file=sys.stderr,
        )
        sys.exit(1)

    return args


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    """
    Orchestrate the full ingestion pipeline.

    1. Parse CLI arguments.
    2. Load ``.env`` and validate LLM provider / API key.
    3. Extract text from PDF.
    4. Fetch metadata from Semantic Scholar (or manual fallback).
    5. Compute baseline trust score.
    6. Enrich metadata with cite-key and title.
    7. Initialise LLM client.
    8. Generate paper profile note (Pass 1).
    9. Generate cross-reference note (Pass 2).

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).
    """
    # --- Step 1: Parse arguments -------------------------------------------------
    args = parse_args(argv)
    pdf_path: str = args.pdf
    doi: str | None = args.doi
    cite_key: str = args.cite_key if args.cite_key else derive_cite_key(pdf_path)
    # --model flag takes precedence; fall back to LLM_MODEL env var
    model: str | None = args.model or os.getenv("LLM_MODEL") or None

    # --- Step 2: Load environment & validate -------------------------------------
    load_dotenv()

    # --provider flag takes precedence; fall back to LLM_PROVIDER env var
    provider = args.provider or os.getenv("LLM_PROVIDER")
    if not provider:
        print(
            "Error: LLM_PROVIDER environment variable is not set. "
            "Must be 'anthropic', 'openai', or 'nim'.",
            file=sys.stderr,
        )
        sys.exit(1)

    provider_lower = provider.lower()
    if provider_lower == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        env_var_name = "ANTHROPIC_API_KEY"
    elif provider_lower == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        env_var_name = "OPENAI_API_KEY"
    elif provider_lower == "nim":
        api_key = os.getenv("NIM_API_KEY")
        env_var_name = "NIM_API_KEY"
    else:
        print(
            f"Error: Unknown LLM_PROVIDER '{provider}'. "
            f"Must be 'anthropic', 'openai', or 'nim'.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not api_key:
        print(
            f"Error: {env_var_name} environment variable is not set.",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Step 3: Extract text from PDF -------------------------------------------
    print(f"→  Extracting text from PDF ...", file=sys.stderr)
    try:
        pdf_text = extract_text(pdf_path)
    except RuntimeError as exc:
        print(f"Error: Failed to extract text from PDF: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"✓  Extracted {len(pdf_text):,} characters", file=sys.stderr)

    # --- Step 4: Fetch metadata --------------------------------------------------
    print(f"→  Fetching metadata from Semantic Scholar ...", file=sys.stderr)
    metadata = fetch_metadata(doi, pdf_text)
    year = metadata.get("year")
    venue = metadata.get("venue") or "unknown"
    citations = metadata.get("citationCount")
    citations_str = str(citations) if citations is not None else "unknown"
    authors_count = len(metadata.get("authors") or [])
    print(f"✓  Metadata: year={year}, venue={venue!r}, citations={citations_str}, authors={authors_count}", file=sys.stderr)

    # --- Step 5: Compute trust score ---------------------------------------------
    venue = metadata.get("venue")
    year = metadata.get("year")
    citation_count = metadata.get("citationCount")
    baseline_trust_score = compute_baseline_trust_score(venue, year, citation_count)
    print(f"✓  Baseline trust score: {baseline_trust_score}/10", file=sys.stderr)

    # --- Step 6: Enrich metadata -------------------------------------------------
    metadata["baseline_trust_score"] = baseline_trust_score
    metadata["cite_key"] = cite_key

    # Title: prefer API response, fall back to PDF extraction
    if not metadata.get("title"):
        metadata["title"] = _extract_title_from_text(pdf_text)

    # --- Step 7: Initialise LLM client -------------------------------------------
    client = init_llm_client(provider, api_key)

    # --- Step 8: Generate paper profile (Pass 1) ---------------------------------
    generate_paper_profile(client, provider, cite_key, metadata, pdf_text, model, subfolder=args.subfolder)

    # --- Step 9: Generate crossref note (Pass 2) ---------------------------------
    paper_title = metadata.get("title") or cite_key
    generate_crossref_note(client, provider, cite_key, pdf_text, paper_title, model, subfolder=args.subfolder)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
