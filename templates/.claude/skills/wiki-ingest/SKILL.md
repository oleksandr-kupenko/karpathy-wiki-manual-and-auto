---
name: wiki-ingest
description: Wiki compiler skill. Trigger when user says "ingest", "create wiki", "compile wiki", "обработай", "переведи в wiki", "remember this", "note this", or "lint the wiki". Creates wiki pages from daily logs and raw sources.
---

<!--
  IMPORTANT: Update all paths below to match your actual setup.
  Default assumes wiki at ~/WIKI/<project>/obsidian/ and compiler at ~/WIKI/<project>/compiler/
-->

# Wiki Ingest Skill

## Vault Location

All wiki files live at: `~/WIKI/PROJECT-NAME/obsidian/`

```
obsidian/
├── index.md              ← Master catalog — READ FIRST
├── log.md                ← Append-only activity log
├── wiki-schema.md        ← Schema and conventions
├── daily/                ← Ephemeral session logs (DELETE after compiling)
├── raw/                  ← Immutable source documents (NEVER delete)
└── wiki/
    ├── concepts/         ← Atomic knowledge: patterns, bugs, features, how-tos
    └── connections/      ← Cross-cutting pages linking multiple topics
```

## Compilation Mode

### Default: Manual (Free)

When the user says "ingest", "create wiki", "compile wiki", "обработай", etc.:

**You (the assistant) compile wiki pages directly** — read source files, create .md pages, update index. No scripts needed. This is the default and recommended approach.

### Optional: Automatic (Script-based, Paid)

If `~/WIKI/PROJECT-NAME/compiler/.env` has API keys configured, you can also run:
```bash
uv run --directory ~/WIKI/PROJECT-NAME/compiler python scripts/compile.py
```
This uses an LLM API (DeepSeek or Claude Agent SDK) to compile automatically. **Only use this if the user explicitly set up API keys and asked for script-based compilation.**

---

## Step-by-Step: Manual Compilation (Default)

When the user says "ingest", "create wiki from daily", "обработай":

### 1. Read sources

Read all files in `obsidian/daily/` (and `obsidian/raw/` if asked).
Read `obsidian/index.md` to understand existing pages.

### 2. Filter: What's Worth a Wiki Page

**Skip (do NOT create pages for):**
- Debugging sessions that led nowhere
- UI tweaks with no architectural impact
- Failed hypotheses
- `FLUSH_OK - Nothing worth saving` entries
- Routine tool calls or file reads
- Feature requests not yet implemented

**Keep (create or update pages for):**
- Bugs found and fixed (root cause + solution)
- Features implemented (architecture, decisions, key files)
- Architectural decisions with rationale
- Patterns, gotchas, lessons learned
- Significant refactoring (what changed and why)
- Config/infra changes affecting production

**When updating is enough:** If a session adds minor context to an existing topic, update the existing page rather than creating a new one.

### 3. Classify and create pages

For each piece of knowledge, choose a folder:

| Folder | When to use |
|--------|-------------|
| `concepts/` | Single-topic pages: patterns, bugs, features, how things work, ops, glossary |
| `connections/` | Pages whose main value is relating multiple topics (workflows, ADRs spanning systems) |

**When in doubt, use `concepts/`.**

One `.md` file per topic. Each page **must** have YAML frontmatter:

```markdown
---
title: "Page Title"
tags: [tag1, tag2]
date: YYYY-MM-DD
sources:
  - "daily/2026-04-14.md"
related:
  - "[[other-wiki-page]]"
---

Concise encyclopedia-style content. 30-80 lines. Facts, not narration.
```

**Rules:**
- File names: `lowercase-with-hyphens.md`
- If a page on this topic already exists — **update it**, don't duplicate
- Wikilinks: `[[filename-without-extension]]`
- Be concise: summarize, don't copy-paste

### 4. Update index.md

Add new pages to the Concepts or Connections table:

```markdown
| [[page-filename]] | One-line summary | 2026-04-14 |
```

Update the `Total pages:` count.

### 5. Append to log.md

```markdown
| 2026-04-14 | manual | daily/2026-04-14.md | 2 pages created |
```

### 6. Delete processed daily files

After successfully compiling, **delete** the `daily/*.md` files that were processed.
**Never** delete files from `raw/`.

---

## "Remember This" / "Note This"

When the user says "remember this", "note this", "запомни":

1. Create or update the most relevant wiki page with the information
2. Add `sources: [conversation]` in frontmatter
3. Update `index.md` + `log.md`

---

## Lint Wiki

```bash
uv run --directory ~/WIKI/PROJECT-NAME/compiler python scripts/lint.py              # all checks
uv run --directory ~/WIKI/PROJECT-NAME/compiler python scripts/lint.py --structural-only # free, no LLM
```

---

## Query Mode

When the user asks a question about the project:
1. Read `obsidian/index.md` to find relevant pages
2. Read the relevant wiki pages
3. Answer with citations using `[[wikilinks]]`

---

## Important

- **Never modify or delete files in `raw/`** — they are immutable
- **`daily/` files are deleted after compilation** — they are ephemeral
- **Always update `index.md`** after any wiki mutation
- **Always append to `log.md`** — it's the audit trail
- **Wikilinks use filename without extension:** `[[server-architecture]]` not `[[server-architecture.md]]`
