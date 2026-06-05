# Agentic Skills Library — Summary & Robot Wiki Applications

## Overview

The [Agentic Skills Library](https://github.com/Sigurius23/Agentic-skills-Library) is a collection of 6 zero-dependency, context-window-optimized Python CLI tools built specifically for autonomous AI agents. Every tool outputs minified JSON on `stdout` (for the agent) and human-readable diagnostics on `stderr` (for the operator).

**Repository location:** `references/Agentic-skills-Library/`
**Installed to:** `~/.local/bin/` (symlinked)
**Database cache:** `~/.cache/oss-scout/scout.db` (6,755 tools indexed, 6 Awesome Lists)

---

## Architecture Principles

All 6 tools follow strict AI-Native design tenets:

1. **`stdout`/`stderr` isolation** — JSON on `stdout` for the agent, diagnostics on `stderr` for humans
2. **Zero dependencies** — Python 3 stdlib only (`urllib`, `sqlite3`, `re`, `ast`, `argparse`, `json`, `ssl`, `socket`, `subprocess`)
3. **Defensive AI engineering** — SSRF protection, auto-LIMIT clauses, read-only DB connections, SQL injection prevention
4. **Aggressive local caching** — SQLite-backed caches with TTLs protect external APIs from agent retry-loops
5. **Framework agnostic** — Works with Codebuff, Claude Code, AutoGen, LangChain, or a bare terminal

---

## The 6 Skills — Detailed

### 1. `oss-scout` — OSS Discovery & Trust Scoring
*Hallucination-proof dependency discovery and repository trust verification.*

| Feature | Detail |
|---------|--------|
| **Commands** | `search`, `trust`, `sync`, `status`, `cache` |
| **Data sources** | GitHub API, Hacker News Algolia, 6 curated Awesome Lists |
| **Trust formula** | `Score = (Stars/1000) - (Months Inactive) + 3(Awesome List) + 2(HN mentions)` |
| **Verdicts** | HIGH_TRUST ≥ 5, MODERATE ≥ 3, LOW ≥ 1, UNVERIFIED < 1 |
| **Local index** | SQLite FTS5, 6,755 tools, sub-millisecond query |
| **API keys** | `GITHUB_TOKEN` (optional, recommended for higher rate limits) |

**Robot Wiki applications:**
- Discover robotics libraries before installing (e.g., MuJoCo wrappers, ROS2 packages, SLAM implementations)
- Verify trustworthiness of GitHub repos before cloning as reference material
- Cross-reference candidate libraries against Awesome Lists for credibility
- Search with robotics-specific queries: `"whole body control"`, `"humanoid locomotion"`, `"sim-to-real transfer"`
- Prevent hallucinating fake repo names when writing project documentation

---

### 2. `paper-scout` — Academic Paper Discovery & Gap Analysis
*Academic literature search, citation verification, and knowledge gap detection.*

| Feature | Detail |
|---------|--------|
| **Commands** | `search`, `cite`, `recommend`, `gaps`, `sync`, `add`, `status`, `cache` |
| **Data sources** | OpenAlex (250M+ works), Semantic Scholar (200M+ papers) |
| **Impact formula** | `Impact = Citations + 5 × Influential Citations` |
| **Gap analysis** | Cross-references search results against local paper base |
| **Import formats** | BibTeX, JSON, Markdown, plain text (auto-detects DOIs) |
| **API keys** | `OPENALEX_API_KEY` (required, free), `SEMANTIC_SCHOLAR_API_KEY` (optional) |

**Robot Wiki applications:**
- **Direct complement to our existing pipeline:** Our `ingest.py` already uses Semantic Scholar for metadata — `paper-scout` adds gap analysis and recommendations
- Find papers on robotics topics we're missing before ingesting PDFs
- Verify citation counts and paper existence before citing (`paper-scout cite <doi>`)
- Discover related papers via `paper-scout recommend <doi>` after ingesting a key paper
- Run `paper-scout gaps "vision-language-action humanoid" --year-min 2024` to find papers missing from our collection
- Import our existing BibTeX library to build the local paper base for gap analysis
- Semantic search with AI embeddings for hard-to-query topics
- Download open-access PDFs directly from OpenAlex or Semantic Scholar

---

### 3. `text-humanizer` — AI-Slop Detection & Writing Quality Gate
*Deterministic linguistic analysis to detect AI-generated writing patterns.*

| Feature | Detail |
|---------|--------|
| **Commands** | `score`, `calibrate` |
| **Slop detection** | 24 forensic AI-slop words (weighted: "delve"=5, "crucial"=3, etc.) |
| **Structural patterns** | 7 regex patterns (em dash overuse, signposting, negative parallelisms) |
| **Cluster weighting** | Exponential penalty when slop words appear within 15 words of each other |
| **Stylometry** | Burstiness (Coefficient of Variation), Type-Token Ratio (vocabulary diversity) |
| **Voice calibration** | Learns user's sentence length, burstiness, and contraction density from samples |
| **False positive protection** | Strips code fences, inline code, blockquotes, and URLs before analysis |

**Robot Wiki applications:**
- **Quality gate for all generated wiki notes:** Pipe generated notes through `text-humanizer` (e.g., `cat wiki/papers/*.md | while read -r line; do echo "$line" | text-humanizer score; done`) to check agent-generated paper profiles for AI-slop before committing
- Use as a CI/CD gate: if `ai_score > 15`, flag the note for human revision
- Calibrate on our own writing style to detect when LLM-generated content diverges from our voice
- Apply to all PR descriptions, commit messages, and project documentation
- Pair with a manual review step for notes flagged with high slop scores
- **Note:** The current implementation only accepts inline text as a positional argument (no `-f` flag or stdin support in the shipped script, despite the README advertising them). For batch file scoring, wrap with a shell loop or extend the script.

---

### 4. `db-scout` — Safe, Read-Only Database Exploration
*SQLite exploration with three-layer security sandbox for AI agents.*

| Feature | Detail |
|---------|--------|
| **Commands** | `schema`, `sample`, `query` |
| **Layer 1** | Read-only URI connection (`?mode=ro`) — writes blocked at SQLite engine level |
| **Layer 2** | Statement allowlist — only `SELECT`, `PRAGMA`, `EXPLAIN`, `WITH` permitted |
| **Layer 3** | Dangerous keyword blocklist — `ATTACH`, `DROP`, `DELETE`, `UPDATE`, `INSERT`, `CREATE`, etc. |
| **Auto-LIMIT** | Appends `LIMIT 10` to plain SELECTs (preserves aggregates, GROUP BY, EXPLAIN) |
| **Cell truncation** | Large text/blob values capped at 100 chars |
| **Table validation** | Validates table names against `sqlite_master` to prevent injection |

**Robot Wiki applications:**
- Explore the `oss-scout` and `paper-scout` local SQLite databases safely
- Query the cached API responses without risk of corruption
- Inspect the FTS5 index contents to understand what's been indexed
- Sample paper base entries to verify sync integrity
- Future: if we build a local database of robot experiment logs, sensor data, or training metrics, `db-scout` provides safe agent access

---

### 5. `repo-scout` — Polyglot Codebase Structure Mapper
*Codebase skeleton extraction preventing agents from reading 10,000-line files blindly.*

| Feature | Detail |
|---------|--------|
| **Commands** | `map`, `file`, `tree`, `search`, `summary` |
| **Tier 1 (AST)** | Python — perfect fidelity via `ast` module (functions, classes, decorators, docstrings, type annotations, imports) |
| **Tier 2 (Regex)** | TypeScript/JavaScript, Go, Rust, Java — catches 90%+ of declarations |
| **Tier 3 (Fallback)** | Any language — keyword-level extraction (`def`, `fn`, `class`, `struct`, etc.) |
| **Safety** | Skips `node_modules`, `.git`, `__pycache__`, minified files, 500KB+ files |
| **Output** | Compressed JSON "skeleton" — no code bodies, only structural metadata |

**Robot Wiki applications:**
- **Map our own project** before making changes: `repo-scout map .` gives a structural overview of the ingest pipeline
- Map cloned reference codebases (e.g., `synto-master`, `gbrain-master`, `obsidian-wiki-main`) to understand their architecture without reading every file
- Search for specific robotics-related functions across reference codebases: `repo-scout search references/ "forward_kinematics"`
- Generate a directory tree of any reference repo before diving in
- Get high-level stats on any codebase before deep exploration

---

### 6. `net-wire` — SSRF-Protected Network Forensics & Web Extraction
*Safe network debugging, API testing, and web page text extraction.*

| Feature | Detail |
|---------|--------|
| **Commands** | `ports`, `kill`, `ping`, `fetch`, `extract` |
| **SSRF protection (4 layers)** | Cloud metadata IP blocking, private/loopback IP blocking, scheme allowlist, redirect TOCTOU validation |
| **`extract` command** | Fetches URL → strips HTML (`<script>`, `<style>`, `<nav>`, `<header>`, `<footer>`) → decodes 30+ entities → returns readable text |
| **Process safety** | PID 1 protected, SIGTERM → wait 1s → SIGKILL escalation |
| **Context protection** | API responses capped at 64KB, JSON recursively truncated, extracted text capped at 3,000 chars |
| **Cross-platform** | `lsof` → `ss` → `netstat` for ports; `kill` → `taskkill` for processes |

**Robot Wiki applications:**
- Check what's running on the local machine before starting services (e.g., before launching a simulation server)
- Kill zombie processes occupying ports needed for robot communication
- Test API endpoints for the LLM pipeline (`net-wire fetch "http://localhost:8000/v1/chat/completions" --allow-local`)
- Extract readable text from robotics blog posts and documentation URLs for manual curation: `net-wire extract "https://unitree.com/g1"`
- Health-check the HPC cluster endpoint or any remote service the pipeline depends on
- Debug network connectivity between the workstation and the G1 robot's onboard Jetson

---

## Integration Map — Skills × Robot Wiki Pipeline

```
Robot Wiki Pipeline Stage          Relevant Skills
─────────────────────────────────────────────────────────
PDF ingestion & metadata fetch  →  paper-scout (gap analysis, citation verification)
                                    net-wire (API health checks, text extraction)

LLM generation (paper profiles) →  text-humanizer (slop detection quality gate)
                                    net-wire (test LLM API endpoints)

Codebase exploration & dev      →  repo-scout (map project, search symbols)
                                    db-scout (safe SQLite exploration)

Dependency discovery             →  oss-scout (find & verify robotics libraries)
                                    oss-scout trust (verify before cloning repos)

Network & infrastructure         →  net-wire (ports, kill, API testing)

Research workflow                →  paper-scout + oss-scout (find papers, verify repos)
                                    net-wire extract (read article text from URLs)
```

---

## Quick Reference — All Commands

| Tool | Key Commands |
|------|-------------|
| `oss-scout` | `search "query"`, `trust "owner/repo"`, `sync`, `status` |
| `paper-scout` | `search "query" --semantic`, `cite <doi>`, `recommend <doi>`, `gaps "topic"`, `sync file.bib`, `status` |
| `text-humanizer` | `score "text to analyze"`, `calibrate "sample text"` |
| `db-scout` | `data.db schema`, `data.db sample users`, `data.db query "SELECT ..."` |
| `repo-scout` | `map ./src`, `file path/to/file.py`, `tree ./src`, `search ./src "functionName"`, `summary ./src` |
| `net-wire` | `ports`, `kill <pid>`, `ping <url>`, `fetch <url> --allow-local`, `extract <url>` |

---

## API Keys Needed

| Tool | Key | Required? | How to Get |
|------|-----|-----------|------------|
| `oss-scout` | `GITHUB_TOKEN` | Recommended (higher rate limits) | GitHub Settings → Developer settings → Personal access tokens |
| `paper-scout` | `OPENALEX_API_KEY` | **Yes** | Free at [openalex.org/users/me](https://openalex.org/users/me) |
| `paper-scout` | `SEMANTIC_SCHOLAR_API_KEY` | Optional (higher rate limits) | Free at [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api) |
| `text-humanizer` | None | — | Local only |
| `db-scout` | None | — | Local only |
| `repo-scout` | None | — | Local only |
| `net-wire` | None | — | No external APIs |

---

## Supplementary Assets

The repository also contains non-executable assets useful for agent integration:

| Asset | Path | Purpose |
|-------|------|---------|
| **System prompt** | `prompts/system_prompt.md` | Master agent instruction set — teaches any AI agent when and how to invoke the 6 tools |
| **Discovery agent prompt** | `prompts/discovery_agent.md` | Specialized prompt for research orchestration workflows |
| **LangChain tools** | `integrations/langchain_tools.py` | Python wrappers to expose skills as LangChain tools |
| **AutoGen skills** | `integrations/autogen_skills.py` | AutoGen-compatible skill definitions |
| **Freebuff/Codebuff setup** | `integrations/freebuff_setup.md` | Instructions for `.agents/knowledge.md` integration |
| **Edge case notes** | `EdgeCasesNotes.md` | Detailed architecture decisions, including why `web-scout` was folded into `net-wire` |

---

## Installation Status

✅ All 6 tools symlinked to `~/.local/bin/` and verified working.

- `repo-scout` — ✅ Tested (mapped 193 files across the project)
- `text-humanizer` — ✅ Tested (ai_score: 15.0 on test sentence)
- `net-wire` — ✅ Tested (detected 33 listening ports)
- `oss-scout` — ✅ Tested (synced 6,755 tools, ran robotics searches)
- `paper-scout` — ⚠ Needs `OPENALEX_API_KEY` to function
- `db-scout` — ✅ Ready (needs a `.db` file to explore)
