# codebuff_tasks/

Task files are intermediate JSON artifacts created when the ingest pipeline runs with
`--provider codebuff`. Instead of calling an external LLM API (Anthropic, OpenAI, or NVIDIA NIM),
the pipeline saves the full analysis context to disk. Codebuff then reads these task files and
generates the final Obsidian markdown notes.

## Workflow

```
┌──────────────┐     ┌─────────────────┐     ┌──────────┐     ┌──────────────────┐
│ python        │     │ codebuff_tasks/  │     │ Codebuff │     │ wiki/            │
│ ingest.py     │────▶│ {cite_key}--     │────▶│ (you)    │────▶│ papers/{key}.md  │
│ --provider    │     │ paper_profile    │     │          │     │ impl-decisions/  │
│ codebuff      │     │ .json            │     │          │     │ {key}-crossref.md│
└──────────────┘     └─────────────────┘     └──────────┘     └──────────────────┘
```

1. **Pipeline runs with `--provider codebuff`:** `ingest.py` performs PDF extraction
   and metadata fetching (Semantic Scholar) as usual, but instead of calling an LLM API
   for Pass 1 (paper profile) and Pass 2 (crossref note), it writes task files.

2. **Task files land in `./codebuff_tasks/`:** Each paper produces two task files
   (one for Pass 1, one for Pass 2).

3. **You ask Codebuff to process them:** Codebuff reads each task file, analyses the
   full PDF text and metadata, and writes the output markdown files to `wiki/`.

4. **Done.** The task files can be deleted or kept for audit/reprocessing.

## Creating task files

```bash
# Single paper
python ingest.py --pdf ./raw_papers/paper.pdf --provider codebuff

# Batch mode
python batch_ingest.py --provider codebuff

# With subfolder
python ingest.py --pdf ./raw_papers/paper.pdf --provider codebuff --subfolder pgg-simulation
```

## File naming

Task files use the pattern:
```
{cite_key}--{task_type}.json
```

- `cite_key`: The Obsidian cite-key, derived from the PDF filename (e.g., `2401.01735v1`)
- `task_type`: Either `paper_profile` (Pass 1) or `crossref_note` (Pass 2)

Examples:
```
codebuff_tasks/2502.17720v4--paper_profile.json
codebuff_tasks/2502.17720v4--crossref_note.json
```

## JSON format

Each task file is a JSON object with the following fields:

| Field | Type | Description |
|---|---|---|
| `cite_key` | string | Obsidian cite-key for the paper |
| `task_type` | string | `"paper_profile"` or `"crossref_note"` |
| `output_path` | string | Target path where the generated markdown should be written (relative to project root) |
| `system_prompt` | string | System instruction that would have been sent to the LLM (for reference) |
| `user_prompt` | string | The fully constructed user prompt with truncated PDF text (what the LLM would have received) |
| `metadata` | object | Paper metadata from Semantic Scholar. For Pass 1: full metadata dict. For Pass 2: `{"title": "..."}` |
| `pdf_text` | string | The **untruncated** full PDF text — Codebuff gets the whole paper, not the 30K-char truncated version sent to LLM APIs |

### Example: `paper_profile` task

```json
{
  "cite_key": "2502.17720v4",
  "task_type": "paper_profile",
  "output_path": "./wiki/papers/pgg-simulation/2502.17720v4.md",
  "system_prompt": "You are a research librarian formatting an Obsidian note...",
  "user_prompt": "You are a research librarian processing an academic paper...\n\n---\ntitle: \"Spontaneous Giving...\"\n...\n\n=== PAPER TEXT ===\n[truncated PDF text]",
  "metadata": {
    "year": 2025,
    "venue": "Conference on Empirical Methods in Natural Language Processing",
    "citationCount": 9,
    "authors": [{"authorId": "...", "name": "Yuxuan Li"}, ...],
    "title": "Spontaneous Giving and Calculated Greed in Language Models",
    "externalIds": {"DOI": "10.48550/arXiv.2502.17720", ...},
    "baseline_trust_score": 5,
    "cite_key": "2502.17720v4"
  },
  "pdf_text": "Spontaneous Giving and Calculated Greed in Language Models\nYuxuan Li\n..."
}
```

### Example: `crossref_note` task

```json
{
  "cite_key": "2502.17720v4",
  "task_type": "crossref_note",
  "output_path": "./wiki/implementation-decisions/pgg-simulation/2502.17720v4-crossref.md",
  "system_prompt": "You are a research assistant mapping a paper...",
  "user_prompt": "Paper Title: Spontaneous Giving...\n\nMap this paper against the implementation decisions...\n\n=== PAPER TEXT ===\n[truncated PDF text]",
  "metadata": {
    "title": "Spontaneous Giving and Calculated Greed in Language Models"
  },
  "pdf_text": "Spontaneous Giving and Calculated Greed..."
}
```

## How Codebuff processes task files

When you ask Codebuff to "process the codebuff task files," it:

1. Lists all `*.json` files in `./codebuff_tasks/`
2. Reads each task file to get the full PDF text, metadata, and output path
3. For `paper_profile` tasks: fills in the paper template (summary, methodology, key findings,
   limitations, prior work, project implications, APA reference) based on a thorough reading
   of the full PDF text
4. For `crossref_note` tasks: maps the paper against the 12 project implementation decisions
   (agent architecture, coordination mechanism, communication protocol, etc.) using the relationship
   types defined in `references/schemas/edges.yaml`
5. Writes the generated markdown to the specified `output_path`
6. Reports completion

## Notes

- **Full PDF text:** The `pdf_text` field contains the complete extracted text, while the
  `user_prompt` contains a truncated version (first 22K + last 8K characters). Codebuff
  reads the full `pdf_text` for comprehensive analysis.
- **Metadata caveats:** Semantic Scholar's API occasionally returns incorrect metadata
  for arXiv IDs. Always verify titles and authors in the output against the actual PDF content.
- **Idempotency:** Reprocessing a task file regenerates the output. You can safely delete
  task files after successful processing, or keep them for audit trails.
