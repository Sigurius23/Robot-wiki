# Full Ecosystem Comparison: All Codebases vs. Karpathy's Vision

## Overview

This document compares **7 codebases** (including our pipeline) against **Karpathy's original LLM Wiki gist** — the conceptual seed that inspired all of them. Each codebase implements a different subset of the vision, optimized for different use cases and scales.

---

## 1. The Full Spectrum

| | Karpathy's Gist | Scholar Agent | AutoSci | Synto | Obsidian-Wiki | Second Brain | GBrain | Our Pipeline |
|---|---|---|---|---|---|---|---|---|---|
| **Author** | Andrej Karpathy | (community) | AutoSci team | kytmanov | Ar9av | NicholasSpisak | Garry Tan (YC) | us |
| **Status** | Concept | Mature (v3.x) | Mature | Beta (v0.4.0) | Active | Active | Production (v0.42.x) | Active development |
| **Language** | — | Python 3.10+ | Python | Python 3.11+ | Markdown | Markdown | TypeScript (Bun) | Python |
| **Paradigm** | Idea file | MCP server | Agent-driven tools | Local LLM pipeline | Agent skill files | Agent skill files (minimal) | Postgres-native brain | Linear pipeline |
| **Storage** | Markdown + git | Flat files + BM25 | 9 entity partitions + JSONL graph | SQLite + Obsidian vault | Obsidian vault + manifest.json | Obsidian vault + log.md | PGLite/Postgres + pgvector | Flat markdown files |
| **LLM Model** | Any | Any (via API) | Any (via agent) | Local (Ollama 4B+14B) | External (agent's model) | External (agent's model) | Cloud + local (multiple) | Any (via API) |
| **Retrieval** | index.md + optional qmd | BM25 | File search | INDEX.json (no embeddings) | Index + optional QMD | Index.md + optional qmd | Hybrid: HNSW+BM25+RRF+reranker | None |
| **Graph** | Wikilinks only | Tags/links only | Typed JSONL edges + bidirectional xref | Wikilinks only | Wikilinks only | Wikilinks only | Typed edges + auto-extraction | None |
| **Query** | Read pages → synthesize | MCP `query_knowledge` | File search | Index-routed Q&A | Tiered retrieval | Tiered retrieval (index → qmd → wikilinks) | Synthesis + gap analysis | None |
| **Ingest** | Per-source, human-guided | API search + download | arXiv/S2 fetch + discover | PDF/MD import with source types | Agent reads any format | Agent reads files (user guided) | Webhook + capture + sync | PDF extraction |
| **Review/Human Loop** | Active involvement | None | None | Rejection feedback + confidence + review UI | Active (read/check/guide) | Explicit "discuss with user" step | doctor + quarantine + enrich review | None |
| **Delta Tracking** | Not needed (manual) | No | No | Incremental compile | .manifest.json + git log | log.md grep | Checkpoint banking (resumable) | No |
| **Multi-Agent** | N/A | No | Claude Code skills | MCP server (12 tools) | 15+ agent platforms | 40+ agents (npx skills add) | MCP (30+ tools) + OAuth | No |
| **Multi-User** | No | No | No | No | No | No | Company brain (OAuth-scoped) | No |
| **Scale** | ~100 sources | Research papers | Research lifecycle | ~200 notes | Personal knowledge | Personal knowledge | 146K+ pages (production) | ~94 papers |
| **Evals** | No | 266 tests | Linter | ~200 tests | None | Blueprint document | LongMemEval + BrainBench + replay | 147 tests |
| **Operational Maturity** | N/A | Test suite | Linter + xref rules | Test suite + git-aware | Agent-driven (ad-hoc) | Blueprint doc + 4 skills | Watchdog, OOM detection, resumable sync, 100+ migrations | Basic test suite |

---

## 2. How Each Implements Karpathy's Three Layers

### Raw Sources
| Codebase | Implementation |
|---|---|
| **Scholar Agent** | Downloads papers from arXiv, stores in `paper-notes/` |
| **AutoSci** | `raw/papers/`, `raw/notes/`, `raw/web/`, `raw/discovered/` — separate read-only dirs |
| **Synto** | `raw/` (user drops files) + `.synto/sources/` (archived originals). 9 source types with matched prompts. |
| **Obsidian-Wiki** | Any file the agent can read — Markdown, PDFs, JSONL exports, chat logs, images. Agent reads directly. |
| **Second Brain** | `raw/` directory + Obsidian Web Clipper. Agent reads files, discusses key takeaways with user before writing. |
| **GBrain** | Git repos synced into Postgres. Webhook ingestion (`POST /ingest`). `gbrain capture` for quick thoughts. |
| **Our Pipeline** | `raw_papers/` — PDF files extracted via PyMuPDF. No import tracking or source type analysis. |

### The Wiki
| Codebase | Implementation |
|---|---|
| **Scholar Agent** | Flat `knowledge/` dir with structured `.md` cards. No entity partitioning. |
| **AutoSci** | 9 entity types (`papers`, `concepts`, `topics`, `people`, `ideas`, `experiments`, `methods`, `Summary`, `foundations`). Each with YAML frontmatter schemas. |
| **Synto** | `wiki/` with `.drafts/`, `sources/`, `queries/`, `synthesis/`. One article per concept, cross-linked. |
| **Obsidian-Wiki** | 10 category dirs (`concepts/`, `entities/`, `skills/`, `references/`, `synthesis/`, `journal/`, `projects/`). Schema emerges from sources. |
| **Second Brain** | 4 category dirs (`sources/`, `entities/`, `concepts/`, `synthesis/`). Minimalist structure. Factual vs interpretive separation enforced. |
| **GBrain** | Schema packs (`gbrain-base-v2`: 15 types including `person`, `company`, `deal`, `meeting`, `concept`, `project`, etc.). User-authored packs via `gbrain schema detect`. |
| **Our Pipeline** | `wiki/papers/` (profiles) + `wiki/implementation-decisions/` (crossrefs). 7 folders by thesis topic. Tagged but no entity partitioning. |

### The Schema
| Codebase | Implementation |
|---|---|
| **Scholar Agent** | `schemas/answer.schema.json` for validation. Templates in `templates/`. |
| **AutoSci** | `runtime/schema/entities.yaml`, `edges.yaml`, `xref.yaml`, `conventions.yaml` — full declarative schema. |
| **Synto** | `synto.toml` per-vault config. Pydantic v2 models for LLM I/O. Source-type prompt templates. |
| **Obsidian-Wiki** | Each SKILL.md IS the schema for that operation. `AGENTS.md` as global convention. `_meta/taxonomy.md` for tags. |
| **Second Brain** | Each SKILL.md IS the schema. `wiki-schema.md` as canonical rules reference (single source of truth). `REQUIREMENTS.md` as reusable blueprint. |
| **GBrain** | `src/core/operations.ts` as the single source of truth. Schema packs in `skills/`. RESOLVER.md for skill dispatch. |
| **Our Pipeline** | `references/schemas/entities.yaml` and `edges.yaml` (exact copies from AutoSci, serving as future prompt spec). No runtime schema enforcement. |

---

## 3. How Each Implements Karpathy's Three Operations

### Ingest
| Codebase | Approach |
|---|---|
| **Scholar Agent** | `search_papers` → `download_paper` → `analyze_paper` → `paper_to_card`. Multi-step pipeline with scoring. |
| **AutoSci** | `discover.py` (gather/score/rank) → agent-driven ingest via Claude Code skills. |
| **Synto** | Two-tier LLM: fast model extracts concepts, heavy model writes articles. Source-type-specific prompts. Incremental compilation. |
| **Obsidian-Wiki** | Agent reads source → extracts concepts/entities/claims → merges into existing pages. Delta tracking via manifest. |
| **Second Brain** | 8-step workflow: read → discuss with user → create source summary → update entity/concept pages → add wikilinks → update index → update log → report. Delta via log.md grep. |
| **GBrain** | `gbrain sync` (git → DB) + `gbrain capture` (quick thoughts) + webhook POST. Resumable checkpoint banking. |
| **Our Pipeline** | `ingest.py`: extract text → fetch metadata → score trust → LLM profile → LLM crossref. Linear, no delta. |

### Query
| Codebase | Approach |
|---|---|
| **Scholar Agent** | BM25 `query_knowledge` → returns matching cards. |
| **AutoSci** | File search + `index.md` + `compile-context` for LLM prompt injection. |
| **Synto** | Index-based routing (INDEX.json): fast model selects pages, heavy model answers. No embeddings. |
| **Obsidian-Wiki** | Tiered retrieval: read titles/tags/summaries first, only open bodies when needed. Optional QMD semantic search. |
| **Second Brain** | Tiered: index.md → qmd (if installed) → read pages → follow wikilinks → raw sources last. Offers to save valuable answers as synthesis pages. |
| **GBrain** | Hybrid search (vector+BM25+graph+reranker) → `gbrain think` synthesizes with citations + gap analysis. |
| **Our Pipeline** | None. SUMMARY_INDEX.md is static. No query interface. |

### Lint
| Codebase | Approach |
|---|---|
| **Scholar Agent** | `close_knowledge_loop.py` validates new cards. |
| **AutoSci** | `lint.py` checks format, schemas, missing reverse links. `xref.yaml` enforces bidirectional consistency. |
| **Synto** | `synto maintain` checks broken wikilinks, orphans, stale articles. `synto eval` scores coverage/citation/link resolution. |
| **Obsidian-Wiki** | `wiki-lint` finds broken links, orphans, contradictions. `tag-taxonomy` enforces controlled vocabulary. `cross-linker` auto-discovers missing links. |
| **Second Brain** | 8 audit steps: broken wikilinks, orphans, contradictions, stale claims, missing pages, missing cross-references, index consistency, data gaps. Severity-ranked (Errors/Warnings/Info). |
| **GBrain** | `gbrain doctor` with 20+ checks (OOM loops, pool health, extraction lag, quarantine, hidden pages, link resolution opportunity). `gbrain eval suspected-contradictions`. |
| **Our Pipeline** | None. No health checks, no link validation, no contradiction detection. |

---

## 4. Unique Innovations Per Codebase

### Scholar Agent
- **4-dimension paper scoring** (fit, freshness, impact, rigor) with configurable domain keywords
- **BM25 local index** for offline knowledge retrieval
- **14 MCP tools** covering the full academic research cycle

### AutoSci
- **9 semantic entity types** with formal YAML schemas and typed bidirectional edges
- **Declarative xref rules** that automatically maintain reciprocal links
- **Lifecycle tracking** for ideas and experiments (`proposed → in_progress → validated/failed`)

### Synto
- **Two-tier model architecture** (fast 4B for analysis, heavy 14B+ for writing) — unique among all codebases
- **Rejection feedback loop** with auto-blocking after 5 rejections
- **Confidence scoring** (0–1) on every draft with threshold-based approval
- **Verbatim source MCP tools** with license-gated access control

### Obsidian-Wiki
- **Skill-based architecture** — the only codebase where the agent IS the LLM, with no runtime scripts
- **15+ agent compatibility** — single skill set works across Claude, Cursor, Windsurf, Codex, Gemini, Hermes, Pi, etc.
- **Cross-agent memory bridge** — query knowledge by which AI tool wrote it
- **Provenance tracking** — extracted / inferred / ambiguous tagging on every claim
- **Agent history ingestion** — mine your own conversations from 6+ AI platforms

### Second Brain
- **Minimalist design** — only 4 skills cover the full lifecycle, proving the pattern needs no bloat
- **Blueprint document (REQUIREMENTS.md)** — unique among all codebases: a reusable specification that anyone can implement from scratch
- **Explicit human-in-the-loop** — ingest pauses to discuss key takeaways before writing (the most explicit human review in the ecosystem)
- **Compounding queries** — every good answer offered for saving back as a synthesis page
- **Factual vs interpretive separation** — source summaries are factual only; concepts and synthesis are interpretive
- **40+ agent compatibility** — via the Agent Skills standard, no per-agent setup needed beyond `npx skills add`

### GBrain
- **Production scale** — 146K+ pages in real deployment, by far the most battle-hardened
- **Hybrid search with autocut** — vector HNSW + BM25 + RRF + cross-encoder reranker + score-discontinuity result-sizing
- **Self-wiring knowledge graph** — zero-LLM entity extraction with typed edges (attended, works_at, invested_in, etc.)
- **Synthesis with gap analysis** — tells you what the brain *doesn't* know yet
- **Operational hardening** — 100+ schema migrations, OOM detection, process watchdog, resumable sync, background work drain, connection ownership tracking
- **Company brain mode** — federated multi-user with OAuth-scoped, source-scoped access
- **Schema packs** — no fixed layout; user-authored taxonomy with 7-tier resolution chain
- **Skill self-improvement** — `gbrain skillopt` with held-out validation gate

### Our Pipeline
- **Two-pass LLM generation** (paper profile + crossref note) — writing both what the paper IS and how it RELATES to the thesis
- **Trust scoring** with venue-tier heuristics
- **Tag taxonomy** applied across 94 papers with 30 consistent tags
- **Summary indices** (SUMMARY_INDEX.md, CROSSREF_INDEX.md) for vault navigation
- **Thesis-specific focus** — all content is scoped to a single research question (LLM agent cooperation/values/bonding)

---

## 5. What We're Missing (Gap Analysis Against the Ecosystem)

| Capability | Best Reference | Status |
|---|---|---|
| **Retrieval/Query** | GBrain hybrid search | ❌ Missing — we have no way to query our 94 papers |
| **Knowledge Graph** | AutoSci typed edges + GBrain auto-extraction | ❌ Missing — flat files only |
| **Delta Tracking** | Obsidian-Wiki .manifest.json | ❌ Missing — re-processing always |
| **Human Review Loop** | Synto rejection feedback + confidence scoring | ❌ Missing — fully automated |
| **Lint/Health** | GBrain doctor + Synto maintain | ❌ Missing — no contradiction detection |
| **Synthesis** | GBrain think (cited prose + gap analysis) | ❌ Missing — crossrefs are per-paper only |
| **MCP Server** | GBrain 30+ tools | ❌ Missing — CLI only |
| **Multi-Agent Support** | Obsidian-Wiki 15+ platforms | ❌ Missing — single CLI |
| **Operational Hardening** | GBrain watchdog, resumable sync, OOM detection | ❌ Missing — basic error handling only |
| **Content Quality Gate** | GBrain junk detection + quarantine | ❌ Missing — trusts PDF text blindly |
| **Schema Enforcement** | AutoSci xref.yaml rules | ⚠️ Partial — schemas copied but not enforced |

---

## 6. What We Already Have That Others Don't

| Capability | Our Pipeline | Notes |
|---|---|---|
| **Two-pass LLM analysis** (what it IS + how it RELATES) | ✅ | Unique in the ecosystem |
| **Thesis-scoped curation** (all 94 papers serve one question) | ✅ | Other codebases are general-purpose |
| **Tag taxonomy with index pages** | ✅ | 30 consistent tags across 94 profiles |
| **Trust scoring with venue heuristics** | ✅ | Scholar Agent has richer scoring but not venue-tier |
| **Structured crossref notes** (Pass B analysis) | ✅ | Closest analog is AutoSci edges, but those are structural, not analytical |

---

## 7. Recommended Adoption Order

Based on maturity, relevance, and implementation complexity:

1. **Karpathy's Gist** — Read first. The conceptual foundation. Everything else is an implementation detail.
2. **Second Brain** — Read second. The most distilled implementation — only 4 skills, plus a reusable blueprint document (REQUIREMENTS.md) that explains how to build your own.
3. **Obsidian-Wiki** — Best reference for skill-based architecture and agent integration patterns (if Second Brain is too minimal).
4. **Synto** — Best reference for two-tier LLM pipeline design and human review loops.
5. **AutoSci** — Best reference for entity schemas and typed graph edges (already partially adopted).
6. **Scholar Agent** — Best reference for paper scoring and MCP tool design (already partially adopted).
7. **GBrain** — Best reference for production hardening, hybrid search, and operational maturity. The most to learn from, but also the most complex.

---

## Appendix A: Our Pipeline — Module-Level Provenance

*Preserved from the original codebase comparison. Documents exactly which reference code was adapted, what was stripped, and what we composed new.*

### Vendor Modules — Adapted from `scholar-agent`

| Our module | Reference original | Lines (ours / ref) | What we stripped | What we kept |
|---|---|---|---|---|
| `vendor/scoring.py` | `scholar_agent/engine/academic/scoring.py` | **93 / 215** | `PaperScorer` class (BM25 relevance, LLM quality scoring, domain keyword matching, exclusion rules, 4-dimension weighted ranking), MCP decorators, FastMCP | `recency_score()` (year-based linear decay [0,1]) and `citation_score()` (log-scaled [0,1]) |
| `vendor/pdf_extractor.py` | `scholar_agent/engine/academic/image_extractor.py` | **89 / 252** | arXiv tarball download, figure extraction (global area ranking), image classification (framework/results), `download_arxiv_pdf`, noise filtering | `extract_text()` (PyMuPDF page iteration), whitespace normalisation (3+ spaces → 1, 3+ newlines → 2), bibliography stripping (References/Bibliography/Works Cited) |
| `vendor/search_provider.py` | Semantic Scholar provider (one of many in scholar-agent) | **127** | BM25 indexing, caching, server registration, MCP decorators | DOI lookup + title search via S2 API, HTTP 429 retry/backoff (max 3, 5s wait), field extraction (year/venue/citationCount/authors) |

### Key Differences: Scoring

The reference `scoring.py` is a **class-based multi-dimensional ranking engine** (`PaperScorer`) with four dimensions:

- **Fit** — keyword matching against domain configuration
- **Freshness** — logarithmic decay over 365 days
- **Impact** — citation velocity with trending mode
- **Rigor** — weighted bag-of-words lexicon with ~70 quality signal terms (e.g., "theorem", "ablation", "proof")

Each dimension is normalised to [0, 10] and combined into a weighted recommendation score.

Our `vendor/scoring.py` extracts only the **two simplest numeric dimensions** (recency + citations), discarding the entire class architecture, keyword matching, and LLM-quality signals. Our `trust_scorer.py` then wraps these in a **venue-tier heuristic** (Nature/NeurIPS = 8, IEEE = 6, arXiv = 4).

### Key Differences: PDF Extraction

The reference `image_extractor.py` (~250 lines) focuses on **figure harvesting** — pulling images from arXiv source tarballs with global area ranking, section classification, and PDF fallback. Text extraction is a small utility (`extract_pdf_text`, ~12 lines).

Our `vendor/pdf_extractor.py` repurposes only the text path, adding **whitespace normalisation** and **bibliography stripping** not present in the reference.

### Pipeline Modules — Our Original Composition

| Module | Lines | Role |
|---|---|---|
| `pdf_extractor.py` | **15** | Thin re-export wrapper around `vendor/pdf_extractor.py` |
| `metadata_fetcher.py` | **167** | Wraps `vendor/search_provider.py` with title extraction from PDF text, manual override fallback, and 4 failure-mode warning paths |
| `trust_scorer.py` | **93** | Venue-tier classification (Tier 1/2/3/4) + enrichment formula using `vendor/scoring.py` |
| `llm_client.py` | **263** | Provider init (Anthropic/OpenAI), two-pass LLM pipeline (paper profile + crossref note), prompt construction, file output |
| `ingest.py` | **210** | CLI arg parsing, env loading, 9-step pipeline orchestration, error handling |

**Total**: ~745 lines of original composition code.

### Schemas & Templates — Copied from AutoSci

| Our reference | AutoSci source | Status |
|---|---|---|
| `references/schemas/entities.yaml` | `AutoSci/runtime/schema/entities.yaml` | **Exact copy** — defines paper entities (title, authors, year, venue, abstract, citation_count, etc.) and their types/constraints |
| `references/schemas/edges.yaml` | `AutoSci/runtime/schema/edges.yaml` | **Exact copy** — defines relationship types (cites, extends, contradicts, builds_on, etc.) between papers |
| `references/templates/paper_template.md` | `AutoSci/runtime/templates/papers.md.tmpl` | **Reformatted** for our output path structure; same semantic structure |

### Pipeline Architecture

#### Our 9-Step Flow

```
CLI args → load .env → extract_text → fetch_metadata → compute_baseline_trust_score
  → enrich metadata → init_llm_client → generate_paper_profile → generate_crossref_note
```

#### Output Structure

| Pass | Output path | Content |
|---|---|---|
| Pass 1 (profile) | `wiki/papers/{cite_key}.md` | Paper metadata + LLM-generated structured profile |
| Pass 2 (crossref) | `wiki/implementation-decisions/{cite_key}-crossref.md` | LLM-generated cross-reference notes linking paper to thesis implications |

#### How it differs from the references

| Aspect | scholar-agent | AutoSci | Our pipeline |
|---|---|---|---|
| Entry point | MCP server (JSON-RPC) | Multiple CLI tools (fetch, discover, serve, etc.) | Single CLI: `python ingest.py --pdf <path>` |
| Architecture | Agent-based with tool dispatch | Wiki management toolchain | Linear pipeline, sequential stages |
| Scoring | 4-dimension weighted ranking | — | Venue-tier heuristic + 2 vendor scores |
| LLM usage | Paper quality analysis | — | Two-pass structured generation (profile + crossref) |
| Output | MCP responses | Wiki markdown files | Wiki markdown files |
| Search | BM25 local index + S2 API | arXiv/S2 web APIs | S2 API only |

#### Summary

- **15% code retention** from references — only the essential stateless utility functions
- **Stripped**: MCP server machinery, multi-dimensional ranking, figure extraction, BM25 indexing, domain configuration, caching, wiki management tools
- **Composed new modules**: `metadata_fetcher`, `trust_scorer`, `llm_client`, `ingest` — wiring the stripped pieces into a linear 9-step pipeline with a single CLI entry point
- **Schemas & templates**: Exact copies from AutoSci, serving as the target specification for future prompt engineering
- **Tests**: 147 tests (15 property-based, full unit coverage across all modules)
