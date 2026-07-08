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

When a user asks to "set up karpathy-wiki for my project", run **Phase 1 first** — ask all questions and collect answers before touching any files. Only then proceed to Phase 2.

---

### Phase 1: Interview

Ask all five questions in one message. Wait for answers. Do not assume defaults silently — if the user skips a question, ask again for that specific one before proceeding.

---

**Q1 — Wiki location**

> Where should the wiki live? It will be a folder **outside** your project repo.
> Default: `~/WIKI/<project-name>/`
>
> It will contain two subdirectories: `compiler/` (scripts) and a vault folder (the knowledge base).

---

**Q2 — Vault folder name**

> What should the vault folder be named? Default: `obsidian`
>
> This name becomes the Obsidian vault name. **Important:** if you later rename the vault inside Obsidian, it renames the actual folder on disk — not just an alias. You can always fix this by updating `WIKI_VAULT_DIR` in `compiler/.env`.

---

**Q3 — AI assistant(s)**

> Which AI assistant(s) do you use in this project? (Pick one or more)
>
> - **Claude Code** — hooks via `.claude/settings.json` + skill file
> - **OpenCode** — hooks via TypeScript plugin (`.opencode/`)
> - **Cursor AI** — hooks via `.cursor/hooks.json` (requires Cursor 1.7+)

---

**Q4 — Session flush method**

> At the end of each session, the wiki system saves what happened. How should it extract knowledge from the conversation?
>
> **A — DeepSeek API** (~$0.01/session): Fast and cheap. Requires a DeepSeek API key from [platform.deepseek.com](https://platform.deepseek.com/).
>
> **B — Claude via Agent SDK** (free with Claude Max subscription): Uses your existing subscription. Spawns a background Haiku agent. Slightly slower than DeepSeek.
>
> **C — Raw transcript only** (free, no API): Saves the conversation transcript as-is, without summarizing. Knowledge is extracted later when you manually run "ingest". Good if you want full control or don't have API access.

---

**Q5 — Automatic wiki compilation**

> After sessions are flushed to daily logs, should the system automatically compile wiki pages?
>
> - **Yes — auto-compile after 18:00** (requires Q4 = A or B): At end of day, `compile.py` runs automatically and generates wiki pages from that day's logs.
> - **No — manual only** (default): You trigger wiki compilation yourself by saying "ingest" or "create wiki from daily".
>
> Note: if Q4 = C (raw only), auto-compile is not available.

---

### Phase 2: Execute

Once you have all answers, run the following steps in order.

#### Step 1: Clone and install

```bash
WIKI_BASE="<answer to Q1>"
VAULT_NAME="<answer to Q2, default: obsidian>"

mkdir -p "$WIKI_BASE"
git clone https://github.com/oleksandr-kupenko/karpathy-wiki-manual-and-auto.git "$WIKI_BASE/compiler"
cp -r "$WIKI_BASE/compiler/templates/vault" "$WIKI_BASE/$VAULT_NAME"
cd "$WIKI_BASE/compiler" && uv sync
```

#### Step 2: Configure `.env`

Create `$WIKI_BASE/compiler/.env`:

```bash
# Always set if vault name != obsidian:
WIKI_VAULT_DIR=<VAULT_NAME>

# Q4 = A (DeepSeek):
DEEPSEEK_API_KEY=sk-your-key-here

# Q4 = B (Claude Agent SDK): no extra key needed — uses Claude Code subscription
# Q4 = C (raw only): no keys needed
```

#### Step 3: Configure flush provider

Create `$WIKI_BASE/compiler/flush-config.json` based on Q4:

| Q4 answer | flush-config.json |
|-----------|-------------------|
| A — DeepSeek | `{"provider": "deepseek"}` |
| B — Claude Agent SDK | `{"provider": "claude"}` |
| C — Raw only | `{"provider": "none"}` |

#### Step 4: Configure auto-compile

Create `$WIKI_BASE/compiler/compile-config.json` based on Q5:

| Q5 answer | compile-config.json |
|-----------|---------------------|
| Yes — auto after 18:00 | `{"provider": "opencode", "auto_compile": true}` |
| No — manual only | `{"auto_compile": false}` |

#### Step 5: Install assistant templates

Use paths from Q1 and Q3. Replace `$PROJECT_DIR` with the actual project path.

```bash
PROJECT_DIR="/path/to/your/project"
WIKI_BASE="<Q1 answer>"
```

**Claude Code** (if selected in Q3):
```bash
mkdir -p "$PROJECT_DIR/.claude/skills/wiki-ingest"
cp "$WIKI_BASE/compiler/templates/.claude/settings.json" "$PROJECT_DIR/.claude/settings.json"
cp "$WIKI_BASE/compiler/templates/.claude/skills/wiki-ingest/SKILL.md" "$PROJECT_DIR/.claude/skills/wiki-ingest/SKILL.md"
```
> If `.claude/settings.json` already exists — merge the `"hooks"` key manually, do not overwrite.

**OpenCode** (if selected in Q3):
```bash
cp -r "$WIKI_BASE/compiler/templates/.opencode" "$PROJECT_DIR/.opencode"
cp "$WIKI_BASE/compiler/templates/opencode.json" "$PROJECT_DIR/opencode.json"
cd "$PROJECT_DIR/.opencode" && npm install
```

**Cursor AI** (if selected in Q3):
```bash
mkdir -p "$PROJECT_DIR/.cursor"
cp "$WIKI_BASE/compiler/templates/cursor-hooks.json" "$PROJECT_DIR/.cursor/hooks.json"
```

#### Step 6: Update paths in templates

Replace all path placeholders in the copied files with actual absolute paths:

- `.claude/settings.json` — `uv run --directory ...` in hook commands → `$WIKI_BASE/compiler`
- `.claude/skills/wiki-ingest/SKILL.md` — vault path → `$WIKI_BASE/$VAULT_NAME`, compiler path → `$WIKI_BASE/compiler`
- `.opencode/plugins/memory-compiler.ts` — `compilerDir` and `vaultDir`
- `.cursor/hooks.json` — hook command paths
- `CLAUDE.md` snippet — vault path

#### Step 7: Add CLAUDE.md snippet

Append `$WIKI_BASE/compiler/templates/CLAUDE.md.snippet` to the project's `CLAUDE.md`. Update the vault path inside it.

> **Vault rename note:** If Obsidian renames your vault folder later, only one file needs updating: set `WIKI_VAULT_DIR=<new-name>` in `compiler/.env`.

#### Step 8: Verify

- Start a new session in your AI assistant
- The assistant should inject the wiki index in its first response
- Say "remember this" — the assistant should create a test wiki page

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
- Optional: DeepSeek API key (for automatic flush)
- Optional: Claude Code subscription (for Claude-based flush)
- Optional: [Obsidian](https://obsidian.md) for browsing the wiki

## Credits

- [Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — original method
- [coleam00/claude-memory-compiler](https://github.com/coleam00/claude-memory-compiler) — two-folder wiki layout
