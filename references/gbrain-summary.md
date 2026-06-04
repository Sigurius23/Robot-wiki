# GBrain: Architectural and Technical Summary

## Overview
**GBrain** is a production-scale personal knowledge brain by [Garry Tan](https://github.com/garrytan) (President & CEO of Y Combinator). Built in TypeScript on Bun, it powers his own AI agent deployments: **146,646 pages, 24,585 people, 5,339 companies**, 66 cron jobs running autonomously. MIT licensed.

**Core insight:** "Search gives you raw pages. GBrain gives you the answer." It combines hybrid retrieval (vector + keyword + graph) with a synthesis layer that produces well-cited prose with explicit gap analysis — telling you what the brain *doesn't* know yet.

**Tagline:** "The brain layer your AI agent has been missing — the only one that does synthesis, graph traversal, and gap analysis in one box."

## How it works (the loop)

```
signal → search → respond → write → auto-link → sync
(every    (brain-first  (informed     (page +    (typed edges     (cron
message)  retrieval)    by context)   timeline)  + backlinks)     keeps fresh)
```

## Directory structure

```
gbrain-master/
├── package.json                # Bun/TypeScript project (v0.42.21.0)
├── VERSION                     # Single source of truth
├── README.md                   # Comprehensive docs with cost matrix, tutorials
├── CLAUDE.md                   # ~39KB orientation + dispatcher (was 592KB)
├── AGENTS.md                   # Entry point for non-Claude agents
├── DESIGN.md                   # Design system tokens (colors, typography, voice)
├── CHANGELOG.md                # Extremely detailed release history
├── INSTALL_FOR_AGENTS.md       # 9-step agent-driven install protocol
├── src/
│   ├── cli.ts                  # CLI entry point (compiled via bun build)
│   ├── core/
│   │   ├── engine.ts           # Contract-first BrainEngine interface (~47 ops)
│   │   ├── postgres-engine.ts  # Postgres + pgvector implementation
│   │   ├── pglite-engine.ts    # PGLite (Postgres 17 via WASM, zero-config)
│   │   ├── operations.ts       # Single source: CLI + MCP generated from this
│   │   ├── migrate.ts          # Schema migrations (100+ versions)
│   │   ├── search/
│   │   │   ├── hybrid.ts       # Hybrid search: vector HNSW + BM25 + RRF + reranker
│   │   │   ├── mode.ts         # 3 search modes (conservative, balanced, tokenmax)
│   │   │   ├── expansion.ts    # LLM multi-query expansion
│   │   │   └── autocut.ts      # Score-discontinuity result-sizing
│   │   ├── link-extraction.ts  # Zero-LLM entity ref extraction from markdown
│   │   ├── think/              # Synthesis layer (brain layer)
│   │   ├── minions/            # BullMQ-shaped job queue (durable sub-agents)
│   │   ├── calibration/        # Hindsight calibration (Brier scores, voice gate)
│   │   ├── skillopt/           # Self-improving skill optimizer
│   │   └── ai/                 # Provider gateway (Anthropic, OpenAI, Google, etc.)
│   ├── commands/               # CLI command implementations
│   └── mcp/                    # MCP server (30+ tools, stdio + HTTP + OAuth 2.1)
├── skills/                     # 43 curated skills + RESOLVER.md dispatcher
│   ├── RESOLVER.md             # Two-layer routing (functional-area pattern)
│   ├── signal-detector/SKILL.md
│   ├── brain-ops/SKILL.md
│   ├── ingest/SKILL.md
│   ├── enrich/SKILL.md
│   └── ... (43 total)
├── docs/
│   ├── architecture/           # System design, topologies, retrieval theory
│   ├── tutorials/              # personal-brain, company-brain, skillopt
│   ├── guides/                 # search-modes, minions, skill development
│   ├── integrations/           # Voice, email, calendar, embedding providers
│   ├── mcp/                    # Per-client MCP setup (Claude, Codex, ChatGPT, etc.)
│   ├── eval/                   # Eval framework, metric glossary, methodology
│   └── ethos/                  # Philosophy (thin harness, fat skills, origin story)
├── recipes/                    # Integration recipes (Twilio voice, email, etc.)
├── tests/                      # Extensive test suite (unit, E2E, engine parity)
├── evals/                      # Functional-area-resolver eval harness
├── admin/                      # React SPA admin dashboard
└── scripts/                    # ~50 CI/CD/verification scripts
```

## Architecture

**Two engines, one contract.** PGLite (Postgres 17 via WASM, zero-config, default) for personal brains up to ~50K pages. Postgres + pgvector (Supabase or self-hosted) for shared/large/multi-machine deployments. The contract-first `BrainEngine` interface in `src/core/engine.ts` defines ~47 operations both engines implement.

**Two organizational axes (brain ⊥ source).** A *brain* is a database (personal, team-mounted). A *source* is a repo inside that brain (wiki, gstack, essays). Routing via `.gbrain-source` dotfiles with 6-tier precedence chain.

**Trust boundary.** `OperationContext.remote` distinguishes trusted local CLI callers from untrusted agent-facing MCP callers. Security-sensitive operations tighten filesystem confinement when `remote=true`.

## Key capabilities

### Hybrid search
- Vector (HNSW on pgvector) + BM25 keyword + reciprocal-rank fusion + source-tier boost + intent-aware query rewriting
- Three named modes: `conservative` (4K tokens), `balanced` (12K), `tokenmax` (20K+expansion)
- Cross-encoder reranker (ZeroEntropy zerank-2, optional local Qwen3-Reranker via llama.cpp)
- Per-query graph signals: adjacency boost, cross-source boost, session demote
- `--explain` shows per-stage attribution
- Autocut: score-discontinuity result-sizing (v0.42.3.0)
- Cache invalidation via knobs_hash versioning

### Self-wiring knowledge graph
- Every `put_page` extracts entity refs from markdown/wikilinks/typed-link syntax
- Zero LLM calls for extraction — pure pattern matching
- Typed edges: `attended`, `works_at`, `invested_in`, `founded`, `advises`, `mentions`, etc.
- Multi-hop traversal via `gbrain graph-query`
- Benchmark: **P@5 49.1%, R@5 97.9%** on 240-page corpus, **+31.4 P@5** over vector-only RAG
- Obsidian-style basename resolution (opt-in `link_resolution.global_basename`)

### Synthesis layer (`gbrain think`)
- Retrieves top pages, composes synthesized answer with citations
- Gap analysis: tells you when a page is stale, when claims are uncited, when pages contradict
- `find_trajectory` for temporal/entity queries
- Honesty: explicit "what the brain doesn't know yet" sections

### Job queue (Minions)
- BullMQ-shaped, Postgres-native
- Durable sub-agents (two-phase pending→done persistence)
- Shell jobs with audit, child jobs with cascading timeouts
- Rate leases for outbound providers
- Crash-safe: survives process death

### Schema packs
- No fixed layout — ships with bundled packs (`gbrain-base-v2`, `gbrain-recommended`)
- User-authored packs via `gbrain schema detect` → `suggest` → `review-candidates` → `use`
- Seven-tier resolution chain (per-call flag → env var → per-source DB → brain-wide → config → global → default)
- 15-type DRY/MECE canonical taxonomy in `gbrain-base-v2`

### Evals framework
- `gbrain eval longmemeval` — public LongMemEval benchmark
- `gbrain eval export` + `replay` — capture real queries, replay against code changes
- `gbrain eval cross-modal` — cross-check outputs with three frontier models
- `gbrain eval retrieval-quality` — NamedThingBench for named-thing retrieval
- `gbrain eval suspected-contradictions` — find conflicts between takes
- Per-run records in `.gbrain-evals/eval-results.jsonl`

### Content-quality gate (v0.42.6.0)
- Detects junk (Cloudflare/CAPTCHA pages) → quarantines
- Flags boilerplate-heavy pages → warns agent
- Unusually large pages → soft-blocked
- Agent-warning channel on search results

### Self-maintenance
- `gbrain doctor` — comprehensive health check (worker OOM, pool health, extraction lag, etc.)
- `gbrain dream` — autonomous overnight cycle (sync, synthesize, embed, extract, lint, backlinks)
- `gbrain enrich --thin` — develops stub pages from brain-internal knowledge
- `gbrain self-upgrade` — atomic binary self-update + autopilot silent channel
- Resumable sync with checkpoint banking (v0.42.17.0)

### MCP server
- 30+ tools over stdio and HTTP (OAuth 2.1, DCR-style client registration)
- Admin dashboard at /admin (scope-gated: read/write/admin)
- Thin-client support (remote MCP)
- Supported clients: Claude Code, Claude Desktop, Cursor, Windsurf, Codex, ChatGPT, Perplexity, Cowork

### Company brain mode
- Federated multi-user with OAuth-scoped access
- Each user sees only their slice — source-scoped, login-gated
- Fuzz-tested for zero cross-user leaks
- Tutorial: `docs/tutorials/company-brain.md`

## Operational hardening (notable fixes)

The CHANGELOG reveals extraordinary operational maturity:
- **Background work drain on exit** (v0.42.20.0) — prevents PGLite lock pinning
- **AI call timeouts** (v0.42.20.0) — stalled providers fall back to keyword results
- **Process watchdog** (v0.42.18.0) — hard deadline for runaway sync on cron
- **Resumable sync** (v0.42.17.0) — checkpoint banking for 44K-page imports
- **OOM-loop detection** (v0.42.16.0) — cause-ranked doctor, worker watchdog
- **Connection ownership** (v0.42.21.0) — shared singleton not nulled by borrowers
- **Wikilink basename resolution** (v0.42.10.0) — Obsidian-style `[[bare-name]]` links
- **Skill self-improvement** (v0.42.11.0) — held-out validation gate, honest receipts

## Tech stack

- **Runtime:** Bun 1.3.10+, TypeScript 5.6+
- **Database:** PGLite (embedded Postgres 17 via WASM) or Postgres + pgvector
- **AI:** AI SDK v6 (@ai-sdk/anthropic, @ai-sdk/openai, @ai-sdk/google)
- **Search:** pgvector HNSW, ZeroEntropy reranker, BM25 via ts_vector
- **Server:** Express 5, MCP SDK 1.29.0, OAuth 2.1
- **Build:** bun build --compile (single binary)
- **Testing:** Bun test, Docker-based CI, 29 E2E files
- **Admin:** React SPA with embedded server-side SVG charts
- **Voice:** Twilio + OpenAI Realtime (optional recipe)

## Relevance to our pipeline

**Deeply relevant — production reference architecture.** GBrain represents the most mature, battle-hardened implementation of the LLM Wiki pattern in existence. Key takeaways:

- **Hybrid search is essential at scale.** BM25 + vector + graph + reranker. Our pipeline has no retrieval layer — this is the blueprint for adding one.
- **Synthesis with gap analysis.** `gbrain think` tells you what it doesn't know. Our crossref notes could be enhanced with confidence/uncertainty signals.
- **Self-wiring knowledge graph.** Zero-LLM entity extraction from markdown. Our pipeline writes flat files with no graph — the edge schemas from AutoSci could be populated automatically using GBrain's approach.
- **Schema packs.** Evolving taxonomy without fixed layout. Our pipeline has fixed output paths.
- **Operational maturity.** The sheer volume of hardening (background work drain, process watchdog, resumable sync, OOM detection, connection ownership) is a masterclass in running an LLM pipeline in production.
- **Company brain / multi-user mode.** Federated access with source-scoping. Relevant if our wiki ever becomes a shared resource.
- **Eval framework.** NamedThingBench, LongMemEval, replay-based regression testing. We have unit tests but no retrieval evals.
- **Content-quality gate.** Automatic junk detection and boilerplate flagging. Our pipeline trusts raw PDF text blindly.
- **Skill-based agent integration.** 43 skills dispatched through RESOLVER.md. The obsidian-wiki skill approach taken to production scale.
- **MCP server with OAuth.** 30+ tools, scope-gated, thin-client support. Our pipeline has no server component.
