# Obsidian-Wiki: Architectural and Technical Summary

## Overview
**obsidian-wiki** is a **skill-based framework** — a collection of ~30 Markdown instruction files (SKILL.md) that any AI coding agent can read and execute to build and maintain an Obsidian knowledge base. By [Ar9av](https://github.com/Ar9av). MIT licensed.

**Core insight:** the agent IS the LLM. No scripts, no dependencies, no API keys. The skills are markdown files that tell the agent *how* to operate on your Obsidian vault. The wiki is the artifact. The agent is the maintainer. Obsidian is the viewer.

**Tagline:** "Instead of asking an LLM the same questions over and over (or doing RAG every time), you compile knowledge once into interconnected markdown files and keep them current."

## How it works (4-stage ingest)

1. **Ingest** — Agent reads source material directly (Markdown, PDFs, JSONL exports, chat logs, transcripts, images). No preprocessing, no pipeline.
2. **Pull Information** — Agent extracts concepts, entities, claims, relationships, open questions. Noise dropped, signal kept.
3. **Merge** — New knowledge merged against existing wiki. Updates existing pages, notes contradictions, strengthens cross-references. Nothing duplicated.
4. **Schema** — Schema emerges from sources and evolves. Agent maintains coherence: categories stay consistent, wikilinks point to real pages, index reflects reality.

## Directory structure

```
obsidian-wiki-main/
├── .skills/                          # ← Canonical skill definitions (source of truth)
│   ├── wiki-setup/SKILL.md
│   ├── wiki-ingest/SKILL.md
│   ├── wiki-history-ingest/SKILL.md
│   ├── wiki-query/SKILL.md
│   ├── wiki-lint/SKILL.md
│   ├── cross-linker/SKILL.md
│   ├── tag-taxonomy/SKILL.md
│   ├── wiki-update/SKILL.md
│   ├── wiki-export/SKILL.md
│   ├── wiki-capture/SKILL.md
│   ├── wiki-research/SKILL.md
│   ├── wiki-synthesize/SKILL.md
│   ├── wiki-dashboard/SKILL.md
│   ├── memory-bridge/SKILL.md
│   ├── daily-update/SKILL.md
│   ├── skill-creator/SKILL.md
│   └── ... (~30 total)
├── CLAUDE.md / AGENTS.md / GEMINI.md  # Bootstrap files for different agents
├── .cursor/rules/                     # Cursor always-on rules
├── .windsurf/rules/                   # Windsurf always-on rules
├── .kiro/steering/                    # Kiro steering
├── .agent/rules/ + workflows/         # Google Antigravity
├── setup.sh                           # One-command agent setup
├── pyproject.toml                     # Pure-stdlib CLI (obsidian-wiki)
├── obsidian_wiki/cli.py              # Thin CLI for skill installation
└── README.md / SETUP.md               # Docs
```

## Vault structure

```
$OBSIDIAN_VAULT_PATH/
├── index.md                # Master index — every page listed
├── log.md                  # Chronological activity log
├── hot.md                  # Session hot cache (~500 words)
├── .manifest.json          # Tracks every ingested source
├── _meta/
│   ├── taxonomy.md         # Controlled tag vocabulary
│   └── *.base              # Obsidian Bases dashboard definitions
├── _insights.md            # Graph analysis (hubs, bridges, dead ends)
├── _raw/                   # Staging area — rough notes promoted on next ingest
├── concepts/               # Abstract ideas, patterns, mental models
├── entities/               # Concrete things — people, tools, libraries, companies
├── skills/                 # How-to knowledge, techniques, procedures
├── references/             # Factual lookups — specs, APIs, configs
├── synthesis/              # Cross-cutting analysis
├── journal/                # Time-bound entries
└── projects/               # Per-project knowledge
```

## Agent compatibility matrix

Works with **any AI coding agent** that can read files:

| Agent | Bootstrap | Skills Dir | Slash Commands |
|---|---|---|---|
| Claude Code | CLAUDE.md | .claude/skills/ + ~/.claude/skills/ | ✅ |
| Cursor | .cursor/rules/ | .cursor/skills/ | ✅ |
| Windsurf | .windsurf/rules/ | .windsurf/skills/ | ✅ |
| Codex | AGENTS.md | ~/.codex/skills/ | ✅ ($) |
| Gemini CLI | GEMINI.md | ~/.gemini/skills/ | ✅ |
| Hermes | .hermes.md | ~/.hermes/skills/ | ✅ |
| Pi | AGENTS.md | ~/.pi/agent/skills/ | ✅ |
| Kiro | .kiro/steering/ | .kiro/skills/ | ✅ |
| OpenCode/Aider/Droid | AGENTS.md | ~/.agents/skills/ | ✅ |
| GitHub Copilot | .github/copilot-instructions.md | ~/.copilot/skills/ | ✅ |
| + many more | | | |

## Complete skill catalog (~30 skills)

| Skill | What it does |
|---|---|
| `wiki-setup` | Initialize vault structure |
| `wiki-ingest` | Distill documents into wiki pages |
| `wiki-history-ingest` | Unified history router (claude, codex, hermes, pi, openclaw, copilot) |
| `claude-history-ingest` | Mine ~/.claude conversations into wiki |
| `codex-history-ingest` | Mine ~/.codex sessions into wiki |
| `hermes-history-ingest` | Mine ~/.hermes memories into wiki |
| `pi-history-ingest` | Mine ~/.pi sessions into wiki |
| `data-ingest` | Ingest any text — chat exports, logs, transcripts |
| `ingest-url` | Fetch and ingest a URL |
| `wiki-status` | Show what's ingested, what's pending, delta |
| `wiki-rebuild` | Archive, rebuild from scratch, or restore |
| `wiki-query` | Answer questions from the wiki |
| `wiki-lint` | Find broken links, orphans, contradictions |
| `cross-linker` | Auto-discover and insert missing wikilinks |
| `tag-taxonomy` | Enforce consistent tag vocabulary |
| `wiki-update` | Sync current project's knowledge into vault |
| `wiki-export` | Export vault graph to JSON, GraphML, Neo4j, HTML |
| `wiki-capture` | Save current conversation as wiki note |
| `wiki-quick-chat-capture` | Zero-friction finding capture to _raw/ |
| `wiki-research` | Autonomous multi-round web research |
| `wiki-dashboard` | Dynamic Obsidian Bases dashboard views |
| `wiki-synthesize` | Discover and fill synthesis gaps |
| `wiki-agent` | Query-driven ingest from specific agent's history |
| `memory-bridge` | Browse and diff knowledge by which AI tool wrote it |
| `daily-update` | Daily maintenance cycle |
| `impl-validator` | Validate implementation against stated goal |
| `graph-colorize` | Color-code Obsidian graph by tag/category/visibility |
| `skill-creator` | Create new skills |

## Key features

- **Delta tracking.** `.manifest.json` tracks every ingested source — path, timestamps, pages produced. On next ingest, only processes new/changed.
- **Project-based organization.** Knowledge filed under projects/ when project-specific, globally when not. Both cross-referenced.
- **Archive and rebuild.** Timestamped snapshots, restore any previous state.
- **Multi-agent ingest.** Dedicated skills for Claude, Codex, Hermes, OpenClaw, Pi, Copilot history — plus catch-all for arbitrary text.
- **Cross-agent targeted search.** `/wiki-claude "rust ownership"` finds relevant conversations from a specific agent.
- **Provenance tracking.** Every claim tagged: extracted, `^[inferred]` (LLM synthesis), or `^[ambiguous]` (sources disagree).
- **Multimodal sources.** Screenshots, whiteboard photos, diagrams — transcribed by vision-capable models.
- **Wiki insights.** Hub detection, bridge pages, tag cluster cohesion, surprising connections.
- **Graph export.** JSON, GraphML, Neo4j Cypher, self-contained HTML visualization.
- **Tiered retrieval.** Read titles/tags/summaries first, only open bodies when cheap pass can't answer.
- **QMD semantic search (optional).** Plug in QMD for vector search over wiki and source documents.
- **`_raw/` staging directory.** Drop rough notes → next ingest promotes them.
- **Visibility tags.** `visibility/pii`, `visibility/internal`, `visibility/public` for content filtering.
- **Agent history ingestion.** Claude, Codex, Hermes, OpenClaw, Copilot, Pi — each with native format parsing.

## Tech stack

- Python 3.9+ (pure stdlib CLI, zero runtime dependencies)
- Hatchling build system
- ~30 Markdown skill files (the actual product)
- Skills distributed via pip, npx skills add, or git clone + setup.sh
- Optional: QMD for semantic search, Obsidian for visualization

## Relevance to our pipeline

**Directly relevant — closest conceptual match.** Obsidian-wiki is the most mature implementation of the Karpathy LLM Wiki pattern as a skill-based agent framework. Key takeaways:

- **Skill-based architecture.** Instead of a monolithic script, skills are modular Markdown files the agent reads on demand. This is a fundamentally different approach from our linear Python pipeline — more flexible, more agent-native.
- **Delta tracking with manifest.** `.manifest.json` tracks what's been ingested vs what's changed. Our pipeline has no delta tracking.
- **Cross-agent memory bridge.** The ability to query knowledge by which AI tool wrote it is novel and directly apposite to a multi-agent thesis.
- **Provenance tracking.** `extracted` vs `inferred` vs `ambiguous` tags on every claim. Our pipeline has no claim-level provenance.
- **Tiered retrieval.** Cheap index scan first, body reads only when needed. Keeps query cost flat as vault grows.
- **Graph export.** JSON/GraphML/Neo4j/HTML export. Our pipeline writes flat Markdown with no graph export.
- **Tag taxonomy enforcement.** Controlled vocabulary with audit skill. We just added tags but have no enforcement mechanism.
- **Agent history ingestion.** The ability to mine your own agent conversations into wiki pages is a powerful pattern for a thesis about LLM agent behavior.
- **Multi-agent compatibility.** The framework works across 15+ coding agents. This is relevant if our pipeline should ever target multiple agent platforms.
