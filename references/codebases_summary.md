# References Codebases: Architectural and Technical Specifications

This document serves as a self-contained guide for LLMs and developers to understand the structure, specifications, and workflows of **scholar-agent** and **AutoSci** (OmegaWiki) without needing to parse the entire source code.

---

# 1. Scholar Agent (`scholar-agent`)

## Overview
**Scholar Agent** is a Python-based academic research assistant designed to build a local knowledge base of markdown files (knowledge cards) using online research (web search, Semantic Scholar, arXiv) and local BM25 indexing. It can be integrated into IDEs (Claude Code, VS Code Copilot) as an Model Context Protocol (MCP) server.

## Directory Structure
```
scholar-agent/
├── pyproject.toml              # Package config (Python 3.10+, uses fastmcp, PyMuPDF)
├── requirements.txt            # Package dependencies
├── .scholar.example.json       # Example configuration template
├── src/scholar_agent/
│   ├── __init__.py             # Module initialization
│   ├── server.py               # FastMCP Server containing 14 tools
│   ├── cli.py                  # CLI entrypoint (scholar-agent)
│   ├── runtime.py              # Manages package install states (editable vs standalone)
│   ├── adapters/               # MCP server adapters
│   ├── config/                 # Configurations, profiles, and environment path resolution
│   ├── config_data/            # Default/fallback config templates
│   ├── schemas/                # Schemas for answers, evidence, and domain routing policy
│   ├── templates/              # Skeleton layouts for paper analysis notes (EN & ZH)
│   ├── validation/             # Scripts to validate frontmatter and normalize notes
│   ├── installers/             # MCP registration modules for Claude, VS Code, OpenCode
│   └── engine/                 # Core business logic
│       ├── academic/           # Modules for paper search, analysis, scoring, and linking
│       │   ├── arxiv_search.py     # arXiv RSS + Semantic Scholar search
│       │   ├── conf_search.py      # Conference paper search (DBLP)
│       │   ├── paper_analyzer.py   # Obsidian-style deep-analysis note generator
│       │   ├── scoring.py          # 4-dim scoring (relevance, recency, popularity, quality)
│       │   ├── image_extractor.py  # PyMuPDF-based figure and text extractor
│       │   ├── note_linker.py      # Keyword wikilinking discoverer
│       │   └── daily_workflow.py   # Daily recommendation paper workflow
│       ├── search_providers/   # Search integrations (Semantic Scholar, arXiv, etc.)
│       ├── local_index.py      # BM25 index builder
│       ├── local_retrieve.py   # BM25 index queries & retrieval
│       ├── close_knowledge_loop.py # Quality-control and validation for new cards
│       ├── scholar_config.py   # Config reader/resolver
│       └── ...                 # Miscellaneous helpers (caching, exceptions, routing)
└── tests/                      # Testing suite (~266 test cases)
```

## Data Directories (Created upon initialization)
By default, data is stored at `~/scholar/` (Global) or `$(pwd)/scholar` (Project-Local).
- `config/`: Configuration files (`config.json`, `.scholar.json`).
- `knowledge/`: Local knowledge cards (structured `.md` files).
- `paper-notes/`: Deep academic analysis notes (Obsidian-compatible Markdown).
- `daily-notes/`: Daily recommendations (recommends top conference + arXiv papers).
- `indexes/`: BM25 search indices.
- `cache/`: API call cache directories.
- `outputs/`: Generated reports and HTML/image assets.

## Model Context Protocol (MCP) Tools
Exposed via `fastmcp` (run with `scholar-agent serve-mcp` or registered automatically).

### Core Tools (Always Available)
1. **`query_knowledge(query: str, limit: int = 5) -> str`**
   - Searches the local knowledge base using a BM25 index. Returns top-k matching cards.
2. **`save_research(query: str, answer_json: str, domain: str = "", language: str = "zh") -> str`**
   - Validates and persists structured research answers into the local knowledge base under `knowledge/<domain>/`.
   - `answer_json` must conform to `answer.schema.json`.
   - Enforces a quality gate (minimum length, evidence-backed claims, non-trivial content).
3. **`list_knowledge(topic: str | None = None) -> str`**
   - Lists all metadata for existing cards, optionally filtered by topic.
4. **`capture_answer(query: str, answer: str, tags: str = "") -> str`**
   - Captures a conversational response as a draft knowledge card (enforces a 150+ character minimum length).
5. **`ingest_source(source: str, title: str = "", tags: str = "", language: str = "zh") -> str`**
   - Ingests text or web page content (fetches URLs, converts HTML to Markdown) into a draft knowledge card.
6. **`build_graph() -> str`**
   - Builds an interactive knowledge graph HTML file (`graph.html`) using `vis.js`.

### Academic Tools (Enabled when `SCHOLAR_ACADEMIC=1`)
7. **`search_papers(query: str, categories: str, max_results: int, top_n: int, skip_hot: bool) -> str`**
   - Combines recent arXiv and hot Semantic Scholar papers, scoring them based on custom research interests.
8. **`search_conf_papers(venues: str, year: int, keywords: str, excluded_keywords: str, top_n: int) -> str`**
   - Searches DBLP for papers in top venues (CVPR, NeurIPS, ICLR, etc.), enriches them via Semantic Scholar, and scores them.
9. **`download_paper(paper_id: str, title: str, domain: str) -> str`**
   - Downloads a paper PDF from arXiv and stores it in the local `paper-notes/` workspace.
10. **`analyze_paper(paper_json: str, output_dir: str, language: str, all_papers_json: str, images_json: str, pdf_path: str) -> str`**
    - Parses paper metadata and PDF/abstract content to produce a comprehensive 20-section Markdown note.
11. **`extract_paper_images(paper_id: str, title: str, output_dir: str, pdf_path: str) -> str`**
    - Downloads arXiv sources to extract embedded figures (falls back to PyMuPDF extraction).
12. **`paper_to_card(paper_json: str, note_path: str) -> str`**
    - Evaluates paper summaries and creates a graph-linked knowledge card in the main wiki.
13. **`daily_recommend(top_n: int, language: str, skip_existing: bool, config_path: str, dual_track: bool) -> str`**
    - Runs the dual-track daily paper recommendation workflow (recommending 2 conference papers + 2 innovation arXiv papers).
14. **`link_paper_keywords(note_path: str, notes_dir: str) -> str`**
    - Scans notes to automatically discover and format known technical keywords into Obsidian `[[wikilinks]]`.

## CLI Interface Subcommands
- **`scholar-agent serve-mcp`**: Starts the FastMCP server.
- **`scholar-agent init`**: Installs data directories, config files, and registers the server with Claude/VS Code.
- **`scholar-agent doctor`**: Performs health, dependency (fastmcp, PyMuPDF), and write diagnostics.
- **`scholar-agent config {show,init,migrate}`**: Inspects, sets up, or migrates the configurations.
- **`scholar-agent install {claude,vscode,opencode} [--write|--status|--uninstall]`**: Generates and writes host-specific configuration settings.
- **`scholar-agent runtime {status,build-wheel,install-standalone,install-pipx}`**: Manages local developer build types.

---

# 2. AutoSci (`OmegaWiki`)

## Overview
**AutoSci** (known as **OmegaWiki**) realizes Andrej Karpathy's LLM-Wiki vision. It is a fully agentic academic platform centering on a structured local wiki as the single source of truth for the entire research lifecycle. Rather than a flat vector RAG, knowledge is compiled into 9 semantic entities connected by a bidirectional, typed relationship graph.

## Directory Structure
```
OmegaWiki/
├── CLAUDE.md                    # Root runtime contract and repo commands
├── setup.sh                     # Setup script to configure environments and languages
├── wiki/                        # Compounding knowledge base
│   ├── papers/                  #   Structured academic summaries
│   ├── concepts/                #   Cross-paper technical concept pages
│   ├── topics/                  #   Research maps, benchmarking trackers, gaps
│   ├── people/                  #   Researcher profiles
│   ├── ideas/                   #   Research ideas with lifecycles (proposed -> validated)
│   ├── experiments/             #   Planned, running, and completed experiment logs
│   ├── methods/                 #   Reusable techniques, architectures, and protocols
│   ├── Summary/                 #   Domain-wide surveys
│   ├── foundations/             #   Background knowledge (terminal wiki pages)
│   ├── outputs/                 #   Generated LaTex drafts, compilation output, and visual assets
│   ├── graph/                   #   Relationship store (edges.jsonl, citations.jsonl)
│   ├── index.md                 #   Auto-compiled table of contents
│   └── log.md                   #   Append-only chronological audit log
├── raw/                         # Source materials
│   ├── papers/                  #   User-supplied .pdf / .tex files (read-only)
│   ├── notes/                   #   User-supplied .md files (read-only)
│   ├── web/                     #   User-supplied .html files (read-only)
│   ├── discovered/              #   Auto-ingested papers from RSS or search feeds
│   └── tmp/                     #   Workspace for paper preparation sidecars
├── tools/                       # Core python engines and utility tools
│   ├── research_wiki.py         #   The core graph compiler/wiki engine (20+ commands)
│   ├── serve.py                 #   Interactive graph visualizer web app
│   ├── lint.py                  #   Checks for format, schemas, and missing reverse links
│   ├── discover.py              #   Gathers, scores, and ranks paper discovery candidates
│   ├── daily_arxiv.py           #   Daily arXiv RSS crawler and recommendation compiler
│   └── ...                      #   Helper scripts (latex compile, email, SSH remote, etc.)
├── .claude/skills/              # 26 instruction blocks (SKILL.md) defining Claude Code commands
├── runtime/                     # Declarative configuration definitions (no codegen)
│   ├── loader.py                #   Python access API to YAML config schemas
│   ├── templates/               #   Skeleton markdown templates for the 9 entity types
│   ├── policy/                  #   Write permissions (writers.yaml)
│   └── schema/                  #   Data schemas, conventions, and relationships
│       ├── entities.yaml        #     YAML schemas specifying fields of all 9 nodes
│       ├── edges.yaml           #     YAML schemas specifying edge properties/directions
│       ├── xref.yaml            #     YAML rules mapping forward links to reverse links
│       └── conventions.yaml     #     Naming rules, slug constraints, and storage paths
└── .github/workflows/           # Daily arXiv crons and recommendation email dispatchers
```

## Declarative Runtime Schemas (`runtime/schema/`)

### Node Entity Schemas (`entities.yaml`)
Every page in the wiki is a Markdown file located at `wiki/{kind}/{slug}.md` containing YAML frontmatter. The 9 types are:
1. **`papers`** (`wiki/papers/`): Stores research details (title, venue, year, tags, importance, contribution_type, cited_by, datasets, code_url).
2. **`concepts`** (`wiki/concepts/`): Tracks technical ideas across papers (definition, maturity, first_introduced, key_papers, related_concepts, parent_topic).
3. **`topics`** (`wiki/topics/`): Map of overall research subfields (key_venues, related_topics, key_people, key_papers, linked_ideas).
4. **`people`** (`wiki/people/`): Researcher credentials (affiliation, research_areas, homepage, scholar).
5. **`ideas`** (`wiki/ideas/`): Tracks generated research ideas through their lifecycle: `proposed -> in_progress -> tested -> (validated | failed)`.
6. **`methods`** (`wiki/methods/`): Cross-paper reusable technique details (type: architecture, training, inference, prompting, optimization, etc.).
7. **`experiments`** (`wiki/experiments/`): Logs experimental setups (model, dataset, hardware, framework, baseline, metrics, remote session info) and lifecycle: `planned -> running -> (completed | abandoned)`.
8. **`Summary`** (`wiki/Summary/`): High-level domain-wide survey documents.
9. **`foundations`** (`wiki/foundations/`): Core base references. Marked as `terminal: true` (receives inward links, but never writes reverse links).

### Edge Type Schemas (`edges.yaml`)
Relations are saved in `wiki/graph/edges.jsonl` (or `citations.jsonl` for citation links).
- **Paper ↔ Paper**: `same_problem_as` (symmetric), `similar_method_to` (symmetric), `builds_on` (directed), `challenges` (directed).
- **Paper → Concept**: `introduces_concept` (directed), `uses_concept` (directed), `extends_concept` (directed), `critiques_concept` (directed).
- **Workflow / Evidence**: `supports` (directed), `contradicts` (directed), `tested_by` (directed), `invalidates` (directed), `addresses_gap` (directed), `derived_from` (directed), `inspired_by` (directed).
- **Bibliographic**: `cites` (directed; tracks source: `semantic_scholar`, `parsed_bib`, or `manual`).

### Integrity & Cross-Referencing rules (`xref.yaml`)
Whenever an entity links to another using Obsidian `[[wikilink]]` syntax, `xref` ensures the reciprocal link is updated. Examples:
- Linking a `paper` to a `concept` adds that paper to the concept's `key_papers` frontmatter.
- Linking a `method` to a `paper` adds that method to the paper's `Related` body section.
- Linking an `experiment` to an `idea` adds that experiment to the idea's `linked_experiments` list.

## Core Helper Engine (`tools/research_wiki.py`)
Provides command-line subcommands to query and edit the wiki database, guaranteeing data integrity.
- **`init <wiki_root>`**: Seeds the wiki directory structures.
- **`slug <title>`**: Sanitizes titles into kebab-case slugs.
- **`add-edge <wiki_root> --from <from_id> --to <to_id> --type <type>`**: Creates semantic relations.
- **`add-citation <wiki_root> --from <from> --to <to>`**: Registers bibliographic links.
- **`add-citations-batch <wiki_root> --citer <citer>`**: Bulk imports cited works from JSON stdin.
- **`rebuild-context-brief <wiki_root>`**: Aggregates wiki status for LLM prompt injections.
- **`rebuild-open-questions <wiki_root>`**: Pulls gaps and open problems into `open_questions.md`.
- **`rebuild-projected-edges <wiki_root>`**: Converts link fields in frontmatter/markdown body into formal graph edges.
- **`stats <wiki_root>`**: Generates wiki usage statistics.
- **`maturity <wiki_root>`**: Evaluates wiki temperature (`cold`, `warm`, or `hot`).
- **`read-meta <path> [field]`**: Outputs specific frontmatter metadata fields as JSON.
- **`set-meta <path> <field> <value> [--append]`**: Atomically updates frontmatter variables.
- **`find <wiki_root> <entity_type> [--field value]`**: Searches nodes matching criteria.
- **`find-similar-concept <wiki_root> <title> [--aliases aliases]`**: Audits concept directories to prevent redundant conceptual nodes.
- **`query <wiki_root> {ready-to-test,orphans}`**: Locates experimental targets or unconnected nodes.
- **`neighbors <wiki_root> <node_id> [--depth d]`**: Explores graph connections using breadth-first traversal.
- **`compile-context <wiki_root> --for <purpose>`**: Compiles specific context templates matching token budgets.
- **`transition <path> --to <status> [--reason r]`**: Transitions status and appends details in `log.md`.
- **`dedup-edges <wiki_root>`** & **`dedup-citations <wiki_root>`**: Removes duplicate rows in graphs.
- **`rebuild-index <wiki_root>`**: Re-compiles `index.md` listing catalog contents.
- **`topic-backfill <wiki_root>`**: Appends matching papers to topic seminal_works / SOTA tracker (post-merge sweep for /init).
- **`checkpoint-{save,load,clear,set-meta,get-meta}`**: Manages state checkpoints for long-running batch sequences (resumable `/init` sessions).

---

# 3. Synto (`synto-master`)

## Overview
**Synto** is a Python CLI tool that turns raw Markdown notes into a self-improving, interlinked wiki powered by local LLMs. Successor to obsidian-llm-wiki-local (608★, 9k+ downloads). By [kytmanov](https://github.com/kytmanov). MIT licensed. **v0.4.0** (May 2026).

**Core insight:** Uses a two-tier LLM approach — a fast 4B model for analysis/concept extraction, a heavy 14B+ model for article writing. This keeps the pipeline cheap on consumer hardware.

## Directory Structure
```
synto-master/
├── pyproject.toml              # Package config (Python 3.11+, Click, Pydantic v2, MCP SDK)
├── install.py                  # Editable install script
├── src/synto/
│   ├── cli.py                  # Click-based CLI entry point
│   ├── config.py               # Two-tier config (per-vault synto.toml + global ~/.config/synto/)
│   ├── models.py               # Pydantic v2 schemas (AnalysisResult, SingleArticle, etc.)
│   ├── state.py                # SQLite state DB (note lifecycle, concept registry, metrics)
│   ├── ollama_client.py        # Thin httpx wrapper around Ollama HTTP API (no langchain)
│   ├── structured_output.py    # 3-tier JSON extraction fallback (native→regex→retry)
│   ├── vault.py                # Frontmatter parsing, wikilink extraction, atomic writes
│   ├── indexer.py              # Generates wiki/index.md + append-only operation log
│   ├── git_ops.py              # Auto-commit with [synto] prefix, safe undo via git revert
│   ├── watcher.py              # Debounced file watcher (watchdog + threading.Timer)
│   ├── pipeline/
│   │   ├── ingest.py           # Fast model: analyzes notes, extracts concepts, creates source pages
│   │   ├── compile.py          # Concept-driven: one article per concept, incremental, hand-edit protection
│   │   ├── query.py            # Index-based page routing (no embeddings), fast model selects, heavy model answers
│   │   └── lint.py             # Static health checks (orphans, broken links, stale articles)
│   └── providers/              # ~20 LLM providers via OpenAI-compatible API
├── tests/                      # ~200 tests (mock OllamaClient, tmp_path vaults, offline)
└── scripts/                    # Smoke tests, compare scripts
```

## Vault Structure
```
~/my-wiki/
├── raw/              ← User drops notes here (Synto never modifies)
├── wiki/             ← Published articles (Obsidian-compatible Markdown)
│   ├── .drafts/      ← LLM-generated articles waiting for review
│   ├── sources/      ← Per-note source summary pages
│   ├── queries/      ← Saved Q&A sessions
│   └── synthesis/    ← Synthesized answers published as wiki pages
├── .synto/
│   ├── state.db      ← SQLite: note lifecycle, concept registry, metrics
│   └── sources/      ← Archived originals (PDF, md, txt)
├── synto.toml        ← Vault config (provider, models, pipeline settings)
└── pack/             ← Agent-ready export (created by synto pack export)
```

## Key Mechanisms
- **Incremental compilation:** Change one note → only articles derived from that note recompile.
- **Rejection feedback loop:** Reject a draft with reasoning → reason injected into next compile prompt. Five rejections auto-blocks the concept.
- **Confidence scores:** Each draft rated 0–1. Approve selectively or set threshold.
- **Three-state lifecycle:** draft → verified → published.
- **Hand-edit protection:** SHA-256 content hash — manual edits never overwritten.
- **No embeddings, no vector database:** `synto query` routes via `INDEX.json`.
- **Source-type analysis:** 9 document types (notes, textbook, paper, spec, api_docs, web_article, corp_docs, transcript, unknown_text) with matched ingest prompts.
- **Multi-language:** Auto-detected at ingest. Articles written in source language.
- **Git-aware:** Every auto-operation commits with `[synto]` prefix.
- **LLM response cache:** SHA-256-keyed responses in SQLite.

## MCP Server (12 tools)
- **Wiki tools (8):** `list_articles`, `read_article`, `find_concept`, `search_articles`, `get_concept`, `list_sources`, `trace_lineage`, `answer_question`
- **Verbatim source tools (4):** `read_source_segment`, `search_source_segments`, `get_source_passages`, `list_segments`
- Source access governed by `[mcp.source_access]` in `synto.toml` (permissive_only / all / deny).

## CLI Surface
| Command | Purpose |
|---|---|
| `synto setup` | Interactive wizard (provider, models, default vault) |
| `synto init ~/my-wiki` | Create vault structure |
| `synto add paper.pdf --type paper` | Import PDF/MD/txt as tracked source |
| `synto run --vault ~/my-wiki` | Ingest + compile |
| `synto review` | Interactive draft review (approve/reject/edit/diff) |
| `synto watch` | File watcher (auto-process on save) |
| `synto query "what is X?"` | Index-routed Q&A |
| `synto serve` | MCP server |
| `synto pack export --target agents` | Portable agent-ready knowledge pack |
| `synto maintain` | Health check, stub creation, orphan cleanup |
| `synto eval` | Offline structural evaluation |
| `synto compare` | A/B model comparison |
| `synto doctor` | Configuration + connectivity diagnostics |

---

# 4. Obsidian-Wiki (`obsidian-wiki-main`)

## Overview
**obsidian-wiki** is a **skill-based framework** — a collection of ~30 Markdown instruction files (SKILL.md) that any AI coding agent can read and execute to build and maintain an Obsidian knowledge base. No scripts, no dependencies — the agent IS the LLM. By [Ar9av](https://github.com/Ar9av). MIT licensed.

**Core insight:** Instead of a monolithic script, skills are modular Markdown files the agent reads on demand. Works with 15+ coding agents (Claude Code, Cursor, Windsurf, Codex, Gemini CLI, Hermes, Pi, Kiro, etc.).

## Directory Structure
```
obsidian-wiki-main/
├── .skills/                          # Canonical skill definitions (source of truth)
│   ├── wiki-setup/SKILL.md           # Initialize vault structure
│   ├── wiki-ingest/SKILL.md          # Distill documents into wiki pages
│   ├── wiki-history-ingest/SKILL.md  # Unified history router (claude, codex, hermes, pi, etc.)
│   ├── wiki-query/SKILL.md           # Answer questions from the wiki
│   ├── wiki-lint/SKILL.md            # Find broken links, orphans, contradictions
│   ├── cross-linker/SKILL.md         # Auto-discover missing wikilinks
│   ├── tag-taxonomy/SKILL.md         # Enforce consistent tag vocabulary
│   ├── wiki-update/SKILL.md          # Sync current project's knowledge into vault
│   ├── wiki-export/SKILL.md          # Export graph to JSON, GraphML, Neo4j, HTML
│   ├── wiki-research/SKILL.md        # Autonomous multi-round web research
│   ├── wiki-synthesize/SKILL.md      # Discover and fill synthesis gaps
│   ├── memory-bridge/SKILL.md        # Browse/diff knowledge by which AI tool wrote it
│   ├── daily-update/SKILL.md         # Daily maintenance cycle
│   ├── skill-creator/SKILL.md        # Create new skills
│   └── ... (~30 total)
├── CLAUDE.md / AGENTS.md / GEMINI.md  # Bootstrap files per agent
├── setup.sh                           # One-command agent setup (symlinks skills into all agents)
├── pyproject.toml                     # Pure-stdlib CLI (obsidian-wiki setup)
├── obsidian_wiki/cli.py              # Thin CLI for skill installation
└── README.md / SETUP.md
```

## Vault Structure
```
$OBSIDIAN_VAULT_PATH/
├── index.md            # Master index — every page listed
├── log.md              # Chronological activity log
├── hot.md              # Session hot cache (~500 words) for context continuity
├── .manifest.json      # Tracks every ingested source: path, timestamps, pages produced
├── _meta/
│   ├── taxonomy.md     # Controlled tag vocabulary
│   └── *.base          # Obsidian Bases dashboard definitions
├── _insights.md        # Graph analysis (hubs, bridges, dead ends)
├── _raw/               # Staging area — rough notes promoted on next ingest
├── concepts/           # Abstract ideas, patterns, mental models
├── entities/           # Concrete things — people, tools, libraries, companies
├── skills/             # How-to knowledge, techniques, procedures
├── references/         # Factual lookups — specs, APIs, configs
├── synthesis/          # Cross-cutting analysis
├── journal/            # Time-bound entries
└── projects/           # Per-project knowledge
```

## Key Features
- **Delta tracking:** `.manifest.json` tracks every ingested source. Next ingest only processes new/changed.
- **Project-based organization:** Knowledge filed under projects/ when project-specific, globally when not.
- **Archive and rebuild:** Timestamped snapshots, restore any previous state.
- **Multi-agent ingest:** Dedicated skills for Claude, Codex, Hermes, OpenClaw, Pi, Copilot history.
- **Cross-agent targeted search:** `/wiki-claude "rust ownership"` finds conversations from a specific agent.
- **Provenance tracking:** Every claim tagged: extracted, `^[inferred]` (LLM synthesis), or `^[ambiguous]` (sources disagree).
- **Multimodal sources:** Screenshots, whiteboard photos, diagrams ingested with vision-capable models.
- **Wiki insights:** Hub detection, bridge pages, tag cluster cohesion, surprising connections.
- **Graph export:** JSON, GraphML, Neo4j Cypher, self-contained HTML visualization.
- **Tiered retrieval:** Read titles/tags/summaries first, only open bodies when cheap pass can't answer.
- **QMD semantic search (optional):** Plug in QMD for vector search over wiki and source documents.
- **Visibility tags:** `visibility/pii`, `visibility/internal`, `visibility/public` for content filtering.
- **Agent history ingestion:** Claude, Codex, Hermes, OpenClaw, Copilot, Pi — each with native format parsing.

## Complete Skill Catalog (~30 skills)
| Skill | Purpose |
|---|---|
| `wiki-setup` | Initialize vault structure |
| `wiki-ingest` | Distill documents into wiki pages |
| `wiki-history-ingest` | Unified history router |
| `wiki-query` | Answer questions from the wiki |
| `wiki-lint` | Find broken links, orphans, contradictions |
| `cross-linker` | Auto-discover missing wikilinks |
| `tag-taxonomy` | Enforce consistent tag vocabulary |
| `wiki-update` | Sync current project into vault |
| `wiki-export` | Export graph to JSON/GraphML/Neo4j/HTML |
| `wiki-capture` | Save current conversation as wiki note |
| `wiki-research` | Autonomous multi-round web research |
| `wiki-synthesize` | Discover and fill synthesis gaps |
| `wiki-dashboard` | Dynamic Obsidian Bases dashboards |
| `memory-bridge` | Browse/diff knowledge by AI tool origin |
| `daily-update` | Daily maintenance cycle |
| `impl-validator` | Validate implementation against goal |
| `graph-colorize` | Color-code Obsidian graph |

---

# 5. GBrain (`gbrain-master`)

## Overview
**GBrain** is a production-scale personal knowledge brain built in TypeScript on Bun by [Garry Tan](https://github.com/garrytan) (President & CEO of Y Combinator). Powers his own agent deployments: **146,646 pages, 24,585 people, 5,339 companies**, 66 cron jobs. MIT licensed. **v0.42.21.0** (June 2026).

**Core insight:** "Search gives you raw pages. GBrain gives you the answer." Combines hybrid retrieval (vector + BM25 + graph + reranker) with a synthesis layer that produces cited prose with explicit gap analysis.

## Directory Structure
```
gbrain-master/
├── package.json                # Bun/TypeScript, v0.42.21.0, 40+ dependencies
├── src/
│   ├── cli.ts                  # CLI entry point (compiled to single binary via bun build)
│   ├── core/
│   │   ├── engine.ts           # Contract-first BrainEngine interface (~47 operations)
│   │   ├── postgres-engine.ts  # Postgres + pgvector implementation
│   │   ├── pglite-engine.ts    # PGLite (Postgres 17 via WASM, zero-config default)
│   │   ├── operations.ts       # Single source: CLI + MCP generated from this
│   │   ├── migrate.ts          # Schema migrations (100+ versions)
│   │   ├── search/
│   │   │   ├── hybrid.ts       # Hybrid: vector HNSW + BM25 + reciprocal-rank fusion + reranker
│   │   │   ├── mode.ts         # 3 search modes (conservative, balanced, tokenmax)
│   │   │   ├── expansion.ts    # LLM multi-query expansion
│   │   │   └── autocut.ts      # Score-discontinuity result-sizing
│   │   ├── link-extraction.ts  # Zero-LLM entity ref extraction from markdown/wikilinks
│   │   ├── think/              # Synthesis layer ("brain layer" — gbrain think)
│   │   ├── minions/            # Durable job queue (BullMQ-shaped, Postgres-native)
│   │   ├── calibration/        # Hindsight calibration (Brier scores, voice gate)
│   │   ├── skillopt/           # Self-improving skill optimizer
│   │   ├── content-sanity.ts   # Content-quality gate (junk detection, quarantine)
│   │   └── ai/                 # Provider gateway (Anthropic, OpenAI, Google, etc.)
│   ├── commands/               # CLI command implementations (doctor, dream, sync, etc.)
│   └── mcp/                    # MCP server (30+ tools, stdio + HTTP + OAuth 2.1)
├── skills/                     # 43 curated skills + RESOLVER.md dispatcher
├── docs/                       # Architecture, tutorials, guides, integrations, eval
├── tests/                      # Unit, E2E, engine parity tests
├── evals/                      # Functional-area-resolver eval harness
├── admin/                      # React SPA admin dashboard
└── scripts/                    # ~50 CI/CD/verification scripts
```

## Key Capabilities

### Hybrid Search
- Vector (HNSW on pgvector) + BM25 keyword + reciprocal-rank fusion + source-tier boost + intent-aware query rewriting
- Three named modes: `conservative` (4K tokens), `balanced` (12K), `tokenmax` (20K+LLM expansion)
- Cross-encoder reranker (ZeroEntropy zerank-2, optional local Qwen3-Reranker)
- Per-query graph signals: adjacency boost, cross-source boost, session demote
- Autocut: score-discontinuity result-sizing — returns the *confident handful*, not a fixed wall
- NamedThingBench eval: **P@5 49.1%, R@5 97.9%** on 240-page corpus, **+31.4 P@5** over vector-only RAG

### Self-Wiring Knowledge Graph
- Every `put_page` extracts entity refs from markdown with zero LLM calls
- Typed edges: `attended`, `works_at`, `invested_in`, `founded`, `advises`, `mentions`, etc.
- Multi-hop traversal via `gbrain graph-query`
- Obsidian-style basename resolution (`[[bare-name]]` across folders) — opt-in

### Synthesis Layer (`gbrain think`)
- Retrieves top pages, composes synthesized answer with citations
- Gap analysis: tells you when a page is stale, claims are uncited, or pages contradict
- `find_trajectory` for temporal/entity queries ("how have their metrics changed?") 

### Job Queue (Minions)
- Durable sub-agents with two-phase pending→done persistence (crash-safe)
- Shell jobs with audit, child jobs with cascading timeouts
- Rate leases for outbound providers

### Schema Packs
- No fixed layout — ships with bundled packs (`gbrain-base-v2` with 15-type DRY/MECE taxonomy)
- User-authored packs via `gbrain schema detect` → `suggest` → `review` → `use`
- Seven-tier resolution chain

### Evals Framework
- `gbrain eval longmemeval` — public LongMemEval benchmark
- `gbrain eval export` + `replay` — capture real queries, replay against code changes
- `gbrain eval cross-modal` — cross-check outputs with three frontier models
- `gbrain eval retrieval-quality` — NamedThingBench for named-thing retrieval
- `gbrain eval suspected-contradictions` — find conflicts between takes

### Operational Hardening (selected from ~30 releases in CHANGELOG)
- Background work drain on exit (prevents DB lock pinning)
- AI call timeouts (stalled providers fall back to keyword results)
- Process watchdog (hard deadline for runaway cron sync)
- Resumable sync with checkpoint banking (44K-page imports)
- OOM-loop detection with cause-ranked doctor output
- Connection ownership tracking (shared singleton not nulled by borrowers)
- Content-quality gate (junk/Cloudflare detection, boilerplate flagging)
- Atomic binary self-update with autopilot silent channel

### MCP Server
- 30+ tools over stdio and HTTP (OAuth 2.1, DCR-style client registration)
- Admin dashboard at /admin
- Thin-client support (remote MCP)
- Company brain mode: federated multi-user, OAuth-scoped, source-scoped access

## Tech Stack
- **Runtime:** Bun 1.3.10+, TypeScript 5.6+
- **Database:** PGLite (embedded Postgres 17 via WASM) or Postgres + pgvector
- **AI:** AI SDK v6 (Anthropic, OpenAI, Google)
- **Search:** pgvector HNSW, BM25 ts_vector, ZeroEntropy reranker
- **Server:** Express 5, MCP SDK 1.29.0, OAuth 2.1
- **Testing:** Bun test, Docker-based CI, 29 E2E files

---

# 6. Karpathy's LLM Wiki Gist (Foundational Document)

## Overview
**Andrej Karpathy's original gist** ([442a6bf](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)) is the conceptual seed that inspired the entire LLM Wiki ecosystem — AutoSci, Synto, obsidian-wiki, our own pipeline, and indirectly GBrain. Published as an idea file, not an implementation.

## The Core Idea
"Instead of just retrieving from raw documents at query time, the LLM **incrementally builds and maintains a persistent wiki** — a structured, interlinked collection of markdown files that sits between you and the raw sources."

**Key difference from RAG:** The wiki is a persistent, compounding artifact. Knowledge is compiled once and kept current, not re-derived on every query.

## Three-Layer Architecture
- **Raw sources** — immutable, curated source documents. LLM reads from them, never modifies.
- **The wiki** — LLM-generated markdown files. The LLM owns this layer entirely.
- **The schema** — a document (CLAUDE.md / AGENTS.md) telling the LLM how the wiki is structured.

## Three Operations
1. **Ingest** — Read source → extract key info → write summary → update index → update entity/concept pages across wiki → append to log. One source might touch 10-15 pages.
2. **Query** — Search pages → read → synthesize answer with citations. **Good answers can be filed back into the wiki as new pages.**
3. **Lint** — Health-check: find contradictions, stale claims, orphan pages, missing cross-references, data gaps.

## Design Principles
- **Intentionally abstract** — no specific directory structure or tooling prescribed
- **Human in the loop** — read summaries, check updates, guide the LLM on emphasis
- **Wiki as git repo** — version history, branching, collaboration for free
- **Obsidian as IDE** — "Obsidian is the IDE; the LLM is the programmer; the wiki is the codebase"
- **Index-driven retrieval** at moderate scale (index.md → drill into pages), with optional qmd for larger wikis

## Historical Connection
Connects the idea to **Vannevar Bush's Memex (1945)** — a personal, curated knowledge store with associative trails. "The part he couldn't solve was who does the maintenance. The LLM handles that."

---

# 6.5. Second Brain (`second-brain-main`)

## Overview
**Second Brain** is a skill-based implementation of the Karpathy LLM Wiki pattern — a focused collection of **4 Markdown skill files** that any AI coding agent can read and execute. Installed via `npx skills add NicholasSpisak/second-brain`. Works with 40+ agents via the [Agent Skills standard](https://agentskills.io). By [NicholasSpisak](https://github.com/NicholasSpisak). Open source.

**Core insight:** Simplicity over feature sprawl. Four operations cover the full lifecycle — setup, ingest, query, lint — each in a single well-documented SKILL.md.

## Directory Structure
```
second-brain-main/
├── README.md                     # User-facing docs (install, quickstart, FAQ)
├── skills/
│   ├── second-brain/SKILL.md          # Onboarding wizard (5-step interactive setup)
│   ├── second-brain-ingest/SKILL.md   # Source processing → wiki pages (8-step workflow)
│   ├── second-brain-query/SKILL.md    # Question answering with tiered search
│   └── second-brain-lint/SKILL.md     # Health-check (8 audit steps, severity-ranked)
├── docs/
│   ├── REQUIREMENTS.md           # Blueprint & origin story — reusable specification
│   ├── llm-wiki.md               # Local copy of Karpathy's original gist
│   └── assets/                   # Screenshots for README
└── tests/
```

## Vault Structure (created by onboarding wizard)
```
your-vault/
├── raw/            # Inbox — drop sources here (LLM never modifies)
│   └── assets/     # Images and attachments
├── wiki/           # LLM-maintained wiki
│   ├── sources/    # One summary per ingested source (factual only)
│   ├── entities/   # People, orgs, products, tools
│   ├── concepts/   # Ideas, frameworks, theories, patterns
│   ├── synthesis/  # Comparisons, analyses, themes (compounds from queries)
│   ├── index.md    # Master catalog with one-line summaries per page
│   └── log.md      # Chronological operation record (parseable with grep)
└── output/         # Reports and generated artifacts
```

## Four Skills

### `/second-brain` — Onboarding Wizard
- 5-step interactive: vault name, location, domain/topic, agent config, optional tools
- Auto-detects running agent, generates correct config file
- Generates 5-8 domain-specific tags from user's topic description
- Offers to install: `summarize`, `qmd`, `agent-browser`
- Idempotent — safe to re-run

### `/second-brain-ingest` — Source Processing
- 8-step workflow: read → discuss with user → create source summary → update entity/concept pages → add wikilinks → update index → update log → report results
- Delta detection via `wiki/log.md` (grep for previously ingested filenames)
- Single source typically touches 10-15 wiki pages
- **Prefer updating existing pages over creating new ones**
- When contradictions found: update page AND note contradiction with both sources cited

### `/second-brain-query` — Question Answering
- Tiered search: index.md first → qmd if available → read relevant pages → follow wikilinks → raw sources last
- Format output to match question type
- Always cite with `[[wikilinks]]`
- **Offer to save valuable answers** as `wiki/synthesis/` pages

### `/second-brain-lint` — Health Check
- **8 audit steps:** broken wikilinks, orphans, contradictions, stale claims, missing pages, missing cross-references, index consistency, data gaps
- Severity-ranked: Errors (must fix), Warnings (should fix), Info (nice to fix)
- Each finding: what, where, fix
- Recommended: after every 10 ingests or monthly

## Key Design Decisions
- **Agent-agnostic** — same wiki conventions work in any agent's config. Switch without rebuilding.
- **Human-in-the-loop by default** — ingest explicitly pauses to discuss key takeaways before writing
- **Factual vs interpretive separation** — source summaries are factual; concept/synthesis pages are interpretive
- **Index-driven retrieval** — `wiki/index.md` for moderate scale; `qmd` as optional upgrade
- **Compounding queries** — valuable answers saved back as wiki pages

## Blueprint Document (REQUIREMENTS.md)
Notable artifact — a single document serving as both origin story and reusable specification:
- ORIGIN (links to Karpathy's tweet + gist)
- THE PATTERN (three folders, agent config as the brain)
- WHAT YOU NEED (Obsidian, agent, Web Clipper)
- FOUR OPERATIONS (onboarding, ingest, query, lint — at requirement level)
- THE AGENT CONFIG FILE (architecture, page format, operations, 10 rules)
- MULTI-AGENT SUPPORT (switch without rebuilding)
- OPTIONAL TOOLS (summarize, qmd, agent-browser)
- HOW IT ALL FITS TOGETHER (concept-to-implementation mapping)

## Comparison to Obsidian-Wiki
| Aspect | Obsidian-Wiki | Second Brain |
|---|---|---|
| Skills | ~30 | 4 |
| Install | pip + bash + npx | npx only |
| Agent platforms | 15+ | 40+ |
| Vault categories | 10 | 4 |
| Delta tracking | .manifest.json | log.md grep |
| Provenance tracking | ✅ | ❌ |
| Agent history ingest | ✅ (6+ agents) | ❌ |
| Blueprint doc | ❌ | ✅ (REQUIREMENTS.md) |
| Complexity | Feature-rich | Minimal |

---

# 8. Structural Comparison (All Codebases)

| Feature | Scholar Agent | AutoSci | Synto | Obsidian-Wiki | Second Brain | GBrain | Our Pipeline |
|---|---|---|---|---|---|---|---|---|
| **Architecture** | Python + FastMCP Server | Script suite + Claude skills | Python CLI (Click) | Markdown skill files (~30) | Markdown skill files (4) | TypeScript/Bun + CLI binary | Python linear pipeline |
| **Paradigm** | MCP server with tools | Agent-driven wiki mgmt | Local LLM pipeline | Agent IS the LLM | Agent IS the LLM (minimal) | Postgres-native brain | Sequential script |
| **Storage** | Flat files + BM25 index | 9 entity partitions + JSONL graph | SQLite + Obsidian vault | Obsidian vault + .manifest.json | Obsidian vault + log.md | PGLite/Postgres + pgvector + HNSW | Flat markdown files |
| **Relationship Graph** | Tags/links only | Explicit JSONL edges + bidirectional | Wikilinks only | Wikilinks only | Wikilinks only | Typed edges + auto-extraction + graph traversal | Flat files only |
| **Retrieval** | BM25 local index | File search + index.md | INDEX.json routing (no embeddings) | Index.md + optional QMD vector | Index.md + optional qmd | Hybrid: vector HNSW + BM25 + RRF + reranker | None yet |
| **LLM Usage** | Paper analysis, scoring | Auto-ingest + compile | Two-tier: fast 4B + heavy 14B | Agent-driven (external) | Agent-driven (external) | Synthesis, enrichment, skillopt | Two-pass: profile + crossref |
| **Integration** | MCP (standard protocol) | Claude Code slash-skills | MCP server (12 tools) | 15+ agent skill dirs | 40+ agents (npx skills add) | MCP (30+ tools) + OAuth 2.1 | CLI only |
| **Human Review** | None | None | Rejection feedback loop | Active (read/check/guide) | Explicit "discuss with user" step | doctor, enrich, quarantine review | None |
| **Operational Maturity** | Test suite (266 cases) | Linter + xref rules | ~200 tests | None (agent-driven) | Blueprint doc (REQUIREMENTS.md) | Extensive (100+ migrations, evals, watchdog, OOM detection) | 147 tests |
| **Scale Target** | Research papers | Research lifecycle | Personal notes → ~200 sources | Personal knowledge | Personal knowledge | 146K+ pages (production) | ~94 papers |
| **Multi-User** | No | No | No | No | No | Yes (company brain, OAuth-scoped) | No |
| **Delta Tracking** | No | No | Incremental compile | .manifest.json | log.md grep | Checkpoint banking (resumable sync) | No |
| **Primary Interface** | `scholar-agent` CLI + MCP | `python3 tools/research_wiki.py` | `synto` CLI | Agent slash commands (`/wiki-*`) | Agent slash commands (`/second-brain-*`) | `gbrain` CLI + MCP | `python ingest.py --pdf` |
