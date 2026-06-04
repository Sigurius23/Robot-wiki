# Synto: Architectural and Technical Summary

## Overview
**Synto** is a Python CLI tool (`pip install synto`) that turns raw Markdown notes into a self-improving, interlinked wiki powered by local LLMs. Successor to [obsidian-llm-wiki-local](https://github.com/kytmanov/obsidian-llm-wiki-local) (608★, 9k+ downloads). By [kytmanov](https://github.com/kytmanov). MIT licensed.

**Core insight:** raw notes are source material, not the final artifact. The LLM compiles them into a structured, cross-linked wiki — and keeps it current as you add more.

**Tagline:** "Treat your notes as source material, not as the final artifact."

## How it works (4-stage pipeline)

```
raw/*.md → Stage 1: Import → Stage 2: Ingest (fast 4B model) → Stage 3: Compile (heavy 14B+ model) → Stage 4: Export (MCP pack)
```

**Two-tier LLM model approach:**
- **Fast model** (4B params, e.g. Gemma 4 `gemma4:e4b`) — pattern-matching. Extracts concepts, summaries, relationships, language detection. Fast and cheap.
- **Heavy model** (14B+ params, e.g. Qwen 2.5 14B) — reasoning. Writes coherent, cross-linked articles from extracted concepts. One article per concept.

## Directory structure

```
synto-master/
├── pyproject.toml              # Package config (Python 3.11+, Click, Pydantic v2, httpx, MCP)
├── README.md                   # Comprehensive documentation
├── CLAUDE.md                   # Agent context: architecture, conventions, testing
├── CHANGELOG.md                # Detailed release history (0.1.1 → 0.4.0)
├── install.py                  # Editable install script
├── src/synto/
│   ├── cli.py                  # Click-based CLI entry point
│   ├── config.py / global_config.py  # Two-tier config (vault synto.toml + ~/.config/synto/config.toml)
│   ├── models.py               # Pydantic v2 schemas (AnalysisResult, SingleArticle, PageSelection, etc.)
│   ├── state.py                # SQLite state DB (note lifecycle, concept registry, metrics)
│   ├── ollama_client.py        # Thin httpx wrapper (no langchain)
│   ├── structured_output.py    # 3-tier JSON extraction fallback
│   ├── vault.py                # Frontmatter parsing, wikilink extraction, atomic writes
│   ├── indexer.py              # INDEX.md generation
│   ├── git_ops.py              # Auto-commit + safe undo
│   ├── watcher.py              # Debounced file watcher
│   ├── pipeline/
│   │   ├── ingest.py           # Fast model analyzes raw notes, extracts concepts
│   │   ├── compile.py          # Concept-driven article compilation (incremental)
│   │   ├── query.py            # Index-based page routing (no embeddings)
│   │   └── lint.py             # Static health checks
│   └── providers/              # ~20 LLM providers via OpenAI-compatible API
├── tests/                      # ~200 test cases (mock OllamaClient, tmp_path vaults)
└── scripts/                    # Smoke tests, compare scripts
```

## Vault structure (created by `synto init`)

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

## Key mechanisms

- **Incremental compilation.** Changing one note only recompiles articles derived from that note.
- **Rejection feedback loop.** Reject a draft with reasoning → reason injected into next compile prompt. Five rejections without approval auto-blocks the concept.
- **Confidence scores.** Each draft gets a score (0–1). Approve selectively or set threshold.
- **Three-state lifecycle:** `draft` → `verified` → `published`.
- **Hand-edit protection.** SHA-256 content hash on every page. Manual edits detected and never overwritten.
- **No embeddings, no vector database.** `synto query` routes questions via `INDEX.json`. Works without GPU, FAISS, or Chroma.
- **Source-type analysis.** Imported documents carry type (notes, textbook, paper, spec, api_docs, web_article, corp_docs, transcript, unknown_text). Each type gets a matched ingest prompt.
- **Multi-language.** Auto-detected at ingest. Articles written in the source language.
- **Git-aware.** Every auto-operation commits with `[synto]` prefix. `synto undo` reverts last N auto-commits.
- **LLM response cache.** Identical prompts reuse cached responses from SQLite.

## MCP server (12 tools)

**Wiki tools (8):** `list_articles`, `read_article`, `find_concept`, `search_articles`, `get_concept`, `list_sources`, `trace_lineage`, `answer_question`

**Verbatim source tools (4):** `read_source_segment`, `search_source_segments`, `get_source_passages`, `list_segments`

Source access is governed by `[mcp.source_access]` in `synto.toml` (permissive_only / all / deny).

## CLI surface

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
| `synto migrate-olw` | Migrate from obsidian-llm-wiki-local |

## Package export format

```
pack/
├── articles/           ← One Markdown file per concept
├── index/
│   └── INDEX.json      ← Machine-readable index with stable article IDs
├── agent/
│   ├── manifest.json   ← Capabilities and pack metadata
│   ├── concepts.json   ← Concept registry with aliases
│   └── sources.json    ← Source provenance
├── AGENTS.md           ← Agent-readable entrypoint
└── CLAUDE.md           ← Claude Code context file
```

## Tech stack

- Python 3.11+
- Click (CLI), Rich (terminal UI), Pydantic v2 (schemas), httpx (HTTP), SQLite (state)
- watchdog (file watcher), python-frontmatter (YAML frontmatter), PyMuPDF4LLM (PDF import)
- MCP SDK (server), tomli-w (TOML writing)
- ~20 LLM providers: Ollama, LM Studio, vLLM, Groq, Together AI, Fireworks AI, DeepInfra, OpenRouter, Mistral, DeepSeek, xAI, NVIDIA NIM, Azure OpenAI, etc.
- Testing: pytest, pytest-cov, pytest-benchmark, ruff

## Relevance to our pipeline

**Directly relevant.** Synto implements the same Karpathy LLM Wiki pattern we are building toward, but as a general-purpose CLI tool rather than a research-paper-specific pipeline. Key takeaways:

- **Two-tier model approach** — fast/cheap model for extraction, powerful model for writing. Our pipeline currently uses a single model for both passes.
- **Incremental compilation** — only recompiles affected articles. Our pipeline re-processes everything.
- **Rejection feedback loop** — human feedback injected into next compile prompt. We have no review step.
- **Hand-edit protection** — content hashing to detect manual edits. We don't track this.
- **No embeddings** — index-based routing. Our pipeline doesn't do retrieval at all yet.
- **MCP server** — exposes wiki as tools. We could add this.
- **PDF import with source types** — structured chunking with type-specific prompts. We have basic PDF extraction.
- **Confidence scoring** — each draft rated 0–1. We have trust scoring but not content confidence.
- **Pack export** — portable agent-ready directory. We don't have an export format.
