# Wiki Schema — Instructions for the LLM Agent

This document defines how the LLM agent operates on the project wiki.

## Wiki Location

- **Vault root:** `obsidian/` (set `WIKI_VAULT_DIR` env var in `compiler/.env` to change)
- **Raw sources:** `obsidian/raw/` — immutable source documents (never delete)
- **Daily logs:** `obsidian/daily/` — ephemeral session logs (deleted after compilation)
- **Wiki pages:** `obsidian/wiki/` — LLM-generated, structured knowledge
- **Index:** `obsidian/index.md` — catalog of all wiki pages (READ FIRST)
- **Log:** `obsidian/log.md` — chronological activity log (append-only)

## Rules

1. **Raw sources are immutable.** Never modify or delete files in `raw/`.
2. **Daily logs are ephemeral.** After processing, delete the source file.
3. **The LLM owns the wiki.** Create, update, and delete wiki pages as needed.
4. **Every change updates the index.** After any mutation, update `index.md`.

## Two Folders

Only two subfolders (same model as [coleam00/claude-memory-compiler](https://github.com/coleam00/claude-memory-compiler)):

| Folder | Purpose | When to use |
|--------|---------|-------------|
| `wiki/concepts/` | Atomic knowledge: facts, patterns, bugs, features, ops, glossary | Single-topic pages |
| `wiki/connections/` | Cross-cutting articles linking multiple topics | Workflows, ADRs, design rationale |

**When in doubt, use `concepts/`.**

## Page Format

Every wiki page must include YAML frontmatter:

```yaml
---
title: Page Title
tags: [tag1, tag2]
date: 2026-04-10
lastmod: 2026-04-12
sources:
  - raw/article-name.md
related:
  - "[[other-wiki-page]]"
---
```

Body: concise markdown, 30-80 lines. Summary, not copy of the source.

## Filtering

Not everything deserves a wiki page. Before creating:

**Skip:** debug sessions that led nowhere, UI tweaks, failed hypotheses, routine tool calls, `FLUSH_OK` entries, unimplemented feature requests.

**Keep:** bugs found + fixed, features implemented, architectural decisions, patterns/gotchas, significant refactoring, config/infra changes.

## Conventions

- File names: `lowercase-with-hyphens.md`
- Wikilinks: `[[filename]]` without `.md` extension
- Writing style: encyclopedia, factual, concise
- Start every session by reading `index.md`
