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
    uv run python compile.py --provider <name>   # override provider (opencode/deepseek)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess as sp
import sys
from pathlib import Path

from config import (
    DAILY_DIR,
    INDEX_FILE,
    LOG_FILE,
    RAW_DIR,
    WIKI_DIR,
    WIKI_SCHEMA_FILE,
    VAULT_DIR,
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
CONFIG_FILE = ROOT_DIR / "compile-config.json"
ENV_FILE = ROOT_DIR / ".env"

WIKI_FOLDER_DESCRIPTIONS = """\
| Folder | When to use |
|--------|-------------|
| `wiki/concepts/` | Atomic pages: facts, patterns, how things work — bugs, features, system design notes, domain knowledge, ops, ADRs that fit one topic |
| `wiki/connections/` | Cross-cutting articles: how multiple topics relate, workflows, design rationale spanning systems (same two-folder model as [coleam00/claude-memory-compiler](https://github.com/coleam00/claude-memory-compiler)) |
"""


def load_env() -> None:
    """Load environment variables from .env file."""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


def load_compile_provider() -> str:
    """Load the LLM provider from config file."""
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return cfg.get("provider", "opencode")
        except (json.JSONDecodeError, OSError):
            pass
    return "opencode"


def source_type_label(path: Path) -> str:
    if path.is_relative_to(DAILY_DIR):
        return "daily"
    if path.is_relative_to(RAW_DIR):
        return "raw"
    return "unknown"


async def compile_source_opencode(source_path: Path, state: dict) -> float:
    """Compile using opencode run command."""
    source_hash = file_hash(source_path)
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

    prompt = f"""Compile the source file below into wiki pages.

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

```
{source_content[:15000]}
```

## Task
Read the source above and compile it into wiki pages.

### Rules:
1. Classify each piece of knowledge into the correct subfolder.
2. Create wiki pages — one .md file per topic. Each page MUST have YAML frontmatter: `title`, `tags`, `date`, `sources`, `related` (using [[wikilinks]]).
3. Update existing pages if new sources add information to topics already covered.
4. Prefer `wiki/concepts/` for single-topic pages; use `wiki/connections/` when the source mainly links multiple areas.
5. Update `index.md` — add new pages to the correct table, update counts.
6. Append to `log.md`.

### File paths:
- Write wiki pages to subfolders of: {WIKI_DIR}
- Update index at: {INDEX_FILE}
- Append log at: {LOG_FILE}

Run the wiki ingest now. Respond with DONE when complete."""

    opencode_cmd = os.environ.get("OPENCODE_BIN", "/home/san/.opencode/bin/opencode")
    vault_dir = str(VAULT_DIR)
    instructions_file = VAULT_DIR / "COMPILE_INSTRUCTIONS.md"
    instructions = instructions_file.read_text() if instructions_file.exists() else ""

    full_prompt = f"""{prompt}

## Instructions
{instructions}

Now execute."""

    proc = sp.Popen(
        [opencode_cmd, "run", full_prompt, "--dir", vault_dir, "--title", f"compile: {source_path.name}", "--dangerously-skip-permissions", "--print-logs"],
        stdout=sp.PIPE,
        stderr=sp.PIPE,
        text=True,
    )

    try:
        stdout, stderr = proc.communicate(timeout=180)
        if proc.returncode != 0:
            print(f"  Error: {stderr}")
            return 0.0
        print(f"  Output: {stdout[:500]}")
    except sp.TimeoutExpired:
        proc.kill()
        print("  Timeout")
        return 0.0

    cost = 0.0

    rel_path = source_path.name if src_type == "daily" else str(source_path.relative_to(RAW_DIR))
    state_key = f"{src_type}/{rel_path}"
    state.setdefault("ingested", {})[state_key] = {
        "hash": source_hash,
        "type": src_type,
        "compiled_at": now_iso(),
        "cost_usd": cost,
    }
    state["total_cost"] = state.get("total_cost", 0.0) + cost
    save_state(state)

    return cost


async def compile_source_deepseek(source_path: Path, state: dict) -> float:
    """Compile using DeepSeek API."""
    from openai import OpenAI

    source_hash = file_hash(source_path)
    source_content = source_path.read_text(encoding="utf-8")
    schema = WIKI_SCHEMA_FILE.read_text(encoding="utf-8")
    wiki_index = read_wiki_index()

    src_type = source_type_label(source_path)
    if src_type == "daily":
        src_rel = f"daily/{source_path.name}"
    else:
        src_rel = f"raw/{source_path.relative_to(RAW_DIR)}"

    prompt = f"""You are a knowledge compiler. Create wiki pages from the source below.

## Wiki Schema
{schema}

## Wiki Folder Guide
{WIKI_FOLDER_DESCRIPTIONS}

## Current Wiki Index
{wiki_index}

## Source to Compile
**File:** {src_rel}
**Type:** {src_type}

{source_content[:12000]}

## Task
Create wiki pages. Output format per page:
```
---
title: Page Title
tags: [tag1, tag2]
date: YYYY-MM-DD
sources:
  - {src_rel}
related:
  - [[other-page]]
---
Page content here.
```

Write to {WIKI_DIR} subfolders. Update {INDEX_FILE} and {LOG_FILE}."""

    load_env()
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("  Error: DEEPSEEK_API_KEY not set")
        return 0.0

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=8000,
        )
        content = resp.choices[0].message.content or ""
    except Exception as e:
        print(f"  Error: {e}")
        return 0.0

    cost = 0.0

    rel_path = source_path.name if src_type == "daily" else str(source_path.relative_to(RAW_DIR))
    state_key = f"{src_type}/{rel_path}"
    state.setdefault("ingested", {})[state_key] = {
        "hash": source_hash,
        "type": src_type,
        "compiled_at": now_iso(),
        "cost_usd": cost,
    }
    state["total_cost"] = state.get("total_cost", 0.0) + cost
    save_state(state)

    return cost


async def compile_source(source_path: Path, state: dict, provider: str) -> float:
    """Compile a single source using the specified provider."""
    if provider == "opencode":
        return await compile_source_opencode(source_path, state)
    elif provider == "deepseek":
        return await compile_source_deepseek(source_path, state)
    else:
        print(f"  Unknown provider: {provider}")
        return 0.0


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
    parser.add_argument(
        "--source",
        choices=["daily", "raw", "all"],
        default="all",
        help="Source type to process",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be compiled")
    parser.add_argument("--cleanup", action="store_true", help="Delete processed daily/ files and exit")
    parser.add_argument(
        "--provider",
        choices=["opencode", "deepseek"],
        help="Override provider (default: from compile-config.json)",
    )
    args = parser.parse_args()

    load_env()
    provider = args.provider or load_compile_provider()
    state = load_state()

    if args.cleanup:
        cleanup_processed_daily(state)
        return

    if args.file:
        target = Path(args.file)
        if not target.is_absolute():
            for base in [DAILY_DIR, RAW_DIR, VAULT_DIR]:
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
        print(
            f"  - {source_type_label(f)}/{f.name if f.is_relative_to(DAILY_DIR) or f.is_relative_to(RAW_DIR) else f}"
        )

    if args.dry_run:
        return

    if provider == "opencode":
        print("\n=== AUTO RUN via opencode ===")
        print(f"Running compile via opencode...")
        total_cost = 0.0
        for i, src_path in enumerate(to_compile, 1):
            print(f"\n[{i}/{len(to_compile)}] Compiling {src_path.name}...")
            cost = asyncio.run(compile_source(src_path, state, provider))
            total_cost += cost
            print(f"  Done.")
        pages = list_wiki_pages()
        print(f"\nCompilation complete.")
        print(f"Wiki: {len(pages)} pages")
        cleanup_processed_daily(state)
        return

    total_cost = 0.0
    for i, src_path in enumerate(to_compile, 1):
        print(f"\n[{i}/{len(to_compile)}] Compiling {src_path.name} (provider: {provider})...")
        cost = asyncio.run(compile_source(src_path, state, provider))
        total_cost += cost
        print(f"  Done.")

    pages = list_wiki_pages()
    print(f"\nCompilation complete. Total cost: ${total_cost:.2f}")
    print(f"Wiki: {len(pages)} pages")

    cleanup_processed_daily(state)


if __name__ == "__main__":
    main()