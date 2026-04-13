# Wiki Compile Instructions

## Your Task

Process all `.md` files from the `daily/` folder and create wiki pages.

## Steps

1. Read `wiki-schema.md` to understand the page format
2. Read `index.md` to see existing pages
3. For each file in `daily/`:
   - Read the file
   - Create 1-2 wiki pages in appropriate `wiki/` subfolders
   - Use YAML frontmatter with title, tags, date, sources, related
4. Update `index.md` with new pages
5. Append to `log.md` with the source filename

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
Content here.
```

## Folders

Use the subfolders that exist in your wiki/ directory:
- `wiki/concepts/` — facts, patterns, how things work
- `wiki/decisions/` — why X over Y
- `wiki/connections/` — non-obvious links between concepts
- `wiki/architecture/` — system design (if exists)
- `wiki/bugs/` — bugs and fixes (if exists)
- `wiki/features/` — features (if exists)
- `wiki/operations/` — operations (if exists)

## IMPORTANT

- Use [[wikilinks]] for related pages (filename without extension)
- Keep pages concise (30-80 lines)
- Write in English unless source is in another language
- Delete processed daily files after creating wiki pages