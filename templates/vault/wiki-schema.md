# Wiki Schema — Instructions for the LLM Agent

<!--
  Vault path: obsidian-vault (default WIKI_VAULT_DIR).
  If you set a different WIKI_VAULT_DIR, update every "obsidian-vault/" path in this file.
-->

This document defines how the LLM agent operates on the project wiki.

## Wiki Location

- **Vault root:** `obsidian-vault/` (default name; set `WIKI_VAULT_DIR` env var in `karpathy-wiki-manual-and-auto/.env` to change)
- **Raw sources:** `obsidian-vault/raw/` — immutable source documents (articles, devlog, transcripts)
- **Daily logs:** `obsidian-vault/daily/` — ephemeral auto-generated session logs (deleted after compilation)
- **Wiki pages:** `obsidian-vault/wiki/` — LLM-generated, structured knowledge
- **Index:** `obsidian-vault/index.md` — catalog of all wiki pages (READ FIRST)
- **Log:** `obsidian-vault/log.md` — chronological activity log (append-only)

## Four Rules

1. **Raw sources are immutable.** Never modify or delete files in `raw/`. Only read from them.
2. **Daily logs are ephemeral.** After processing a `daily/*.md` file into wiki pages, delete the source file.
3. **The LLM owns the wiki.** The LLM creates, updates, and deletes wiki pages. The human reads them (in Obsidian).
4. **Every change updates the index.** After any wiki mutation, update `index.md`.

## Operations

### Compile (the unified compiler)

A single compiler (`karpathy-wiki-manual-and-auto/scripts/compile.py`) processes both `raw/` and `daily/` sources into `wiki/` pages.

**Auto-trigger:** After 18:00, `flush.py` spawns `compile.py` if today's daily log has changed or there are unprocessed `raw/` files.

**Manual trigger:** User says "ingest", "обработай", "переведи в wiki", or runs:
```bash
uv run --directory karpathy-wiki-manual-and-auto python scripts/compile.py
```

**Process:**
1. Read the source file from `raw/` or `daily/`
2. Read `index.md` and existing wiki pages for context
3. Create or update wiki pages in the correct subfolder
4. Update `index.md` with new/modified pages
5. Append to `log.md`
6. If source was `daily/*.md`: delete the file after successful compilation

### Query

When the user asks a question about the project:
1. Read `index.md` first to locate relevant pages
2. Read the relevant wiki pages
3. Synthesize an answer with citations (link to wiki pages)
4. If the answer produces a valuable new artifact, offer to file it as a new wiki page

### Lint

When asked to "lint the wiki" or "health check":
```bash
uv run --directory karpathy-wiki-manual-and-auto python scripts/lint.py
```
Checks: broken links, orphans, unprocessed sources, stale pages, missing backlinks, sparse pages, contradictions.

## Wiki Page Format

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

## Subfolder Conventions

| Folder | Purpose | Example pages |
|--------|---------|---------------|
| `wiki/architecture/` | System design, data flows, component relationships | `server-architecture.md` |
| `wiki/decisions/` | Architectural and design decisions with rationale | `why-markdown-wiki-not-rag.md` |
| `wiki/bugs/` | Notable bugs, root causes, fixes | `visual-highlights-fix.md` |
| `wiki/features/` | Feature design docs, implementation notes | `auth-server.md` |
| `wiki/concepts/` | Domain concepts, glossary entries, atomic knowledge | `quality-tiers.md` |
| `wiki/operations/` | Deployment, infrastructure, CI/CD notes | `deployment.md` |
| `wiki/connections/` | Cross-cutting insights linking 2+ concepts | `auth-and-api-design.md` |

## Token Economy

- Always read `index.md` first — it tells you where everything is
- Don't scan directories blindly; use the index
- Keep wiki pages concise — they are summaries, not copies
- When updating multiple pages, batch your reads and writes

## Workflow Tips

- When starting a new session, read `index.md` and the last 5 entries of `log.md` to get oriented
- When the user describes a bug fix or design decision, offer to create a wiki page
- When the user says "remember this" or "note this", immediately create or update the relevant wiki page
- The wiki should reflect the project's current state, not its history — update pages when reality changes
