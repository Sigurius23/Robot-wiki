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

# 3. Structural Comparison

| Feature | Scholar Agent (`scholar-agent`) | AutoSci (`OmegaWiki`) |
|---|---|---|
| **Architecture** | Python package + FastMCP Server | Custom script suite (`tools/`) + Claude Code slash-skills |
| **Storage Model** | Simple folders + flat list files + BM25 index | 9 folder entity partitions + Obsidian markdown vaults |
| **Relationship Graph** | None (uses direct tags/links) | Explicit JSONL edge/citation files + bidirectional links |
| **Integration** | Standard Model Context Protocol (MCP) | Custom Claude Code skill configs (`.claude/skills/`) |
| **Verification Gate** | Schema check + minimal content length | Scripted structural linter (`lint.py`) + YAML rules |
| **Workspace Mode** | Shared Global or isolated Project-Local | Standard Project-Local repo tracking |
| **Primary CLI Interface** | `scholar-agent` commands | `python3 tools/research_wiki.py` subcommands |
