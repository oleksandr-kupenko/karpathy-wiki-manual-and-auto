# Wiki Compile Instructions

## Your Task

Process `.md` files from `daily/` and/or `raw/` and create wiki pages.

## Steps

1. Read `wiki-schema.md` to understand the page format
2. Read `index.md` to see existing pages
3. For each source file:
   - Read the file
   - Evaluate: is this worth a wiki page? (Skip debug sessions, UI tweaks, failed hypotheses, FLUSH_OK entries)
   - Create 1-2 wiki pages in `wiki/concepts/` or `wiki/connections/`
   - Use YAML frontmatter with title, tags, date, sources, related
4. Update `index.md` with new pages
5. Append to `log.md` with the source filename
6. Delete processed `daily/` files

## Page Format

```yaml
---
title: Page Title
tags: [tag1, tag2]
date: YYYY-MM-DD
sources:
  - daily/filename.md
related:
  - [[other-page]]
---
Content here (30-80 lines, encyclopedia style).
```

## Two Folders Only

- `wiki/concepts/` — single-topic pages: facts, patterns, bugs, features, ops
- `wiki/connections/` — pages linking multiple topics: workflows, ADRs

**When in doubt, use `concepts/`.**

## Rules

- Use `[[wikilinks]]` for related pages (filename without extension)
- Keep pages concise (30-80 lines)
- If a page on this topic already exists, update it
- Delete processed daily files after creating wiki pages
- Never delete files from `raw/`
