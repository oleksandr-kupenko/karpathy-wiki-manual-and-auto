"""
Unified compiler — processes both daily/ and raw/ sources into wiki pages.

Usage:
    uv run python compile.py                    # compile new/changed sources
    uv run python compile.py --all              # force recompile everything
    uv run python compile.py --file <path>      # compile a specific file
    uv run python compile.py --source daily     # only daily/ sources
    uv run python compile.py --source raw       # only raw/ sources
    uv run python compile.py --dry-run          # show what would be compiled
    uv run python compile.py --cleanup          # delete processed daily/ files
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from config import (
    AGENTS_FILE,
    DAILY_DIR,
    INDEX_FILE,
    LOG_FILE,
    RAW_DIR,
    WIKI_DIR,
    WIKI_SCHEMA_FILE,
    now_iso,
)
from utils import (
    file_hash,
    list_source_files,
    list_wiki_pages,
    load_state,
    read_wiki_index,
    save_state,
)

ROOT_DIR = Path(__file__).resolve().parent.parent

WIKI_FOLDER_DESCRIPTIONS = """\
| Folder | When to use |
|--------|-------------|
| `wiki/concepts/` | Facts, patterns, how things work — bugs, features, architecture, domain knowledge, operations, anything concrete |
| `wiki/decisions/` | Why X over Y — architectural choices, trade-offs, design rationale |
| `wiki/connections/` | Non-obvious links between 2+ concepts across topics |
"""


def source_type_label(path: Path) -> str:
    if path.is_relative_to(DAILY_DIR):
        return "daily"
    if path.is_relative_to(RAW_DIR):
        return "raw"
    return "unknown"


async def compile_source(source_path: Path, state: dict) -> float:
    """Compile a single source (daily log or raw document) into wiki pages."""
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        query,
    )

    source_content = source_path.read_text(encoding="utf-8")
    schema = WIKI_SCHEMA_FILE.read_text(encoding="utf-8")
    wiki_index = read_wiki_index()

    existing_pages = {}
    for page_path in list_wiki_pages():
        rel = page_path.relative_to(WIKI_DIR)
        content = page_path.read_text(encoding="utf-8")
        truncated = content[:800] + "..." if len(content) > 800 else content
        existing_pages[str(rel)] = truncated

    existing_context = ""
    if existing_pages:
        parts = []
        for rel_path, content in existing_pages.items():
            parts.append(f"### {rel_path}\n```markdown\n{content}\n```")
        existing_context = "\n\n".join(parts)

    src_type = source_type_label(source_path)
    if src_type == "daily":
        src_rel = f"daily/{source_path.name}"
    else:
        src_rel = f"raw/{source_path.relative_to(RAW_DIR)}"

    timestamp = now_iso()

    prompt = f"""You are a knowledge compiler. Your job is to read a source document and create/update structured wiki pages.

## Wiki Schema

{schema}

## Wiki Folder Guide

{WIKI_FOLDER_DESCRIPTIONS}

## Current Wiki Index

{wiki_index}

## Existing Wiki Pages (truncated)

{existing_context if existing_context else "(No existing wiki pages yet)"}

## Source to Compile

**File:** {src_rel}
**Type:** {src_type}

{source_content[:15000]}

## Your Task

Read the source above and compile it into wiki pages.

### Rules:

1. **Classify** each piece of knowledge into the correct subfolder (see folder guide above).
2. **Create wiki pages** — one .md file per topic (NOT per source file). A single source may create multiple pages; multiple sources may merge into one page.
   - Each page MUST have YAML frontmatter: `title`, `tags`, `date`, `sources` (pointing to `{src_rel}`), `related` (using `[[wikilinks]]`)
   - Body is concise markdown — **summary, not copy** of the source
   - Target 30-80 lines per page
   - Use `[[wikilinks]]` for cross-references (filename without extension, without folder prefix)
3. **Update existing pages** if new sources add information to topics already covered.
   - Read the existing page, merge new info, add source to frontmatter, add `lastmod` field
4. **Create connection articles** in `wiki/connections/` if this source reveals non-obvious relationships between 2+ existing concepts
5. **Update the index file** ({INDEX_FILE.name}) — add new pages to the correct table, update counts.
6. **Append to the log file** ({LOG_FILE.name}) with format:
   `## [{timestamp}] compile | {source_path.name}` followed by Sources/Created/Updated lists.

### File paths:
- Write wiki pages to subfolders of: {WIKI_DIR}
- Update index at: {INDEX_FILE}
- Append log at: {LOG_FILE}

### Quality standards:
- Every page must have complete YAML frontmatter
- Every page must have at least 2 `[[wikilinks]]` in `related` field
- Keep pages concise — wiki pages are summaries, not copies
- Write in English unless the source is explicitly in another language
"""

    cost = 0.0

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                cwd=str(ROOT_DIR.parent),
                system_prompt={"type": "preset", "preset": "claude_code"},
                allowed_tools=["Read", "Write", "Edit", "Glob", "Grep"],
                permission_mode="acceptEdits",
                max_turns=30,
            ),
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        pass
            elif isinstance(message, ResultMessage):
                cost = message.total_cost_usd or 0.0
                print(f"  Cost: ${cost:.4f}")
    except Exception as e:
        print(f"  Error: {e}")
        return 0.0

    rel_path = source_path.name if src_type == "daily" else str(source_path.relative_to(RAW_DIR))
    state_key = f"{src_type}/{rel_path}"
    state.setdefault("ingested", {})[state_key] = {
        "hash": file_hash(source_path),
        "type": src_type,
        "compiled_at": now_iso(),
        "cost_usd": cost,
    }
    state["total_cost"] = state.get("total_cost", 0.0) + cost
    save_state(state)

    return cost


def cleanup_processed_daily(state: dict) -> None:
    """Delete daily/ files that have been successfully compiled."""
    ingested = state.get("ingested", {})
    deleted = []
    for key, info in list(ingested.items()):
        if info.get("type") != "daily":
            continue
        filename = key.split("/", 1)[1] if "/" in key else key
        daily_file = DAILY_DIR / filename
        if daily_file.exists():
            daily_file.unlink()
            deleted.append(filename)
    if deleted:
        print(f"Cleaned up {len(deleted)} processed daily files: {', '.join(deleted)}")


def main():
    parser = argparse.ArgumentParser(description="Compile sources into wiki pages")
    parser.add_argument("--all", action="store_true", help="Force recompile all sources")
    parser.add_argument("--file", type=str, help="Compile a specific file")
    parser.add_argument("--source", choices=["daily", "raw", "all"], default="all", help="Source type to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be compiled")
    parser.add_argument("--cleanup", action="store_true", help="Delete processed daily/ files and exit")
    args = parser.parse_args()

    state = load_state()

    if args.cleanup:
        cleanup_processed_daily(state)
        return

    if args.file:
        target = Path(args.file)
        if not target.is_absolute():
            for base in [DAILY_DIR, RAW_DIR, ROOT_DIR.parent]:
                candidate = base / args.file
                if candidate.exists():
                    target = candidate
                    break
        if not target.exists():
            print(f"Error: {args.file} not found")
            sys.exit(1)
        to_compile = [target]
    else:
        all_sources = list_source_files(args.source)
        if args.all:
            to_compile = all_sources
        else:
            to_compile = []
            for src_path in all_sources:
                src_type = source_type_label(src_path)
                if src_type == "daily":
                    rel = src_path.name
                else:
                    rel = str(src_path.relative_to(RAW_DIR))
                state_key = f"{src_type}/{rel}"
                prev = state.get("ingested", {}).get(state_key, {})
                if not prev or prev.get("hash") != file_hash(src_path):
                    to_compile.append(src_path)

    if not to_compile:
        print("Nothing to compile — all sources are up to date.")
        return

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Sources to compile ({len(to_compile)}):")
    for f in to_compile:
        print(f"  - {source_type_label(f)}/{f.name if f.is_relative_to(DAILY_DIR) or f.is_relative_to(RAW_DIR) else f}")

    if args.dry_run:
        return

    total_cost = 0.0
    for i, src_path in enumerate(to_compile, 1):
        print(f"\n[{i}/{len(to_compile)}] Compiling {src_path.name}...")
        cost = asyncio.run(compile_source(src_path, state))
        total_cost += cost
        print(f"  Done.")

    pages = list_wiki_pages()
    print(f"\nCompilation complete. Total cost: ${total_cost:.2f}")
    print(f"Wiki: {len(pages)} pages")

    cleanup_processed_daily(state)


if __name__ == "__main__":
    main()
