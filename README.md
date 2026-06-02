# LLM Wiki — Literature Review Pipeline

A single-command Python CLI that transforms a local academic PDF into two structured Obsidian Markdown notes. Built to support a bachelor thesis on Public Goods Games (PGG) simulated with LLM-based agents whose personalities are grounded in Schwartz Theory of Basic Human Values.

---

## Prerequisites & Installation

This pipeline requires **Python 3.10+** (utilises modern union type syntax `str | None`).

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install pinned dependencies
pip install -r requirements.txt
```

---

## Configuration

Before running the pipeline, configure your API keys in a local `.env` file. Copy the template and fill in the values:

```bash
cp .env.example .env
```

### `.env` File Structure
```dotenv
# LLM provider: "anthropic", "openai", or "nim"
LLM_PROVIDER=nim

# API keys — only the key for your chosen provider is required
NIM_API_KEY=nvapi-...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Semantic Scholar API key (optional but recommended — 1 req/s vs shared pool)
# Get one free at: https://www.semanticscholar.org/product/api
SEMANTIC_SCHOLAR_API_KEY=...

# Optional overrides
# LLM_MODEL=deepseek-ai/deepseek-v4-pro   # overrides provider default
# NIM_BASE_URL=http://0.0.0.0:8000/v1      # point at local NIM container
```

### Default Models

If you do not specify a model via `--model` or `LLM_MODEL`, the pipeline uses these defaults:

| Provider | Default model |
|---|---|
| `nim` | `deepseek-ai/deepseek-v4-pro` |
| `anthropic` | `claude-sonnet-4-20250514` |
| `openai` | `gpt-4o` |

---

## Quick Start

```bash
# 1. Drop your PDF into raw_papers/
cp your_paper.pdf raw_papers/

# 2. Run the pipeline
python ingest.py --pdf "./raw_papers/your_paper.pdf"

# Optional: override the cite-key (default: derived from filename)
python ingest.py --pdf "./raw_papers/your_paper.pdf" --cite-key smith2024

# Optional: provide DOI to skip PDF extraction of DOI
python ingest.py --pdf "./raw_papers/your_paper.pdf" --doi 10.1234/abc

# Optional: override the LLM model
python ingest.py --pdf "./raw_papers/your_paper.pdf" --model meta/llama-3.1-70b-instruct
```

**Output Files:**
- `./wiki/papers/{cite-key}.md` — structured paper profile note
- `./wiki/implementation-decisions/{cite-key}-crossref.md` — crossref against 12 thesis implementation decisions

### Example Outputs

Here is what the generated files look like for a sample paper:

<details>
<summary>📄 View Example Paper Profile (<code>wiki/papers/schwartz2024.md</code>)</summary>

```markdown
---
title: "Revision and Cross-cultural Adaptation of the Human Values Scale for Self-completion Modes"
authors: "Elena Sommer, Brita Dorer, Ulrike Efu Nkong, Tim Hanson, Sabine Zinn, Shalom H. Schwartz"
year: 2025
journal: "Survey Practice"
citation-count: 0
url: "https://doi.org/10.29115/sp-2025-0017"
tags: [literature, unprocessed]
cite-key: "schwartz2024"
---
# Revision and Cross-cultural Adaptation of the Human Values Scale for Self-completion Modes
source: https://doi.org/10.29115/sp-2025-0017
thesis-relevance: Details the development and cross-cultural validation of the revised 20-item Human Values Scale, providing the validated instrument and methodology essential for operationalising agents' Schwartz values in a simulated PGG.

## Summary
This paper documents the revision and adaptation of the Human Values Scale (HVS) for the European Social Survey’s transition to self-completion modes. It introduces a shortened, gender-neutral, 20-item scale designed to measure the refined theory of 19 basic human values. Through a multilingual translation process (TRAPD) and a cognitive pretest with participants of diverse migration backgrounds, the study refined the scale for cross-cultural comparability, leading to its adoption in ESS Round 12 and the German SOEP.

## Methodology
- **Study type**: Survey methodology / questionnaire development and validation
- **Participants or agents**: Human
- **N**: 21 participants in the cognitive interview pretest; translation teams across multiple ESS countries
- **Game or task**: Not applicable
- **Key manipulations**: Revision of the HVS (gender-neutral wording, single-statement items), cross-cultural cognitive pretesting, and multilingual advance translation
- **Outcome measures**: Qualitative assessment of item comprehension and cross-cultural applicability; identification of translation and interpretation challenges
- **Pre-registered**: No

## Key findings
- The new HVS items were generally well understood by diverse participants, including those with migration and refugee backgrounds (Sommer et al., 2025, p. 6).
- The transition to gender-neutral language posed significant translation challenges, as grammatical gender-neutral plurals equivalent to "they" are absent in many languages (Sommer et al., 2025, p. 5).
- Cognitive pretesting with Ukrainian refugees revealed temporal and situational ambiguity; participants were uncertain whether to refer to their pre- or post-displacement selves, leading to the addition of "now" in the scale’s introductory text (Sommer et al., 2025, p. 6).

## Limitations acknowledged by the authors
- Measurement invariance
- Time-series comparability
- Cross-population applicability (awaiting further data)
- Limitations of gender-neutral translation in some languages

## What this paper builds on
- [[schwartz2012]] — (Schwartz et al., 2012) — The refined theory of 19 basic human values that the new 20-item scale is designed to measure.
- [[schwartz2022]] — (Schwartz and Cieciuch, 2022) — Prior item formulations from which the first version of the new scale was developed.
- [[dorertrapd2022]] — (Dorer, 2022) — The TRAPD translation methodology implemented to ensure high-quality, comparable survey translations.
- [[harkness2010]] — (Harkness et al., 2010) — The "ask-the-same-question" approach that guides the translation process for cross-national comparability.

## What this paper leaves open
The measurement invariance of the new HVS across different linguistic and cultural groups, including whether its psychometric properties hold for populations with migration or refugee backgrounds, remains unverified until data from ESS Round 12 and SOEP are analyzed.

## Thesis implications
The validated 20-item scale and its gender-neutral, single-statement format provide a directly implementable, state-of-the-art instrument for grounding LLM agents' values in a simulated PGG. The documented translation and cross-cultural adaptation challenges indicate that value operationalisations must be carefully contextualised, with special attention to temporal framing (e.g., "now") for agent personas.

## Contradictions with other papers
No contradictions identified yet.

## APA 7th edition reference
Sommer, E., Dorer, B., Efu Nkong, U., Hanson, T., Zinn, S., & Schwartz, S. H. (2025). Revision and cross-cultural adaptation of the Human Values Scale for self-completion modes. *Survey Practice, 18*. https://doi.org/10.29115/SP-2025-0017
```

</details>

<details>
<summary>🔗 View Example Cross-Reference Analysis (<code>wiki/implementation-decisions/schwartz2024-crossref.md</code>)</summary>

```markdown
### 1. Persona injection — single-value trait description
- covered: no
- finding: The paper describes the Human Values Scale, which measures a comprehensive set of basic human values, not a single-value trait description (Sommer et al., 2025, pp. 1–2).
- alignment: not covered

### 2. Bonding protocol — text summary injection
- covered: no
- finding: The paper focuses on survey methodology for cross-cultural value measurement and does not mention any text summary injection protocol (Sommer et al., 2025).
- alignment: not covered

... [Entries 3 to 11 omitted for brevity] ...

### 12. Temperature — fixed at 0.7
- covered: no
- finding: The paper does not mention any temperature parameter setting (Sommer et al., 2025).
- alignment: not covered

---
SUPPORTS: []
CONTRADICTS: []
SILENT ON: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
```

</details>

---

## Pipeline — Step by Step

The diagram below outlines the flow of data and decision-making within the pipeline:

```mermaid
flowchart TD
    PDF[Input PDF File] --> Stage2[Stage 2: Text Extraction]
    Stage2 -->|Cleaned Text| Stage3{Stage 3: Metadata Fetch}
    
    Stage3 -->|Strategy 1| S1[CLI --doi]
    Stage3 -->|Strategy 2| S2[Extract DOI from PDF]
    Stage3 -->|Strategy 3| S3[Title-based Search]
    Stage3 -->|Strategy 4| S4[Local Fallback: PDF text only]
    
    S1 & S2 & S3 -->|Semantic Scholar API| Score[Stage 4: Trust Scorer]
    S4 -->|Minimal Metadata| Score
    
    Score -->|Enriched Metadata| LLM[LLM Generation]
    LLM -->|Pass 1| P1[wiki/papers/{cite_key}.md]
    LLM -->|Pass 2| P2[wiki/implementation-decisions/{cite_key}-crossref.md]
```

### Stage 1: CLI Argument Parsing (`ingest.py`)

1. Parse `--pdf`, `--doi`, `--cite-key`, `--model` from the command line.
2. Validate: file must exist, must have `.pdf` extension (case-insensitive).
3. If `--doi` provided, validate it matches `^10\..+` (standard DOI format). Exit with error if invalid.
4. If `--cite-key` not provided, derive it automatically from the PDF filename:
   - Take the filename stem (without extension)
   - Lowercase everything
   - Replace spaces and underscores with hyphens
   - Strip leading/trailing hyphens
   - Example: `Smith_2024 paper.pdf` → `smith-2024-paper`
5. Load `.env` via `python-dotenv`. Validate `LLM_PROVIDER` and the corresponding API key (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `NIM_API_KEY`). Exit with a named error if missing.

---

### Stage 2: PDF Text Extraction (`pdf_extractor.py` → `vendor/pdf_extractor.py`)

6. Open the PDF with **PyMuPDF** (`fitz.open(pdf_path)`). Re-raise any fitz exception as `RuntimeError` with the file path in the message.
7. Iterate over all pages and concatenate `page.get_text()` output.
8. **Whitespace normalisation** (two regex passes):
   - `re.sub(r'[^\S\n]{3,}', ' ', text)` — collapse 3+ consecutive non-newline whitespace to a single space
   - `re.sub(r'\n{3,}', '\n\n', text)` — collapse 3+ consecutive blank lines to one blank line
9. **Bibliography stripping**: scan lines for a heading matching `r'^\s*(References|Bibliography|Works Cited)\s*$'` (case-insensitive). On first match, truncate all text from that line to the end of the document. If no match, return the full cleaned text.
10. Print: `✓  Extracted {N} characters`

---

### Stage 3: Metadata Retrieval (`metadata_fetcher.py` → `vendor/search_provider.py`)

The pipeline tries four strategies in order, stopping at the first success:

**Strategy 1 — CLI DOI lookup**
- If the user passed `--doi`, send:
  ```
  GET https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}
      ?fields=year,venue,citationCount,authors,title,abstract,externalIds
      x-api-key: {SEMANTIC_SCHOLAR_API_KEY}
  ```
- On HTTP 429: retry up to 3 times with escalating waits (60s, 120s, 180s).
- On HTTP 4xx/5xx (non-429): print warning, move to next strategy.
- On success: return metadata dict. **Stop here.**

**Strategy 2 — DOI extracted from PDF text**
- Scan the first 3000 characters and last 1000 characters of the PDF text for DOI patterns:
  - `https://doi.org/10.xxxx/xxxx` or `http://doi.org/10.xxxx/xxxx`
  - bare `10.xxxx/xxxx` pattern
- Strip trailing punctuation (`.`, `,`, `;`, `)`) from the match.
- Print: `→  Found DOI in PDF text: {doi}`
- Send the same `GET .../paper/DOI:{doi}?fields=...` request as Strategy 1.
- On success: print `✓  DOI lookup succeeded`, return metadata dict. **Stop here.**

**Strategy 3 — Title-based search**
- Extract the first plausible title line from the PDF text:
  - Skip lines ≤10 characters
  - Skip all-caps lines with ≤4 words (journal headers like "ARTICLES")
  - Skip lines starting with `http://` or `https://`
  - Skip bare DOIs (starts with `10.`, single word)
  - Return the first line that passes all filters
- Build a query list (tried in order):
  1. Full extracted title
  2. First 6 words of title
  3. First 4 words of title
  4. First 8 words of the first long line (>20 chars) in the PDF body
- For each query, send:
  ```
  GET https://api.semanticscholar.org/graph/v1/paper/search
      ?query={query}&fields=year,venue,citationCount,authors,title,abstract,externalIds&limit=1
      x-api-key: {SEMANTIC_SCHOLAR_API_KEY}
  ```
- Pre-request delay: 1.0s if API key present, 3.0s if unauthenticated.
- On success with results: return metadata dict. **Stop here.**
- On no results: print warning, try next query.

**Strategy 4 — PDF text fallback (no API)**
- Extract year: first 4-digit number in range 1950–2029 found in the first 2000 chars of the PDF.
- Use the extracted title from Strategy 3's title extraction.
- Return a minimal metadata dict with `venue=None`, `citationCount=None`, `authors=[]`.
- Print: `Warning: All Semantic Scholar queries failed. Extracting metadata from PDF text.`

**Metadata dict returned:**
```python
{
    "year":          int | None,
    "venue":         str | None,
    "citationCount": int | None,
    "authors":       list[{"name": str}],
    "title":         str | None,
    "externalIds":   {"DOI": str, ...} | {},
}
```

Print: `✓  Metadata: year={year}, venue={venue}, citations={N}, authors={N}`

---

### Stage 4: Trust Score Calculation (`trust_scorer.py` → `vendor/scoring.py`)

11. Classify the venue string into a tier using case-insensitive substring matching (checked in priority order):
    - **Tier 1–2** (score 8): `nature`, `neurips`, `icml`, `pnas`
    - **Tier 3** (score 6): `ieee`, `springer`, `elsevier`
    - **Tier 4** (score 4): `arxiv`, `ssrn`
    - **Default** (score 4): `None`, empty, or unmatched
12. Enrich with recency and citation-count signals from `vendor/scoring.py`.
13. Clamp final score to `[1, 10]`.
14. Add `baseline_trust_score` to the metadata dict.
15. Print: `✓  Baseline trust score: {N}/10`

---

### Stage 5: Metadata enrichment (`ingest.py`)

16. Add `cite_key` to the metadata dict.
17. Add `title`: prefer the title returned by the S2 API; fall back to the PDF-extracted title if S2 didn't return one.

---

### Stage 6: LLM Pass 1 — Paper Profile (`llm_client.py`)

18. Construct the Pass 1 prompt by injecting metadata into `PROMPT_A_TEMPLATE`:
    - Fill YAML frontmatter fields: `title`, `authors`, `year`, `journal`, `citation-count`, `url` (built from `externalIds.DOI`), `cite-key`
    - Append the full cleaned PDF text after `=== PAPER TEXT ===`
19. Send to the configured LLM provider:
    - **Anthropic**: `client.messages.create(model=..., system=SYSTEM_PROMPT_A, messages=[...])`
    - **OpenAI / NIM**: streaming `client.chat.completions.create(model=..., stream=True, ...)` — chunks collected as they arrive, token count printed live (`✍  N tokens received ...`)
20. On API exception: print error with cite-key, skip file write.
21. On empty/whitespace response: print warning with cite-key, skip file write.
22. On success: write response to `./wiki/papers/{cite_key}.md` (UTF-8). Create parent directory if needed. Print overwrite warning if file already exists.
23. Print: `✓  Paper profile written → ./wiki/papers/{cite_key}.md`

**System prompt (Pass 1):**
> "You are a research librarian formatting an Obsidian note for an academic vault. Output valid Obsidian markdown only — no code fences, no preamble, no explanation. Start directly with the YAML frontmatter block (---). Use only the metadata values provided — do not hallucinate citation counts, venues, or authors."

---

### Stage 7: LLM Pass 2 — Implementation Decision Crossref (`llm_client.py`)

24. Construct the Pass 2 prompt by injecting `cite_key` into `PROMPT_B_TEMPLATE`, which contains all 12 thesis implementation decisions with the exact format:
    ```
    ### N. {Decision name}
    - covered: yes / partially / no
    - finding: [one-sentence paraphrase + citation]
    - alignment: aligned / contradicts / extends / not covered
    ```
25. Append the full cleaned PDF text after `=== PAPER TEXT ===`.
26. Send to LLM using the same streaming approach as Pass 1.
27. On success: write to `./wiki/implementation-decisions/{cite_key}-crossref.md` (UTF-8).
28. Print: `✓  Crossref note written  → ./wiki/implementation-decisions/{cite_key}-crossref.md`

**System prompt (Pass 2):**
> "You are a research assistant mapping a paper against specific thesis implementation decisions. Answer only what the paper explicitly states. Do not infer or generalise. Output the crossref note directly — no preamble, no explanation."

---

## Project Structure

```
project_root/
├── ingest.py                  # CLI entry point and pipeline orchestrator
├── pdf_extractor.py           # Thin wrapper over vendor/pdf_extractor.py
├── metadata_fetcher.py        # S2 metadata retrieval + DOI/title/fallback logic
├── trust_scorer.py            # Venue-tier heuristic + scoring enrichment
├── llm_client.py              # LLM provider abstraction, prompt construction, file writing
├── vendor/
│   ├── pdf_extractor.py       # PyMuPDF extraction + whitespace/bibliography cleaning
│   ├── search_provider.py     # Semantic Scholar API client with retry logic
│   └── scoring.py             # Recency and citation-count scoring functions
├── references/
│   ├── schemas/
│   │   ├── entities.yaml      # Obsidian `papers` entity frontmatter schema
│   │   └── edges.yaml         # Cross-reference edge type vocabulary
│   └── templates/
│       └── paper_template.md  # Paper profile section skeleton
├── raw_papers/                # Input PDFs (drop files here)
├── wiki/
│   ├── papers/                # Output: paper profile notes
│   └── implementation-decisions/  # Output: crossref notes
├── tests/                     # Property-based and unit tests
├── .env                       # Your API keys (not committed)
├── .env.example               # Template
└── requirements.txt           # Pinned dependencies
```

### Code Architecture & Vendoring Pattern

This project uses a clean architectural separation between CLI/Orchestration wrappers and standalone logical engines:
- **Root-level scripts** (`ingest.py`, `pdf_extractor.py`, `metadata_fetcher.py`, `trust_scorer.py`, `llm_client.py`) parse CLI arguments, construct user-facing logs, manage state, and orchestrate the pipeline stages.
- **Vendored engines** (`vendor/`) represent the underlying pure functional logic (e.g. interacting with the Semantic Scholar API, parsing document text, or scoring algorithms). This guarantees that external integration libraries are self-contained and easily testable in isolation.

---

## The 12 Thesis Implementation Decisions

The cross-reference note maps every paper against these decisions:

1. **Persona injection** — single-value trait description
2. **Bonding protocol** — text summary injection
3. **Stake operationalisation** — explicit elimination thresholds
4. **Contribution elicitation** — structured JSON with motivation field
5. **Memory architecture** — single preceding round only
6. **Gossip & ostracism mechanics**
7. **Agent evolution** — wealth-based cloning
8. **Round structure** — simultaneous vs. sequential play
9. **API failure handling** — default to zero contribution
10. **Model selection** — reasoning vs. standard models
11. **Measurement** — LLM self-report scales (trust, IOS)
12. **Temperature** — fixed at 0.7

---

## Error Handling

| Stage | Error | Behaviour |
|---|---|---|
| CLI | `--pdf` not provided | Exit 1, print usage |
| CLI | PDF file not found | Exit 1, print path + "not found" |
| CLI | File not `.pdf` | Exit 1, print "not a PDF" |
| CLI | Invalid DOI format | Exit 1, print "DOI format is invalid" |
| Config | Missing API key | Exit 1, print missing variable name |
| PDF extraction | PyMuPDF exception | Re-raise as `RuntimeError` with file path |
| Metadata | S2 HTTP 429 | Retry 3× with escalating waits (60s/120s/180s) |
| Metadata | S2 HTTP 4xx/5xx | Print warning, try next strategy |
| Metadata | No results found | Try next query / strategy |
| Metadata | All strategies fail | Extract year+title from PDF text, continue |
| LLM Pass 1/2 | API exception | Print error with cite-key, skip file write |
| LLM Pass 1/2 | Empty response | Print warning with cite-key, skip file write |
| File write | File already exists | Print overwrite warning, overwrite |
| File write | OSError | Print path + error, skip file, continue |

---

## Running Tests

```bash
pytest tests/ -v
```

All 147 tests cover the full pipeline with property-based tests (Hypothesis) for each correctness property and unit tests for every error path.
