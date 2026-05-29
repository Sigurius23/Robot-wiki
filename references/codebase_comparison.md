# Codebase Comparison: Our Pipeline vs. Reference Codebases

## Overview

Our literature review pipeline adapts code from two upstream reference codebases:

- **[scholar-agent](../../references/scholar-agent/)** — an academic literature discovery & ranking engine with MCP server architecture
- **[AutoSci](../../references/AutoSci/)** — a scientific knowledge management wiki with schema definitions and templates

We kept approximately **15% of the reference code by volume** — specifically the recency/citation scoring functions, the PyMuPDF text path, and the Semantic Scholar API client with retry logic. Everything else (MCP machinery, multi-dimensional ranking, figure extraction, BM25 indexing, domain configuration, caching, wiki management) was stripped.

---

## 1. Vendor Modules — Adapted from `scholar-agent`

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

---

## 2. Pipeline Modules — Our Original Composition

| Module | Lines | Role |
|---|---|---|
| `pdf_extractor.py` | **15** | Thin re-export wrapper around `vendor/pdf_extractor.py` |
| `metadata_fetcher.py` | **167** | Wraps `vendor/search_provider.py` with title extraction from PDF text, manual override fallback, and 4 failure-mode warning paths |
| `trust_scorer.py` | **93** | Venue-tier classification (Tier 1/2/3/4) + enrichment formula using `vendor/scoring.py` |
| `llm_client.py` | **263** | Provider init (Anthropic/OpenAI), two-pass LLM pipeline (paper profile + crossref note), prompt construction, file output |
| `ingest.py` | **210** | CLI arg parsing, env loading, 9-step pipeline orchestration, error handling |

**Total**: ~745 lines of original composition code.

---

## 3. Schemas & Templates — Copied from AutoSci

| Our reference | AutoSci source | Status |
|---|---|---|
| `references/schemas/entities.yaml` | `AutoSci/runtime/schema/entities.yaml` | **Exact copy** — defines paper entities (title, authors, year, venue, abstract, citation_count, etc.) and their types/constraints |
| `references/schemas/edges.yaml` | `AutoSci/runtime/schema/edges.yaml` | **Exact copy** — defines relationship types (cites, extends, contradicts, builds_on, etc.) between papers |
| `references/templates/paper_template.md` | `AutoSci/runtime/templates/papers.md.tmpl` | **Reformatted** for our output path structure; same semantic structure |

These serve as the **spec for future prompt engineering** once the `"TODO"` placeholders in `llm_client.py` are replaced with actual prompts that generate wiki pages matching these schemas.

---

## 4. Pipeline Architecture

### Our 9-Step Flow

```
CLI args → load .env → extract_text → fetch_metadata → compute_baseline_trust_score
  → enrich metadata → init_llm_client → generate_paper_profile → generate_crossref_note
```

### Output Structure

| Pass | Output path | Content |
|---|---|---|
| Pass 1 (profile) | `wiki/papers/{cite_key}.md` | Paper metadata + LLM-generated structured profile |
| Pass 2 (crossref) | `wiki/implementation-decisions/{cite_key}-crossref.md` | LLM-generated cross-reference notes linking paper to edge types |

### How it differs from the references

| Aspect | scholar-agent | AutoSci | Our pipeline |
|---|---|---|---|
| Entry point | MCP server (JSON-RPC) | Multiple CLI tools (fetch, discover, serve, etc.) | Single CLI: `python ingest.py --pdf <path>` |
| Architecture | Agent-based with tool dispatch | Wiki management toolchain | Linear pipeline, sequential stages |
| Scoring | 4-dimension weighted ranking | — | Venue-tier heuristic + 2 vendor scores |
| LLM usage | Paper quality analysis | — | Two-pass structured generation (profile + crossref) |
| Output | MCP responses | Wiki markdown files | Wiki markdown files |
| Search | BM25 local index + S2 API | arXiv/S2 web APIs | S2 API only |

---

## 5. Summary

- **15% code retention** from references — only the essential stateless utility functions
- **Stripped**: MCP server machinery, multi-dimensional ranking, figure extraction, BM25 indexing, domain configuration, caching, wiki management tools
- **Composed new modules**: `metadata_fetcher`, `trust_scorer`, `llm_client`, `ingest` — wiring the stripped pieces into a linear 9-step pipeline with a single CLI entry point
- **Schemas & templates**: Exact copies from AutoSci, serving as the target specification for future prompt engineering
- **Tests**: 147 tests (15 property-based, full unit coverage across all modules)
