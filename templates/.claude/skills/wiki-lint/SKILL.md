---
name: wiki-lint
description: >-
  Runs wiki health checks for this project vault. Trigger when the user says lint the wiki,
  lint wiki, wiki health, or invokes this skill.
disable-model-invocation: true
---

<!--
  Replace PROJECT-NAME with your wiki folder.
-->

# Wiki — Lint

## Scope

- **Compiler:** `~/WIKI/PROJECT-NAME/compiler/`

## Commands

Full checks:

```bash
uv run --directory ~/WIKI/PROJECT-NAME/compiler python scripts/lint.py
```

Structural only (no LLM / cheaper):

```bash
uv run --directory ~/WIKI/PROJECT-NAME/compiler python scripts/lint.py --structural-only
```

Summarize results for the user and suggest concrete fixes for reported issues.
