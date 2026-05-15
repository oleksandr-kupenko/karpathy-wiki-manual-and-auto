---
name: wiki-ingest-raw
description: >-
  Compiles immutable sources from obsidian/raw/ into wiki pages for this project only.
  Trigger when the user says ingest raw, compile raw, or invokes this skill. Prefer
  compile.py --source raw when the compiler is configured; otherwise manual ingest from raw/.
disable-model-invocation: true
---

<!--
  Replace PROJECT-NAME with your wiki folder.
-->

# Wiki — Ingest raw

## Scope

- **Vault:** `~/WIKI/PROJECT-NAME/obsidian/`
- **Compiler:** `~/WIKI/PROJECT-NAME/compiler/`

## Scripted path (optional, paid / API)

If `~/WIKI/PROJECT-NAME/compiler/.env` is configured and the user wants script-based compile:

```bash
uv run --directory ~/WIKI/PROJECT-NAME/compiler python scripts/compile.py --source raw
```

Preview without writes:

```bash
uv run --directory ~/WIKI/PROJECT-NAME/compiler python scripts/compile.py --source raw --dry-run
```

Then verify `obsidian/index.md` and `obsidian/log.md`.

## Manual path (default, free)

If no API setup or the user prefers no script:

1. Read `obsidian/raw/*.md` (and other raw assets as applicable).
2. Create or update pages under `obsidian/wiki/` per `wiki-schema.md`.
3. Update `index.md`, append `log.md`.

**Never** delete or modify files under `obsidian/raw/` (immutable).
