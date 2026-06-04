# Karpathy's LLM Wiki: The Foundational Gist

## Overview
This is **Andrej Karpathy's original gist** ([442a6bf](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)) that inspired the entire LLM Wiki ecosystem — AutoSci, Synto, obsidian-wiki, our own pipeline, and indirectly GBrain. It's a conceptual document, not an implementation — "designed to be copy pasted to your own LLM Agent."

## The core idea

"Instead of just retrieving from raw documents at query time, the LLM **incrementally builds and maintains a persistent wiki** — a structured, interlinked collection of markdown files that sits between you and the raw sources."

This is the key difference from RAG: **the wiki is a persistent, compounding artifact.** Knowledge is compiled once and kept current, not re-derived on every query.

## Three-layer architecture

```
Raw sources → The wiki → The schema
(immutable)    (LLM-maintained)   (conventions doc)
```

**Raw sources** — curated, immutable source documents. The LLM reads from them but never modifies them.

**The wiki** — LLM-generated markdown files. Summaries, entity pages, concept pages, comparisons, synthesis. The LLM owns this layer entirely.

**The schema** — a document (CLAUDE.md / AGENTS.md) that tells the LLM how the wiki is structured, what the conventions are, and what workflows to follow. Co-evolved over time.

## Three operations

1. **Ingest** — Read new source → discuss key takeaways → write summary page → update index → update relevant entity/concept pages across the wiki → append to log. Single source might touch 10-15 pages.

2. **Query** — Search for relevant pages → read them → synthesize answer with citations. Key insight: **good answers can be filed back into the wiki as new pages** — compounding knowledge from questions as well as sources.

3. **Lint** — Health-check the wiki. Look for contradictions, stale claims, orphan pages, missing cross-references, data gaps. LLM suggests new questions to investigate.

## Indexing and logging

**index.md** — content-oriented catalog. Each page listed with link + one-line summary + metadata. Organized by category. LLM reads the index first to find relevant pages, then drills in. Works at moderate scale (~100 sources, ~hundreds of pages) without embeddings.

**log.md** — chronological append-only record. `grep "^## \[" log.md | tail -5` gives last 5 entries. Gives timeline and helps LLM understand what's been done recently.

## Use cases

- **Personal:** tracking goals, health, psychology — filing journal entries, articles, podcast notes
- **Research:** going deep on a topic over weeks/months — reading papers and building a comprehensive wiki with an evolving thesis
- **Reading a book:** filing each chapter, building character/theme/plot pages (like Tolkien Gateway)
- **Business/team:** internal wiki maintained by LLMs, fed by Slack, meetings, project docs
- **Competitive analysis, due diligence, trip planning, course notes, hobby deep-dives**

## Key design decisions

- **Intentionally abstract.** No specific directory structure, page formats, or tooling prescribed. "Everything mentioned above is optional and modular."
- **Human in the loop.** "I prefer to ingest sources one at a time and stay involved — I read the summaries, check the updates, and guide the LLM on what to emphasize."
- **Wiki as git repo.** Version history, branching, collaboration for free.
- **Obsidian as IDE.** "Obsidian is the IDE; the LLM is the programmer; the wiki is the codebase."

## Optional tooling

- **Obsidian Web Clipper** — browser extension for capturing articles as markdown
- **Obsidian graph view** — see shape of wiki (hubs, orphans)
- **Marp** — markdown-based slide decks from wiki content
- **Dataview** — Obsidian plugin for querying page frontmatter
- **qmd** — local search engine with hybrid BM25/vector search + LLM re-ranking (optional, for larger wikis)

## Why this works

"The tedious part of maintaining a knowledge base is not the reading or the thinking — it's the bookkeeping. Updating cross-references, keeping summaries current, noting when new data contradicts old claims, maintaining consistency across dozens of pages. Humans abandon wikis because the maintenance burden grows faster than the value. LLMs don't get bored, don't forget to update a cross-reference, and can touch 15 files in one pass."

## Historical connection

Karpathy connects the idea to **Vannevar Bush's Memex (1945)** — a personal, curated knowledge store with associative trails between documents. "Bush's vision was closer to this than to what the web became: private, actively curated, with the connections between documents as valuable as the documents themselves. The part he couldn't solve was who does the maintenance. The LLM handles that."

## Relevance to our pipeline

**Foundational.** This single document is the conceptual seed for everything we're building. Key principles we should measure ourselves against:

- **Compounding knowledge.** Our pipeline currently processes papers as independent units. We should be merging new knowledge into existing pages, flagging contradictions, and strengthening cross-references — not just writing new files.
- **Query answers filed back.** Our pipeline has no query capability yet. When we build it, answers should be persistable as new wiki pages.
- **Lint as first-class operation.** We have no lint/health-check step. Contradictions between papers, stale claims, orphan pages — all should be surfaced.
- **Index-driven retrieval.** Our SUMMARY_INDEX.md is a good start, but it's static. An auto-maintained index with one-line summaries per page that the LLM reads first would scale better.
- **Human in the loop.** Karpathy emphasizes staying involved — reading summaries, checking updates, guiding emphasis. Our pipeline is fully automated with no review step.
- **Wiki as git repo.** We already have this (the wiki is in git), but we don't leverage it for version history or branching.
