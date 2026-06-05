# Terminal Tools

You have 6 CLI tools installed at `~/.local/bin/`. They all output minified JSON on `stdout`. Parse it. Diagnostics go to `stderr` — ignore those.

## Rules

- **Never hallucinate** repo names, paper DOIs, or citation counts. Use the tools to verify.
- **Never run raw SQL.** Use `db-scout`.
- **Check trust score** before recommending any repo. Reject trust < 3 (UNVERIFIED or LOW).
- **After writing docs**, run `text-humanizer` on your output. Revise if `ai_score > 15`.
- **Use `--allow-local`** for any localhost URL.
- **Use `repo-scout` before reading files** to understand unfamiliar codebase structure.

## Project Context

This is the **Robot Wiki** — a literature review pipeline and knowledge base for robotics research. Key facts:

- **Robot:** Unitree G1 humanoid (Edu Edition) with Jetson Orin NX (100 TOPS), Livox Mid-360 LiDAR, Intel RealSense D435i
- **Workstation:** NVIDIA RTX 5090 (24GB VRAM), 64GB RAM, 2TB NVMe
- **Pipeline:** `ingest.py` processes PDFs → extracts metadata via Semantic Scholar → generates Obsidian wiki notes with LLM (NIM/DeepSeek V4 Pro)
- **12 implementation decisions** cross-referenced against every paper (agent architecture, coordination, communication, safety, etc.)
- **Wiki vault:** `wiki/papers/`, `wiki/implementation-decisions/`, `wiki/methods/`, `wiki/our-project-hardware/`

## Tools

### oss-scout — Find and verify robotics libraries
```
oss-scout search "humanoid locomotion"       # find tools
oss-scout trust "owner/repo"                # verify before cloning
oss-scout sync                              # rebuild local index (10 lists, 7,800+ tools)
oss-scout status                            # see index stats
```
**Index includes:** 4 robotics-focused Awesome Lists (robotics, robotic_tooling, robot_learning, legged_locomotion) plus 6 general lists.

### paper-scout — Academic paper discovery & gap analysis
```
paper-scout search "topic" --source s2 --year-min 2024    # Semantic Scholar search
paper-scout search "topic" --source openalex --semantic    # OpenAlex embedding search
paper-scout cite "10.xxxx/..."                            # verify paper exists
paper-scout gaps "humanoid locomotion" --year-min 2023     # find missing papers
paper-scout recommend "10.xxxx/..."                       # similar papers
paper-scout sync wiki/papers/some-file.md                 # import DOIs from wiki
paper-scout status                                        # base stats
```
**Supports:** DOI, ArXiv ID, OpenAlex ID, Semantic Scholar ID auto-detection. Impact formula: `Citations + 5 × Influential Citations`.

### repo-scout — Map codebases (use before reading files)
```
repo-scout map .                             # structural map of whole project
repo-scout map references/synto-master       # map a reference codebase
repo-scout search . "functionName"           # find definitions
repo-scout file src/llm_client.py            # single file deep-map
repo-scout tree .                            # directory overview with sizes
repo-scout summary .                         # language/file stats
```
**Polyglot:** Python (AST), TypeScript/JS/Go/Rust/Java (regex), any language (keyword fallback).

### db-scout — Safe database exploration
```
db-scout ~/.cache/oss-scout/scout.db schema        # explore oss-scout index
db-scout ~/.cache/paper-scout/papers.db schema     # explore paper base
db-scout ~/.cache/paper-scout/papers.db sample paper_base  # sample entries
db-scout file.db query "SELECT ..."                # read-only queries (auto-LIMIT)
```

### net-wire — Network debugging & web extraction
```
net-wire ports                              # list listening ports
net-wire kill 8492                          # free a blocked port
net-wire ping "url" --allow-local           # health check
net-wire fetch "http://localhost:8000/v1/chat/completions" --allow-local  # test LLM API
net-wire extract "https://unitree.com/g1"   # read web page (HTML stripped)
```

### text-humanizer — Check docs for AI slop
```
text-humanizer score "text to analyze"       # score inline text
text-humanizer score "$(cat file.md)"         # score a file's content
text-humanizer calibrate "sample prose"       # learn project writing style
```
**Note:** Current implementation accepts inline text only (no `-f` flag). Use `"$(cat file.md)"` to score files.

## Quick Decision Guide

| I need to... | Run this |
|---|---|
| Find a robotics library | `oss-scout search "concept"` |
| Verify a repo before cloning | `oss-scout trust "owner/repo"` |
| Find papers on a topic | `paper-scout search "topic" --source s2 --year-min 2024` |
| Find papers we're missing | `paper-scout gaps "topic" --year-min 2023` |
| Verify a paper exists | `paper-scout cite "DOI"` |
| Understand unfamiliar code | `repo-scout map ./path` |
| Find where X is defined | `repo-scout search ./path "X"` |
| Explore a database safely | `db-scout file.db schema` |
| Debug a port conflict | `net-wire ports` then `net-wire kill <pid>` |
| Test an API endpoint | `net-wire fetch "url" --allow-local` |
| Read a web page | `net-wire extract "url"` |
| Check docs for AI slop | `text-humanizer score "$(cat file.md)"` |

## API Keys Configured

| Key | Status | Used by |
|-----|--------|---------|
| `GITHUB_TOKEN` | ✅ | oss-scout (higher rate limits) |
| `OPENALEX_API_KEY` | ✅ | paper-scout (OpenAlex search) |
| `SEMANTIC_SCHOLAR_API_KEY` | ✅ | paper-scout (S2 search), pipeline ingest.py |
| `NIM_API_KEY` | ✅ | pipeline LLM generation |

## Research Workflow

When asked to do deep multi-source research, follow this orchestration order:

1. **Current state → web search** (use your built-in `researcher-web` agent)
2. **Academic depth → paper-scout** (`search` then `cite` to verify, then `gaps` to find missing)
3. **Code & community → oss-scout** (`search` then `trust` on top results before recommending)
4. **Synthesis → combine all three** into a structured comparison with source attribution

See `references/Agentic-skills-Library/prompts/discovery_agent.md` for the full research protocol.
