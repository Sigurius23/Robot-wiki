# Second Brain: Architectural and Technical Summary

## Overview
**Second Brain** is a skill-based implementation of the Karpathy LLM Wiki pattern — a collection of **4 focused Markdown skill files** that any AI coding agent can read and execute to build and maintain an Obsidian knowledge base. By [NicholasSpisak](https://github.com/NicholasSpisak). Open source.

**Core insight:** Simplicity over feature sprawl. Four operations cover the full lifecycle (setup, ingest, query, lint), each in a single well-documented SKILL.md file. Install via `npx skills add NicholasSpisak/second-brain` — works with 40+ agents.

**Tagline:** "The LLM is the librarian. You're the curator."

## How it works

```
raw/ (inbox) → /second-brain-ingest → wiki/ (compiled knowledge) → /second-brain-query → answers
                     ↑                                                        |
                     |                    /second-brain-lint ←────────────────┘
                     |                    (health-check)
```

## Directory structure

```
second-brain-main/
├── README.md                           # User-facing docs (install, quickstart, FAQ)
├── .gitignore
├── skills/
│   ├── second-brain/SKILL.md           # Onboarding wizard (5-step interactive setup)
│   ├── second-brain-ingest/SKILL.md    # Source processing → wiki pages
│   ├── second-brain-query/SKILL.md     # Question answering against wiki
│   └── second-brain-lint/SKILL.md      # Health-check (8 audit steps)
├── docs/
│   ├── REQUIREMENTS.md                 # Blueprint & origin story (the founding document)
│   ├── llm-wiki.md                     # Local copy of Karpathy's original gist
│   └── assets/                         # Screenshots for README
└── tests/                              # Test directory
```

## Vault structure (created by onboarding wizard)

```
your-vault/
├── raw/                    # Your inbox — drop sources here (never modified by LLM)
│   └── assets/             # Images and attachments
├── wiki/                   # LLM-maintained wiki
│   ├── sources/            # One summary per ingested source
│   ├── entities/           # People, orgs, products, tools
│   ├── concepts/           # Ideas, frameworks, theories
│   ├── synthesis/          # Comparisons, analyses, themes
│   ├── index.md            # Master catalog of all pages (one-line summaries)
│   └── log.md              # Chronological operation record (parseable with grep)
├── output/                 # Reports and generated artifacts
└── CLAUDE.md               # Agent config (varies by agent)
```

## Four skills

### 1. `/second-brain` — Onboarding Wizard
- 5-step interactive setup: vault name, location, domain/topic, agent config, optional CLI tools
- Auto-detects running agent and generates the correct config file (CLAUDE.md, AGENTS.md, GEMINI.md, .cursor/rules/)
- Generates 5-8 domain-specific tags based on user's described topic
- Offers to install 3 optional CLI tools: `summarize`, `qmd`, `agent-browser`
- Idempotent — safe to re-run

### 2. `/second-brain-ingest` — Source Processing
- 8-step workflow per source: read → discuss with user → create source summary → update entity/concept pages → add wikilinks → update index → update log → report results
- Delta detection: checks `wiki/log.md` for previously ingested filenames, only processes new ones
- A single source typically touches **10-15 wiki pages**
- Key principle: **prefer updating existing pages over creating new ones**
- When new info contradicts existing: update AND note the contradiction with both sources cited

### 3. `/second-brain-query` — Question Answering
- Search strategy: read `wiki/index.md` first → use `qmd` if available → read relevant pages → follow `[[wikilinks]]` → check raw sources as last resort
- Format output to match the question (factual, comparison, exploration, list)
- Always cite with `[[wikilinks]]`
- **Key principle: offer to save valuable answers** — comparisons, analyses, new connections → `wiki/synthesis/`

### 4. `/second-brain-lint` — Health Check
- **8 audit steps**: broken wikilinks, orphan pages, contradictions, stale claims, missing pages, missing cross-references, index consistency, data gaps
- Reports by severity: **Errors** (must fix), **Warnings** (should fix), **Info** (nice to fix)
- Each finding includes: what, where, fix
- Suggests linting after every 10 ingests or monthly
- Logs the lint pass to `wiki/log.md`

## Key design decisions

- **Agent-agnostic by design.** The same wiki conventions work in any agent's config file. Switch agents without rebuilding.
- **Human-in-the-loop by default.** The ingest skill explicitly asks the user about key takeaways before writing anything. "Discuss key takeaways with the user" is step 2 of 8.
- **Factual vs interpretive separation.** Source summary pages are factual only. Interpretation and synthesis go in concept and synthesis pages.
- **Index-driven retrieval.** `wiki/index.md` with one-line summaries per page. `qmd` as optional upgrade for larger wikis.
- **Compounding queries.** Good answers get saved back as synthesis pages — knowledge compounds from questions as well as sources.

## Agent compatibility

Works with **40+ agents** via the [Agent Skills standard](https://agentskills.io). The onboarding wizard auto-detects and generates the correct config:

| Agent | Config file | Slash commands |
|---|---|---|
| Claude Code | `CLAUDE.md` | `/second-brain`, `/second-brain-ingest`, etc. |
| Codex | `AGENTS.md` | Same |
| Cursor | `.cursor/rules/second-brain.mdc` | Same |
| Gemini CLI | `GEMINI.md` | Same |

## Recommended optional tools

| Tool | Purpose | Install |
|---|---|---|
| **summarize** | CLI media summarization | `npm i -g @steipete/summarize` |
| **qmd** | Local hybrid search (BM25 + vector) | `npm i -g @tobilu/qmd` |
| **agent-browser** | Browser automation for web research | `npm i -g agent-browser && agent-browser install` |

## Blueprint document (REQUIREMENTS.md)

The `docs/REQUIREMENTS.md` is a notable artifact — it's both a founding document and a reusable blueprint for anyone who wants to build their own implementation from scratch. Key sections:

- **ORIGIN** — links to Karpathy's tweet and gist, establishes lineage
- **THE PATTERN** — three folders (raw/, wiki/, output/), the agent config as the brain
- **WHAT YOU NEED** — Obsidian, an AI coding agent, the Web Clipper
- **FOUR OPERATIONS** — onboarding, ingest, query, lint — each described at the requirement level
- **THE AGENT CONFIG FILE** — architecture, page format, operations, 10 rules
- **MULTI-AGENT SUPPORT** — the pattern is agent-agnostic; switch without rebuilding
- **OPTIONAL TOOLS** — summarize, qmd, agent-browser
- **HOW IT ALL FITS TOGETHER** — concept-to-implementation mapping table

## Comparison to obsidian-wiki

| Aspect | obsidian-wiki | second-brain |
|---|---|---|
| **Skills** | ~30 | 4 |
| **Install method** | pip + bash setup.sh + npx | npx skills add only |
| **Agent platforms** | 15+ | 40+ |
| **Vault categories** | 10 (concepts, entities, skills, references, synthesis, journal, projects, etc.) | 4 (sources, entities, concepts, synthesis) |
| **Delta tracking** | `.manifest.json` with timestamps | `wiki/log.md` grep-based detection |
| **Provenance tracking** | extracted / inferred / ambiguous tags | Not tracked |
| **Agent history ingest** | 6+ agents (Claude, Codex, Hermes, Pi, etc.) | None |
| **Graph export** | JSON, GraphML, Neo4j, HTML | None |
| **Blueprint doc** | Not present | REQUIREMENTS.md (detailed blueprint) |
| **Human review** | Active involvement | Explicit "discuss with user" step in ingest |
| **Complexity** | Feature-rich, ~30 skills | Minimal, 4 skills |

## Relevance to our pipeline

**Directly relevant — the most distilled implementation.** Second Brain strips the Karpathy pattern to its essence: 4 operations, 4 skills, no bloat. Key takeaways:

- **The REQUIREMENTS.md blueprint pattern.** A single document that serves as both origin story and reusable specification. We could adopt this for our pipeline — a `PIPELINE_BLUEPRINT.md` that explains the architecture, operations, and rules.
- **Human-in-the-loop as a design principle.** The ingest skill explicitly pauses to discuss with the user before writing. Our pipeline is fully automated — adding a review step (like Synto's rejection feedback) would improve quality.
- **Index-driven retrieval with incremental upgrade.** Start with `wiki/index.md` (like our SUMMARY_INDEX.md), add `qmd` when the wiki grows. Our pipeline has the index but no query interface to use it.
- **Factual vs interpretive separation.** Source summaries are factual; concept/synthesis pages are interpretive. Our Pass A (profile) is factual but Pass B (crossref) is interpretive — we already have this separation.
- **Contradiction detection in lint.** The lint skill actively looks for conflicting claims between pages. We have 94 papers across 7 folders — contradictions between them are undetected.
- **Compounding queries.** "Offer to save valuable answers" is a simple but powerful pattern. Our pipeline has no query capability yet, but when we add it, this principle should be adopted.
