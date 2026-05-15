---
name: wiki-remember
description: >-
  Creates or updates a wiki page from the current conversation. Trigger when the
  user says remember this, note this, запомни, or invokes this skill. Writes only
  under ~/WIKI/PROJECT-NAME/obsidian/ — no compile.py.
disable-model-invocation: true
---

<!--
  Replace PROJECT-NAME with your wiki folder.
-->

# Wiki — Remember this

## Scope

- **Vault:** `~/WIKI/PROJECT-NAME/obsidian/`

## Steps

1. Read `obsidian/index.md`.
2. **Search for existing page before writing:**
   - Check `index.md` titles/summaries for the same topic
   - Scan filenames in `wiki/concepts/` and `wiki/connections/`
   - If match found → read it → update (merge, remove stale info, update `lastmod` + `sources`)
   - Only create new file if topic is genuinely new
3. Pick folder: `wiki/concepts/` unless note ties multiple systems (`wiki/connections/`).
4. Write with YAML frontmatter per `obsidian/wiki-schema.md` (include `sources: [conversation]`).
5. Update `obsidian/index.md` and append `obsidian/log.md`.

Do **not** run `compile.py`. Do **not** delete `raw/` or unprocessed `daily/` files unless the user asked to fold this into a daily ingest.
