#!/usr/bin/env python
"""
audit_wiki.py — Audit A/B counts across the wiki vault.

Checks that every paper profile (wiki/papers/) has a corresponding
crossref note (wiki/implementation-decisions/) and vice versa.
Flags mismatches, orphans, and reports per-folder and global totals.

Usage:
    python audit_wiki.py                    # full audit (default)
    python audit_wiki.py --brief            # only show mismatches and summary
    python audit_wiki.py --folder bonding   # audit a single folder
    python audit_wiki.py --json             # machine-readable output
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAPERS_DIR = ROOT / "wiki" / "papers"
CROSSREF_DIR = ROOT / "wiki" / "implementation-decisions"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _discover_folders() -> list[str]:
    """Return all subdirectories in wiki/papers/, excluding top-level .md files."""
    if not PAPERS_DIR.is_dir():
        return []
    folders = sorted(
        d.name for d in PAPERS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )
    # Also check crossref dir for any folders not present in papers (rare)
    if CROSSREF_DIR.is_dir():
        for d in CROSSREF_DIR.iterdir():
            if d.is_dir() and d.name not in folders and not d.name.startswith("."):
                folders.append(d.name)
    return sorted(folders)


def _count_profiles(folder: str) -> set[str]:
    """Return the set of profile stems (filenames minus .md) in a folder."""
    folder_path = PAPERS_DIR / folder
    if not folder_path.is_dir():
        return set()
    return {
        f.stem for f in folder_path.iterdir()
        if f.is_file() and f.suffix == ".md"
    }


def _count_crossrefs(folder: str) -> set[str]:
    """Return the set of crossref stems (filenames minus '-crossref.md') in a folder."""
    folder_path = CROSSREF_DIR / folder
    if not folder_path.is_dir():
        return set()
    result = set()
    for f in folder_path.iterdir():
        if f.is_file() and f.name.endswith("-crossref.md"):
            # Strip "-crossref.md" suffix
            stem = f.name[:-len("-crossref.md")]
            result.add(stem)
    return result


def _top_level_profiles() -> set[str]:
    """Return the set of top-level .md files directly in wiki/papers/."""
    if not PAPERS_DIR.is_dir():
        return set()
    return {
        f.stem for f in PAPERS_DIR.iterdir()
        if f.is_file() and f.suffix == ".md"
    }


def _top_level_crossrefs() -> set[str]:
    """Return the set of top-level crossref stems directly in wiki/implementation-decisions/."""
    if not CROSSREF_DIR.is_dir():
        return set()
    result = set()
    for f in CROSSREF_DIR.iterdir():
        if f.is_file() and f.name.endswith("-crossref.md"):
            stem = f.name[:-len("-crossref.md")]
            result.add(stem)
    return result


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def run_audit(
    folders: list[str] | None = None,
    brief: bool = False,
    json_output: bool = False,
) -> dict:
    """Run the full audit and return results as a dict."""
    if folders is None:
        folders = _discover_folders()

    if not folders:
        print("No wiki folders found. Are you in the right directory?", file=sys.stderr)
        return {
            "folders": [],
            "total_profiles": 0,
            "total_crossrefs": 0,
            "mismatches": 0,
            "orphan_profiles": 0,
            "orphan_crossrefs": 0,
            "global_matched": False,
        }

    results = {
        "folders": [],
        "total_profiles": 0,
        "total_crossrefs": 0,
        "mismatches": 0,
        "orphan_profiles": 0,
        "orphan_crossrefs": 0,
    }

    all_ok = True

    for folder in folders:
        profiles = _count_profiles(folder)
        crossrefs = _count_crossrefs(folder)

        a = len(profiles)
        b = len(crossrefs)
        matched = a == b

        profiles_without_crossref = profiles - crossrefs
        crossrefs_without_profile = crossrefs - profiles

        folder_result = {
            "folder": folder,
            "profiles": a,
            "crossrefs": b,
            "matched": matched,
            "profiles_orphaned": sorted(profiles_without_crossref),
            "crossrefs_orphaned": sorted(crossrefs_without_profile),
        }
        results["folders"].append(folder_result)
        results["total_profiles"] += a
        results["total_crossrefs"] += b

        if not matched:
            results["mismatches"] += 1
            results["orphan_profiles"] += len(profiles_without_crossref)
            results["orphan_crossrefs"] += len(crossrefs_without_profile)
            all_ok = False

    # Top-level files
    tl_profiles = _top_level_profiles()
    tl_crossrefs = _top_level_crossrefs()
    results["top_level_profiles"] = len(tl_profiles)
    results["top_level_crossrefs"] = len(tl_crossrefs)
    results["top_level_matched"] = tl_profiles == tl_crossrefs
    results["top_level_profiles_orphaned"] = sorted(tl_profiles - tl_crossrefs)
    results["top_level_crossrefs_orphaned"] = sorted(tl_crossrefs - tl_profiles)

    # True grand totals (subfolder + top-level)
    grand_a = results["total_profiles"] + results["top_level_profiles"]
    grand_b = results["total_crossrefs"] + results["top_level_crossrefs"]
    results["grand_profiles"] = grand_a
    results["grand_crossrefs"] = grand_b

    # Global matched
    results["global_matched"] = (
        results["total_profiles"] == results["total_crossrefs"]
        and all_ok
        and results["top_level_matched"]
    )

    # Output
    if json_output:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return results

    # Human-readable output
    _print_report(results, brief)

    return results


def _print_report(results: dict, brief: bool) -> None:
    """Print the audit report in human-readable format."""
    ok = "✓" if results["global_matched"] else "✗"

    grand_a = results.get("grand_profiles", results["total_profiles"])
    grand_b = results.get("grand_crossrefs", results["total_crossrefs"])

    print(f"\n{ok}  Wiki A/B Audit", file=sys.stderr)
    print(f"   Subfolder profiles:  {results['total_profiles']}", file=sys.stderr)
    print(f"   Subfolder crossrefs: {results['total_crossrefs']}", file=sys.stderr)
    if results["top_level_profiles"] > 0 or results["top_level_crossrefs"] > 0:
        print(f"   Top-level profiles:  {results['top_level_profiles']}", file=sys.stderr)
        print(f"   Top-level crossrefs: {results['top_level_crossrefs']}", file=sys.stderr)
        if not results["top_level_matched"]:
            print(f"   ⚠️  Top-level mismatch", file=sys.stderr)
    print(f"   Grand total:         {grand_a} profiles / {grand_b} crossrefs", file=sys.stderr)

    # Per-folder table
    if not brief or results["mismatches"] > 0:
        print(f"\n{'Folder':<25} {'A':>4} {'B':>4}  Status", file=sys.stderr)
        print("-" * 50, file=sys.stderr)

        for f in results["folders"]:
            a = f["profiles"]
            b = f["crossrefs"]
            status = "✓ OK" if f["matched"] else f"⚠️  MISMATCH (+{f['profiles_orphaned']} A, +{f['crossrefs_orphaned']} B)"
            print(f"  {f['folder']:<23} {a:>4} {b:>4}  {status}", file=sys.stderr)

    # Orphan details
    has_orphans = (
        results["orphan_profiles"] > 0
        or results["orphan_crossrefs"] > 0
        or (results.get("top_level_profiles_orphaned") or results.get("top_level_crossrefs_orphaned"))
    )
    if has_orphans:
        print(f"\n  --- Orphan Details ---", file=sys.stderr)
        for f in results["folders"]:
            if f["profiles_orphaned"]:
                print(f"\n  📄 {f['folder']}/ — Profiles WITHOUT crossrefs:", file=sys.stderr)
                for stem in f["profiles_orphaned"]:
                    print(f"       • {stem}.md", file=sys.stderr)
            if f["crossrefs_orphaned"]:
                print(f"\n  🔗 {f['folder']}/ — Crossrefs WITHOUT profiles:", file=sys.stderr)
                for stem in f["crossrefs_orphaned"]:
                    print(f"       • {stem}-crossref.md", file=sys.stderr)
    # Top-level orphans — empty lists are falsy, non-empty are truthy
        if results.get("top_level_profiles_orphaned"):
            print(f"\n  📄 wiki/papers/ (top-level) — Profiles WITHOUT crossrefs:", file=sys.stderr)
            for stem in results["top_level_profiles_orphaned"]:
                print(f"       • {stem}.md", file=sys.stderr)
        if results.get("top_level_crossrefs_orphaned"):
            print(f"\n  🔗 wiki/implementation-decisions/ (top-level) — Crossrefs WITHOUT profiles:", file=sys.stderr)
            for stem in results["top_level_crossrefs_orphaned"]:
                print(f"       • {stem}-crossref.md", file=sys.stderr)

    # Summary
    print(f"\n{'─' * 50}", file=sys.stderr)
    if results["global_matched"]:
        print(f"✅  All A/B counts match — vault is consistent.", file=sys.stderr)
    else:
        print(f"❌  {results['mismatches']} folder(s) with mismatches. "
              f"Fix: add missing profiles or crossrefs, or remove orphaned files.", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Audit A/B counts across wiki/papers/ and wiki/implementation-decisions/.",
    )
    parser.add_argument(
        "--brief",
        action="store_true",
        default=False,
        help="Only show mismatches and summary (skip per-folder table when all OK).",
    )
    parser.add_argument(
        "--folder",
        default=None,
        help="Audit only a single folder (e.g., 'pgg-simulation', 'bonding').",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results as machine-readable JSON.",
    )

    args = parser.parse_args(argv)

    # Warn if both --json and --brief are used (--json takes priority)
    if args.json and args.brief:
        print("Warning: --brief is ignored when --json is used.", file=sys.stderr)

    folders = [args.folder] if args.folder else None

    results = run_audit(
        folders=folders,
        brief=args.brief,
        json_output=args.json,
    )

    # Exit code: 0 if all matched, 1 if mismatches found
    if not results["global_matched"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
