---
name: wiki-ingest
description: Unified wiki compiler. Processes sources from raw/ (immutable, manual) and daily/ (ephemeral, auto-generated) into structured wiki pages. Trigger when user says "ingest", "process raw", "wiki ingest", "переведи в wiki", "обработай raw", or "remember this" / "note this". Also handles "lint the wiki".
---

<!--
  Vault path: obsidian-vault (default WIKI_VAULT_DIR).
  If you set a different WIKI_VAULT_DIR, update every "obsidian-vault/" path in this file.
-->

# Wiki Ingest — Unified Source → Wiki Pipeline

Processes sources from `raw/` (immutable) and `daily/` (ephemeral) into structured wiki pages.

## Architecture

```
raw/     → compile.py → wiki/    (immutable sources, manual: devlog, articles)
daily/   → compile.py → wiki/    (ephemeral, auto-generated from sessions, deleted after processing)
                      → index.md (one index)
                      → log.md   (one log)
```

One compiler (`compile.py`) handles both source types. Automatic compilation triggered after 18:00 by `flush.py`. Manual via CLI or skill.

## Paths

- **Vault root:** `obsidian-vault/`
- **Raw sources:** `obsidian-vault/raw/` (immutable — never modify or delete)
- **Daily logs:** `obsidian-vault/daily/` (ephemeral — deleted after successful compilation)
- **Wiki pages:** `obsidian-vault/wiki/` (subfolders below)
- **Index:** `obsidian-vault/index.md` (single unified index)
- **Log:** `obsidian-vault/log.md` (single unified log)
- **Schema:** `obsidian-vault/wiki-schema.md`
- **Compiler:** `karpathy-wiki/scripts/compile.py`

## When to Trigger

1. User says "ingest", "process raw", "wiki ingest", "переведи в wiki", "обработай raw"
2. User adds files to `raw/` or `daily/` and asks to process them
3. User says "remember this" / "note this" / "запомни" (create wiki page from conversation)
4. User says "lint the wiki" / "check wiki health"

## Step-by-Step: Ingest

### 1. Run the compiler

```bash
uv run --directory karpathy-wiki python scripts/compile.py              # all unprocessed
uv run --directory karpathy-wiki python scripts/compile.py --source raw  # only raw/
uv run --directory karpathy-wiki python scripts/compile.py --source daily # only daily/
uv run --directory karpathy-wiki python scripts/compile.py --file <path> # specific file
uv run --directory karpathy-wiki python scripts/compile.py --dry-run     # preview
```

The compiler uses Claude Agent SDK to read sources and create/update wiki pages directly.

### 2. Verify results

After compilation:
- Check `obsidian-vault/index.md` for new pages
- Check `obsidian-vault/log.md` for the compilation entry
- Processed `daily/` files are automatically deleted

### 3. Manual override (if needed)

If the compiler missed something or you need fine-grained control:

1. Read the source file
2. Create wiki page manually in the correct subfolder
3. Update `index.md` and `log.md`

## Step-by-Step: "Remember This"

When user says "remember this" / "note this" without a source:

1. Create wiki page from conversation context
2. No `sources:` in frontmatter (or `sources: [conversation]`)
3. Update `index.md` + `log.md`

## Step-by-Step: Lint Wiki

```bash
uv run --directory karpathy-wiki python scripts/lint.py              # all checks
uv run --directory karpathy-wiki python scripts/lint.py --structural-only # free, no LLM
```

## Wiki Page Folders

| Folder | When to use |
|--------|-------------|
| `wiki/architecture/` | System design, data flows, component relationships |
| `wiki/decisions/` | Architectural/design decisions with rationale |
| `wiki/bugs/` | Notable bugs, root causes, fixes |
| `wiki/features/` | Feature design docs, implementation notes |
| `wiki/concepts/` | Domain concepts, glossary, patterns |
| `wiki/operations/` | Deployment, infrastructure, CI/CD, tooling |
| `wiki/connections/` | Cross-cutting insights linking 2+ concepts |

## Wiki Page Format

```yaml
---
title: Page Title
tags: [tag1, tag2]
date: YYYY-MM-DD
sources:
  - raw/path/to/source.md
related:
  - "[[other-wiki-page]]"
---
```

## Important

- **Never modify or delete files in `raw/`** — they are immutable
- **`daily/` files are auto-deleted after compilation** — they are ephemeral
- **Always update `index.md`** after any wiki mutation
- **Always append to `log.md`** — it's the audit trail
- **Wikilinks use the filename without extension:** `[[server-architecture]]` not `[[server-architecture.md]]`
