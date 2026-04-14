# AGENTS.md - Unified Knowledge Base Schema

> Adapted from [Andrej Karpathy's LLM Knowledge Base](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) architecture.

## The Compiler Analogy

```
raw/            = source code    (immutable: devlog, articles, transcripts)
daily/          = source code    (ephemeral: auto-generated session logs, deleted after compile)
LLM             = compiler       (extracts and organizes knowledge)
wiki/           = executable     (structured, queryable knowledge base)
lint            = test suite     (health checks for consistency)
```

---

## Architecture

### Layer 1: Sources (`raw/` + `daily/`)

Two types of sources feed into one compiler:

| Source | Nature | Lifecycle |
|--------|--------|-----------|
| `raw/` | Manual: devlog files, articles, transcripts | Immutable — never modified or deleted |
| `daily/` | Auto-generated: session summaries from hooks | Ephemeral — deleted after compilation |

### Layer 2: Wiki (`wiki/`)

LLM-owned, human-readable. One index, one log.

```
wiki/
├── concepts/        Atomic knowledge: facts, patterns, bugs, features, system notes, domain, ops
└── connections/     Cross-cutting links, workflows, rationale spanning multiple topics
```

Same **two-folder** layout as [coleam00/claude-memory-compiler](https://github.com/coleam00/claude-memory-compiler) (`concepts/` + `connections/`). Older vaults with extra subfolders are optional; scripts only scan `WIKI_SUBDIRS` from `scripts/config.py`.

### Structural Files

- **`index.md`** — Master catalog. Every wiki page with a one-line summary. READ FIRST for any query.
- **`log.md`** — Append-only build log. Audit trail of every compile, query, lint.
- **`wiki-schema.md`** — Schema for the LLM agent operating on the wiki.

---

## Article Format

Every wiki page must have YAML frontmatter:

```yaml
---
title: "Page Title"
tags: [tag1, tag2]
date: 2026-04-10
lastmod: 2026-04-12
sources:
  - "raw/devlog/server/auth.md"
related:
  - "[[other-wiki-page]]"
---
```

Body is concise markdown — **summary, not copy** of the source. Target 30-80 lines.

---

## Automation (Hook System)

Hooks in `.claude/settings.json` fire automatically in Claude Code:

| Hook | When | What it does |
|------|------|-------------|
| `session-start.py` | Session starts | Reads index.md + recent daily log → injects into context |
| `session-end.py` | Session ends | Extracts conversation → spawns flush.py → daily log |
| `pre-compact.py` | Before context compaction | Same as session-end (saves context before it's lost) |

**`flush.py`** (background process):
1. Extracts key knowledge from conversation via DeepSeek/Claude
2. Appends to `daily/YYYY-MM-DD.md`
3. After 18:00: if daily log changed → spawns `compile.py`

**`compile.py`** (the unified compiler):
- Processes both `raw/` and `daily/` sources
- Uses Claude Agent SDK to create/update wiki pages directly
- Deletes processed `daily/` files automatically
- State tracked in `state.json` (SHA-256 hashes, costs)

---

## Scripts

| Script | Purpose |
|--------|---------|
| `compile.py` | Compile sources → wiki pages (both raw/ and daily/) |
| `flush.py` | Extract knowledge from conversations → daily log |
| `query.py` | Index-guided knowledge base Q&A |
| `lint.py` | Health checks (broken links, orphans, contradictions) |
| `config.py` | Path constants |
| `utils.py` | Shared helpers |

---

## State Tracking

`scripts/state.json`:
- `ingested` — map of source keys (`daily/file.md` or `raw/path/file.md`) to hashes, timestamps, costs
- `total_cost` — cumulative API cost

`scripts/last-flush.json`:
- Flush deduplication (session_id + timestamp)

Both are gitignored and regenerated automatically.

---

## Conventions

- **Wikilinks:** `[[filename]]` without `.md` extension, without folder prefix
- **Writing style:** Encyclopedia-style, factual, concise
- **File naming:** lowercase, hyphens for spaces
- **Frontmatter:** Required on every page (title, tags, date, sources, related)
