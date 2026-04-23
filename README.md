# Karpathy Memory — Persistent Wiki for AI Coding Assistants

Permanent memory for AI coding assistants (Claude Code, OpenCode, Cursor). Based on [Andrej Karpathy's method](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): Markdown Wiki instead of RAG.

## What It Does

AI assistants forget everything between sessions. This project gives them permanent memory:

1. **Session start** — wiki index injected into assistant context (it "remembers")
2. **During session** — hooks capture conversation context
3. **Session end** — key knowledge is summarized into daily logs
4. **Compile** — daily logs + raw notes become structured wiki pages

## Structure

Wiki lives **outside** your project repo (one wiki can serve multiple projects):

```
~/WIKI/
└── my-project/
    ├── compiler/                ← This repo (cloned here)
    │   ├── scripts/             ← compile.py, flush.py, lint.py, query.py
    │   └── hooks/               ← Python hooks for Claude/Cursor
    └── obsidian/                ← The vault (knowledge base)
        ├── index.md             ← Master catalog — READ FIRST
        ├── log.md               ← Append-only activity log
        ├── wiki-schema.md       ← Schema for the LLM agent
        ├── raw/                 ← Immutable sources (never deleted)
        ├── daily/               ← Ephemeral session logs (deleted after compile)
        └── wiki/
            ├── concepts/        ← Atomic knowledge: patterns, bugs, features, how-tos
            └── connections/     ← Cross-cutting: workflows, design rationale spanning topics
```

In your **project repo**, you only need three things:
- **Skill file** — `.claude/skills/wiki-ingest/SKILL.md` (instructions for the assistant)
- **Hooks config** — `.claude/settings.json`, `.opencode/`, or `.cursor/hooks.json`
- **CLAUDE.md snippet** — wiki protocol instructions

---

## Setup Guide (Prompt for AI Assistant)

When a user asks to "set up karpathy-wiki for my project", follow these steps one by one. **Ask before acting.**

### Step 1: Ask About Wiki Location

Ask the user:

> Where should I create the wiki? Default: `~/WIKI/<project-name>/` — a folder **outside** your project repo.
> It will have two subdirectories: `compiler/` (scripts from this repo) and `obsidian/` (the knowledge base).
>
> Example: if your project is at `~/projects/my-app`, the wiki would be at `~/WIKI/my-app/`.

If the user doesn't specify, use `~/WIKI/<project-name>/` where `<project-name>` matches the project's folder name.

### Step 2: Clone and Install

```bash
WIKI_BASE="$HOME/WIKI/my-project"  # use the path from Step 1

mkdir -p "$(dirname "$WIKI_BASE")"
git clone https://github.com/oleksandr-kupenko/karpathy-wiki-manual-and-auto.git "$WIKI_BASE/compiler"
cp -r "$WIKI_BASE/compiler/templates/vault" "$WIKI_BASE/obsidian"
cd "$WIKI_BASE/compiler" && uv sync
```

### Step 3: Ask About Compilation Mode

Ask the user:

> How should wiki pages be created?
>
> **Option A — Manual (default, free):** You tell the assistant "create wiki from daily" or "ingest". The assistant reads source files and creates wiki pages directly — no scripts, no API costs.
>
> **Option B — Automatic (paid):** After 18:00, a Python script automatically compiles daily logs into wiki pages using an LLM. Requires DeepSeek API key (~$0.01/compile) or Claude Agent SDK (~$2+/compile).

If Option A: skip `.env` and `compile-config.json` setup. The assistant handles compilation manually when asked.

If Option B: create `$WIKI_BASE/compiler/.env`:
```
DEEPSEEK_API_KEY=sk-your-key-here
```
And `$WIKI_BASE/compiler/compile-config.json`:
```json
{"provider": "opencode"}
```

### Step 4: Install Templates Into Project

Ask which AI assistants the user works with, then copy the corresponding templates:

```bash
PROJECT_DIR="/path/to/your/project"
WIKI_BASE="$HOME/WIKI/my-project"
```

**Claude Code:**
```bash
mkdir -p "$PROJECT_DIR/.claude/skills/wiki-ingest"
cp "$WIKI_BASE/compiler/templates/.claude/settings.json" "$PROJECT_DIR/.claude/settings.json"
cp "$WIKI_BASE/compiler/templates/.claude/skills/wiki-ingest/SKILL.md" "$PROJECT_DIR/.claude/skills/wiki-ingest/SKILL.md"
```
> If `.claude/settings.json` already exists, merge the `"hooks"` key manually.

**OpenCode:**
```bash
cp -r "$WIKI_BASE/compiler/templates/.opencode" "$PROJECT_DIR/.opencode"
cp "$WIKI_BASE/compiler/templates/opencode.json" "$PROJECT_DIR/opencode.json"
cd "$PROJECT_DIR/.opencode" && npm install
```

**Cursor AI** (requires Cursor 1.7+):
```bash
mkdir -p "$PROJECT_DIR/.cursor"
cp "$WIKI_BASE/compiler/templates/cursor-hooks.json" "$PROJECT_DIR/.cursor/hooks.json"
```

### Step 5: Update Paths

Replace all path placeholders in the copied templates with actual paths:

- `.claude/settings.json` — update `uv run --directory ...` paths in hook commands
- `.claude/skills/wiki-ingest/SKILL.md` — update vault and compiler paths
- `.opencode/plugins/memory-compiler.ts` — update `compilerDir` and `vaultDir`
- `.cursor/hooks.json` — update hook command paths
- `CLAUDE.md` snippet — update vault path

### Step 6: Add CLAUDE.md Snippet

Append the content of `$WIKI_BASE/compiler/templates/CLAUDE.md.snippet` to the project's `CLAUDE.md`.

If you renamed the vault or moved it, update all `obsidian/` paths in the snippet.

### Step 7: Verify

- Start a new session in your AI assistant
- The assistant should mention the wiki index in its first response
- Try saying "remember this" to create a test wiki page

---

## Usage

### In Chat

| Command | What happens |
|---------|-------------|
| "ingest" / "create wiki from daily" | Assistant reads `daily/` and `raw/`, creates wiki pages manually |
| "remember this" / "note this" | Assistant creates a wiki page from current conversation |
| "lint the wiki" | Runs health checks on the wiki |

### Via CLI

```bash
cd ~/WIKI/my-project/compiler

uv run python scripts/compile.py                # compile all unprocessed sources
uv run python scripts/compile.py --source raw   # only raw/
uv run python scripts/compile.py --source daily # only daily/
uv run python scripts/compile.py --dry-run      # preview without writing

uv run python scripts/lint.py                   # health check
uv run python scripts/lint.py --structural-only # free, no LLM

uv run python scripts/query.py "How does auth work?"  # search the wiki
```

---

## Wiki Folders

Only **two** folders (same model as [coleam00/claude-memory-compiler](https://github.com/coleam00/claude-memory-compiler)):

| Folder | When to use |
|--------|-------------|
| `wiki/concepts/` | Single-topic pages: patterns, bugs, features, how things work, ops commands, glossary |
| `wiki/connections/` | Pages whose main value is linking multiple topics: workflows, design rationale, ADRs |

**When in doubt, use `concepts/`.** Only use `connections/` when the page explicitly ties 2+ separate topics together.

---

## Hooks

| Hook | When | What it does |
|------|------|-------------|
| `sessionStart` | Session starts | Reads `index.md` + recent daily log → injects into context |
| `sessionEnd` | Session ends | Extracts conversation → spawns `flush.py` → daily log |
| `preCompact` | Before context compaction | Saves context before it's lost to summarization |

**`flush.py`** (background, no user interaction):
1. Extracts key knowledge from conversation via DeepSeek or Claude
2. Appends to `daily/YYYY-MM-DD.md`
3. If after 18:00 and compilation is enabled (Option B): spawns `compile.py`

---

## Optional: Obsidian

Point an Obsidian vault at your `obsidian/` directory for graph view, backlinks, and search.

---

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Optional: DeepSeek API key (for automatic flush/compile)
- Optional: Claude Code subscription (for Claude-based flush/compile)
- Optional: [Obsidian](https://obsidian.md) for browsing the wiki

## Credits

- [Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — original method
- [coleam00/claude-memory-compiler](https://github.com/coleam00/claude-memory-compiler) — two-folder wiki layout
