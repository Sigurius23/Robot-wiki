#!/usr/bin/env python
"""
process_codebuff_tasks.py — Queue manager for Codebuff task files.

Lists, inspects, and manages the task files in ./codebuff_tasks/ that were
created by the ingest pipeline with --provider codebuff.

Usage:
    python process_codebuff_tasks.py               # list all queued tasks (default)
    python process_codebuff_tasks.py --list         # same as default
    python process_codebuff_tasks.py --clean        # remove task files whose outputs exist
    python process_codebuff_tasks.py --reset        # delete output files so Codebuff reprocesses

Task files are created by running the ingest pipeline with --provider codebuff:
    python ingest.py --pdf ./raw_papers/paper.pdf --provider codebuff
    python batch_ingest.py --provider codebuff

Once task files exist, ask Codebuff to process them. This script helps you
track what's pending, what's done, and clean up afterwards.
"""

import argparse
import json
import sys
from pathlib import Path

_TASKS_DIR = Path("./codebuff_tasks")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_task_files() -> list[Path]:
    """Return all .json task files in the tasks directory, sorted by name."""
    if not _TASKS_DIR.is_dir():
        return []
    return sorted(
        p for p in _TASKS_DIR.iterdir()
        if p.is_file() and p.suffix == ".json" and p.name != "README.md"
    )


def _load_task(task_path: Path) -> dict:
    """Load and return a task JSON file as a dict. Returns empty dict on failure."""
    try:
        return json.loads(task_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  Warning: Failed to read {task_path.name}: {exc}", file=sys.stderr)
        return {}


def _output_exists(output_path: str) -> bool:
    """Check whether the output file for a task already exists."""
    return Path(output_path).is_file()


def _group_by_cite_key(task_files: list[Path]) -> dict[str, list[Path]]:
    """Group task file paths by their cite_key (extracted from filename)."""
    groups: dict[str, list[Path]] = {}
    for task_path in task_files:
        # Filename format: {cite_key}--{task_type}.json
        stem = task_path.stem  # e.g., "2502.17720v4--paper_profile"
        if "--" in stem:
            cite_key = stem.split("--")[0]
        else:
            cite_key = stem
        groups.setdefault(cite_key, []).append(task_path)
    return groups


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list() -> None:
    """Print a summary table of all queued tasks and their output status."""
    task_files = _find_task_files()

    if not task_files:
        print("No task files found in ./codebuff_tasks/.", file=sys.stderr)
        print(
            "\nCreate task files by running the pipeline with --provider codebuff:",
            file=sys.stderr,
        )
        print("    python ingest.py --pdf ./raw_papers/paper.pdf --provider codebuff", file=sys.stderr)
        print("    python batch_ingest.py --provider codebuff", file=sys.stderr)
        return

    groups = _group_by_cite_key(task_files)

    print(f"✓  Found {len(task_files)} task file(s) for {len(groups)} paper(s) in ./codebuff_tasks/\n", file=sys.stderr)

    # Dynamically compute column width to avoid overflow for long cite-keys
    max_cite_key_len = max(len(k) for k in groups.keys()) if groups else 30
    cite_key_width = max(max_cite_key_len + 2, 30)

    # Header — use dynamic width for cite-key column
    header = (
        f"{'Cite-Key':<{cite_key_width}} | {'Pass 1':<8} | {'Pass 2':<8} | {'Outputs':<10} | Status"
    )
    print(header, file=sys.stderr)
    print("-" * len(header), file=sys.stderr)

    complete = 0
    pending = 0
    partial = 0

    for cite_key in sorted(groups.keys()):
        paper_tasks = groups[cite_key]

        has_profile = any("paper_profile" in p.name for p in paper_tasks)
        has_crossref = any("crossref_note" in p.name for p in paper_tasks)

        # Determine output paths from task files
        p1_output_exists = False
        p2_output_exists = False

        for task_path in paper_tasks:
            task = _load_task(task_path)
            if not task:
                continue
            output_path = task.get("output_path", "")
            if "paper_profile" in task_path.name:
                p1_output_exists = _output_exists(output_path)
            elif "crossref_note" in task_path.name:
                p2_output_exists = _output_exists(output_path)

        # Status
        both_done = p1_output_exists and p2_output_exists
        both_missing = not p1_output_exists and not p2_output_exists

        if both_done:
            status = "✓ Complete"
            complete += 1
        elif both_missing:
            status = "○ Pending"
            pending += 1
        else:
            status = "◐ Partial"
            partial += 1

        p1_mark = "✓" if p1_output_exists else "—"
        p2_mark = "✓" if p2_output_exists else "—"
        outputs_str = "Both" if both_done else ("None" if both_missing else "Partial")

        print(
            f"{cite_key:<{cite_key_width}} |  {p1_mark:<6} |  {p2_mark:<6} | {outputs_str:<10} | {status}",
            file=sys.stderr,
        )

    print("-" * len(header), file=sys.stderr)
    print(
        f"Complete: {complete}  |  Pending: {pending}  |  Partial: {partial}  |  Total: {len(groups)} paper(s)",
        file=sys.stderr,
    )

    if pending > 0:
        print(
            f"\n→  {pending} paper(s) waiting for Codebuff. "
            f"Ask Codebuff to process the codebuff_tasks/ directory.",
            file=sys.stderr,
        )

    if complete > 0:
        print(
            f"→  {complete} paper(s) already processed. "
            f"Use --clean to remove their task files, or --reset to reprocess.",
            file=sys.stderr,
        )


def cmd_clean(dry_run: bool = False) -> None:
    """Remove task files whose output markdown files already exist.

    Args:
        dry_run: If True, only print what would be removed without deleting.
    """
    task_files = _find_task_files()

    if not task_files:
        print("No task files found.", file=sys.stderr)
        return

    to_remove: list[Path] = []

    for task_path in task_files:
        task = _load_task(task_path)
        if not task:
            continue
        output_path = task.get("output_path", "")
        if output_path and _output_exists(output_path):
            to_remove.append(task_path)

    if not to_remove:
        print("No completed task files to clean up.", file=sys.stderr)
        return

    print(
        f"{'Would remove' if dry_run else 'Removing'} {len(to_remove)} completed task file(s):",
        file=sys.stderr,
    )
    for task_path in to_remove:
        print(f"  {task_path.name}", file=sys.stderr)
        if not dry_run:
            try:
                task_path.unlink()
            except OSError as exc:
                print(f"    Error: {exc}", file=sys.stderr)

    if not dry_run:
        remaining = len(_find_task_files())
        print(f"\n✓  {remaining} task file(s) remaining.", file=sys.stderr)


def cmd_reset(cite_key: str | None = None, dry_run: bool = False) -> None:
    """Delete output markdown files so Codebuff can regenerate them.

    Args:
        cite_key: If provided, only reset outputs for this specific paper.
                  If None, reset all outputs for all queued tasks.
        dry_run: If True, only print what would be deleted without deleting.
    """
    task_files = _find_task_files()

    if not task_files:
        print("No task files found. Nothing to reset.", file=sys.stderr)
        return

    to_reset: list[Path] = []
    seen: set[str] = set()

    for task_path in task_files:
        task = _load_task(task_path)
        if not task:
            continue

        task_cite_key = task.get("cite_key", "")
        if cite_key and task_cite_key != cite_key:
            continue

        output_path = task.get("output_path", "")
        if output_path and output_path not in seen and _output_exists(output_path):
            to_reset.append(Path(output_path))
            seen.add(output_path)

    if not to_reset:
        scope = f"for '{cite_key}'" if cite_key else "for any queued task"
        print(f"No output files found {scope}.", file=sys.stderr)
        return

    scope = f"for '{cite_key}'" if cite_key else "across all papers"
    print(
        f"{'Would remove' if dry_run else 'Removing'} {len(to_reset)} output file(s) {scope}:",
        file=sys.stderr,
    )
    for output_path in to_reset:
        print(f"  {output_path}", file=sys.stderr)
        if not dry_run:
            try:
                output_path.unlink()
            except OSError as exc:
                print(f"    Error: {exc}", file=sys.stderr)

    if not dry_run:
        print(
            f"\n✓  Done. Ask Codebuff to reprocess the task files to regenerate outputs.",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Queue manager for Codebuff task files in ./codebuff_tasks/.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        default=False,
        help="List all queued tasks and their output status (default action).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        default=False,
        help="Remove task files whose output markdown files already exist.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        default=False,
        help="Delete output markdown files so Codebuff can regenerate them.",
    )
    parser.add_argument(
        "--cite-key",
        default=None,
        help="When used with --reset, only reset outputs for this specific paper.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be done without actually doing it (for --clean and --reset).",
    )

    args = parser.parse_args(argv)

    # --dry-run only makes sense with --clean or --reset
    if args.dry_run and not args.clean and not args.reset:
        print("Warning: --dry-run has no effect without --clean or --reset.", file=sys.stderr)

    # --list is the default action when no flags are given
    if not args.clean and not args.reset:
        cmd_list()
        return

    if args.clean:
        cmd_clean(dry_run=args.dry_run)

    if args.reset:
        cmd_reset(cite_key=args.cite_key, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
