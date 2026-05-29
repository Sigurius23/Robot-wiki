# LLM Wiki -- Academic Literature Review Pipeline

A CLI pipeline that ingests an academic PDF and produces two structured
Obsidian Markdown notes: a paper profile and an implementation-decision
cross-reference. The pipeline extracts text from the PDF, fetches metadata
from the Semantic Scholar API, computes a baseline trust score, and runs a
two-pass LLM generation (Anthropic Claude or OpenAI GPT-4o).

## Architecture

The pipeline is a linear sequence of nine stages orchestrated by a single
entry point (`ingest.py`). Each stage delegates to a dedicated module:

```
                    +------------------+
                    |   ingest.py      |  CLI args, env, orchestration
                    +--------+---------+
                             |
        +--------------------+--------------------+
        |                    |                    |
+-------v--------+  +--------v-------+  +---------v---------+
| pdf_extractor  |  | metadata       |  | trust_scorer      |
| (PyMuPDF)      |  | fetcher (S2)   |  | (venue-tier)      |
+----------------+  +----------------+  +-------------------+
        |                    |                    |
        +--------------------+--------------------+
                             |
                    +--------v---------+
                    | llm_client.py    |  Anthropic / OpenAI
                    | Pass 1: profile  |
                    | Pass 2: crossref |
                    +------------------+
```

### The Nine Stages

1. **Parse CLI arguments** -- validate `--pdf` path, optional `--doi` and `--cite-key`
2. **Load `.env`** -- read `LLM_PROVIDER` and the corresponding API key (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`)
3. **Extract text** -- PyMuPDF extraction with whitespace normalisation and bibliography stripping
4. **Fetch metadata** -- Semantic Scholar API lookup by DOI (preferred) or title search; falls back to manual stdin entry on failure
5. **Compute trust score** -- venue-tier classification (Nature/NeurIPS = 8, IEEE = 6, arXiv = 4) enriched with recency and citation signals; clamped to [1, 10]
6. **Enrich metadata** -- attach trust score, cite-key, and extracted title to the metadata dict
7. **Initialise LLM client** -- Anthropic or OpenAI SDK, validated against the `.env` provider
8. **Pass 1 -- Paper profile** -- LLM generates a structured Obsidian note with YAML frontmatter conforming to the `papers` entity schema and body sections (Problem & Context, Key Idea, Method, etc.)
9. **Pass 2 -- Crossref note** -- LLM maps the paper against 12 thesis implementation decisions using the edge type vocabulary from `edges.yaml` (supports, contradicts, builds_on, challenges, addresses_gap, no_coverage)

## Installation

```bash
# Clone the repository
git clone https://github.com/Sigurius23/LLM_Wiki.git
cd LLM_Wiki

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```bash
# Choose your provider
LLM_PROVIDER=anthropic     # or openai

# Set the corresponding API key
ANTHROPIC_API_KEY=sk-ant-...
# or
OPENAI_API_KEY=sk-...
```

## Usage

```bash
python ingest.py --pdf ./raw/smith2024.pdf
```

With an optional DOI (improves metadata accuracy):

```bash
python ingest.py --pdf ./raw/smith2024.pdf --doi 10.1234/example
```

With a custom cite-key:

```bash
python ingest.py --pdf ./raw/smith2024.pdf --cite-key smith-neurips-2024
```

### Output

Two files are produced relative to the project root:

```
wiki/
  papers/
    <cite-key>.md                          # Paper profile (Pass 1)
  implementation-decisions/
    <cite-key>-crossref.md                 # Crossref note (Pass 2)
```

The cite-key is derived from the PDF filename by default: `Smith_2024 paper.pdf`
becomes `smith-2024-paper`.

### Manual metadata entry

If the Semantic Scholar API returns no results (or is unreachable), the pipeline
falls back to an interactive stdin prompt asking for year, venue, citation count,
and authors. Each field can be skipped by pressing Enter.

## Module Overview

### `ingest.py` -- CLI Orchestrator

Entry point that parses arguments, loads the environment, and runs the nine-stage
pipeline sequentially. Handles all error paths (missing PDF, invalid DOI, missing
API keys, extraction failures).

### `pdf_extractor.py` -- PDF Text Extraction

Thin wrapper over `vendor/pdf_extractor.py`. Exposes `extract_text(pdf_path)`
which returns cleaned text (whitespace normalised, bibliography stripped).

### `metadata_fetcher.py` -- Semantic Scholar Metadata

Wraps `vendor/search_provider.py` and provides `fetch_metadata(doi, pdf_text)`.
Attempts DOI lookup first, falls back to title-based search, and finally prompts
for manual entry. Returns `{year, venue, citationCount, authors}`.

### `trust_scorer.py` -- Baseline Trust Score

Classifies venues into four tiers (Nature/NeurIPS/ICML/PNAS = tier 1-2, IEEE/Springer/Elsevier
= tier 3, arXiv/SSRN = tier 4) and enriches with recency and citation signals from
`vendor/scoring.py`. Returns an integer in [1, 10].

### `llm_client.py` -- LLM Provider and Note Generation

- Initialises Anthropic (`claude-sonnet-4-20250514`) or OpenAI (`gpt-4o`) clients
- Constructs prompts from module-level templates referencing `entities.yaml` and `edges.yaml`
- Pass 1 (`generate_paper_profile`): produces `wiki/papers/{key}.md`
- Pass 2 (`generate_crossref_note`): produces `wiki/implementation-decisions/{key}-crossref.md`

### `vendor/` -- Adapted Reference Code

Stripped-down modules adapted from [scholar-agent](https://github.com/sigurius23/scholar-agent):

| Module | Origin | Purpose |
|---|---|---|
| `vendor/scoring.py` | Academic scoring engine | `recency_score()` and `citation_score()` only |
| `vendor/pdf_extractor.py` | Figure harvester | `extract_text()` via PyMuPDF only |
| `vendor/search_provider.py` | Semantic Scholar provider | DOI lookup + title search with 429 retry |

For a detailed comparison, see `references/codebase_comparison.md`.

## Schema References

The pipeline output targets the wiki schemas defined in the `references/`
directory, which are preserved from the [AutoSci](https://github.com/sigurius23/AutoSci) project:

- `references/schemas/entities.yaml` -- entity type definitions (papers, concepts, topics, people, ideas, methods, experiments)
- `references/schemas/edges.yaml` -- graph edge types (cites, builds_on, challenges, supports, contradicts, addresses_gap, etc.)
- `references/templates/paper_template.md` -- section skeleton for paper notes (Problem & Context, Key Idea, Method, etc.)

## Testing

```bash
# Run the full test suite (147 tests)
python -m pytest tests/ -v

# Run tests for a specific module
python -m pytest tests/test_llm_client.py -v
python -m pytest tests/test_ingest.py -v
python -m pytest tests/test_trust_scorer.py -v
```

The test suite includes property-based tests (Hypothesis) covering all 15
specified properties across the pipeline, plus unit tests with mocked SDK
clients and API responses.

## Dependencies

- **PyMuPDF** -- PDF text extraction
- **requests** -- Semantic Scholar API calls
- **anthropic** -- Claude LLM client (optional, provider-dependent)
- **openai** -- GPT-4o LLM client (optional, provider-dependent)
- **python-dotenv** -- `.env` file loading
- **hypothesis** -- property-based testing
- **pytest** -- test framework
- **pyyaml** -- YAML schema parsing in tests

## Reference Codebases

This project adapts code from two upstream repositories:

- [scholar-agent](https://github.com/sigurius23/scholar-agent) -- academic literature discovery and ranking engine (MCP server architecture)
- [AutoSci](https://github.com/sigurius23/AutoSci) -- scientific knowledge management wiki (schema definitions, templates, and toolchain)

Both are included as git sub-references in `references/`.
