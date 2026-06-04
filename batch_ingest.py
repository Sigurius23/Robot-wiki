#!/usr/bin/env python
"""
batch_ingest.py — Batch ingest academic papers from raw_papers/ subfolders.

Usage:
    python batch_ingest.py [--dir ./raw_papers] [--dry-run] [--provider nim] [--limit 5]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Reuse the cite-key derivation logic from ingest.py
sys.path.append(str(Path(__file__).parent))
from ingest import derive_cite_key


def map_to_topic(pdf_path: Path) -> str:
    """
    Map a PDF path to a topic based on its parent folder structure within raw_papers.
    """
    try:
        raw_papers_dir = Path("./raw_papers").resolve()
        resolved_pdf = pdf_path.resolve()
        rel = resolved_pdf.relative_to(raw_papers_dir)
        if len(rel.parts) > 1:
            return rel.parts[0]
    except (ValueError, RuntimeError):
        pass
    return "general"


def main():
    parser = argparse.ArgumentParser(
        description="Recursively batch ingest PDFs and organize them into topic folders.",
    )
    parser.add_argument(
        "--dir",
        default="./raw_papers",
        help="Directory to scan recursively for PDFs (default: ./raw_papers).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List all files and their mapped topics without running ingestion.",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="LLM provider override to pass to ingest.py (anthropic, openai, nim).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="LLM model override to pass to ingest.py.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-process files even if they already exist in the wiki.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of new/pending papers to process in this run.",
    )

    args = parser.parse_args()

    scan_dir = Path(args.dir)
    if not scan_dir.is_dir():
        print(f"Error: Directory not found: {args.dir}", file=sys.stderr)
        sys.exit(1)

    print(f"→  Scanning {scan_dir} recursively for PDFs...", file=sys.stderr)
    pdf_files = sorted(
        [
            p
            for p in scan_dir.rglob("*")
            if p.is_file() and p.suffix.lower() == ".pdf"
        ]
    )

    if not pdf_files:
        print("No PDF files found.", file=sys.stderr)
        return

    print(f"✓  Found {len(pdf_files)} PDF(s)\n", file=sys.stderr)

    papers_to_process = []
    already_processed_count = 0

    print(
        f"{'Topic/Subfolder':<22} | {'Cite-Key':<40} | {'Status':<10} | File Path",
        file=sys.stderr,
    )
    print("-" * 120, file=sys.stderr)

    for pdf_path in pdf_files:
        cite_key = derive_cite_key(str(pdf_path))
        topic = map_to_topic(pdf_path)

        # Check if output files already exist in wiki
        profile_path = Path(f"./wiki/papers/{topic}/{cite_key}.md")
        crossref_path = Path(
            f"./wiki/implementation-decisions/{topic}/{cite_key}-crossref.md"
        )
        exists = profile_path.exists() and crossref_path.exists()

        if exists:
            status = "Completed"
            already_processed_count += 1
        else:
            status = "Pending"
            papers_to_process.append((pdf_path, cite_key, topic))

        rel_path = pdf_path.relative_to(scan_dir)
        print(
            f"{topic:<22} | {cite_key:<40} | {status:<10} | {rel_path}",
            file=sys.stderr,
        )

    print("-" * 120, file=sys.stderr)
    print(
        f"Total found: {len(pdf_files)} | Completed (already in wiki): {already_processed_count} | Pending: {len(papers_to_process)}",
        file=sys.stderr,
    )

    if args.dry_run:
        print("\nDry-run complete. No files were processed.", file=sys.stderr)
        return

    # Filter by limit if specified
    if args.force:
        # If forcing, process everything found
        papers_to_process = [
            (p, derive_cite_key(str(p)), map_to_topic(p)) for p in pdf_files
        ]

    if not papers_to_process:
        print(
            "\nAll papers are already completed. Nothing to ingest (use --force to re-process).",
            file=sys.stderr,
        )
        return

    if args.limit is not None:
        papers_to_process = papers_to_process[: args.limit]
        print(
            f"Applying limit: will process first {len(papers_to_process)} pending paper(s).",
            file=sys.stderr,
        )

    print(
        f"\nStarting batch ingestion of {len(papers_to_process)} paper(s)...\n",
        file=sys.stderr,
    )

    success_count = 0
    failure_count = 0

    for i, (pdf_path, cite_key, topic) in enumerate(papers_to_process, 1):
        print(
            f"[{i}/{len(papers_to_process)}] Processing '{cite_key}' (topic: {topic})...",
            file=sys.stderr,
        )

        cmd = [
            sys.executable,
            "ingest.py",
            "--pdf",
            str(pdf_path),
            "--subfolder",
            topic,
        ]
        if args.provider:
            cmd.extend(["--provider", args.provider])
        if args.model:
            cmd.extend(["--model", args.model])

        # Run ingest.py as a subprocess to isolate errors and preserve console outputs/spinners
        res = subprocess.run(cmd, check=False)

        if res.returncode == 0:
            print(f"✓  Successfully processed '{cite_key}'\n", file=sys.stderr)
            success_count += 1
        else:
            print(
                f"✗  Failed to process '{cite_key}' (exit code {res.returncode})\n",
                file=sys.stderr,
            )
            failure_count += 1

    print("=" * 60, file=sys.stderr)
    print("Batch Ingestion Summary:", file=sys.stderr)
    print(f"  Successfully processed: {success_count}", file=sys.stderr)
    print(f"  Failed:                 {failure_count}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    if failure_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
