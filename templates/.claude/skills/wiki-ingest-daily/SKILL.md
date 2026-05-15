---
name: wiki-ingest-daily
description: >-
  Turns session summaries in obsidian/daily/ into wiki pages for this project only.
  Trigger when the user says ingest daily, create wiki from daily, обработай daily,
  or invokes this skill. Manual agent compile only — do not run compile.py for daily.
disable-model-invocation: true
---

<!--
  Replace PROJECT-NAME with your wiki folder.
-->

# Wiki — Ingest daily (manual)

## Scope

- **Vault:** `~/WIKI/PROJECT-NAME/obsidian/`

## Important

**Do not** run `compile.py` for this workflow (daily ingest is manual: you read, write wiki pages, then clean up `daily/`).

## Steps

1. Read `obsidian/wiki-schema.md`, `obsidian/index.md`, and every `obsidian/daily/*.md`.
2. Follow `obsidian/COMPILE_INSTRUCTIONS.md` for classification (`concepts/` vs `connections/`) and frontmatter.
3. **For each topic, check for an existing page before writing:**
   - Search `index.md` titles and summaries for the same feature/bug/topic
   - Scan filenames in `wiki/concepts/` and `wiki/connections/` for name overlap
   - If a match exists → read it → **update** it (merge new info, remove stale facts, update `lastmod` + `sources`)
   - Only create a new file if no existing page covers this topic
4. Update `index.md` (new rows for new pages; update summary/date for updated pages). Append `log.md` (note created vs updated count).
5. After success, **delete** the processed `obsidian/daily/*.md` files.
6. **Never** delete anything under `obsidian/raw/`.

## Filter

Skip low-signal noise (see the umbrella `wiki-ingest` skill for skip/keep heuristics if needed).
