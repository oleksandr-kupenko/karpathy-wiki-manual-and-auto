"""Path constants and configuration for the unified knowledge base.

Set WIKI_VAULT_DIR env var to override the vault directory name.
Default: looks for a sibling directory named '*-obsidian' or falls back
to the WIKI_VAULT_DIR name set at install time.
"""

import os
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).resolve().parent.parent

PROJECT_DIR = ROOT_DIR.parent

VAULT_DIR = Path(os.environ.get(
    "WIKI_VAULT_PATH",
    str(PROJECT_DIR / os.environ.get("WIKI_VAULT_DIR", "obsidian-vault")),
))

DAILY_DIR = VAULT_DIR / "daily"
RAW_DIR = VAULT_DIR / "raw"
WIKI_DIR = VAULT_DIR / "wiki"
SCRIPTS_DIR = ROOT_DIR / "scripts"
HOOKS_DIR = ROOT_DIR / "hooks"
REPORTS_DIR = ROOT_DIR / "reports"
AGENTS_FILE = ROOT_DIR / "AGENTS.md"
WIKI_SCHEMA_FILE = VAULT_DIR / "wiki-schema.md"

INDEX_FILE = VAULT_DIR / "index.md"
LOG_FILE = VAULT_DIR / "log.md"
STATE_FILE = SCRIPTS_DIR / "state.json"

WIKI_SUBDIRS = [
    "concepts",
    "decisions",
    "connections",
]

TIMEZONE = os.environ.get("WIKI_TIMEZONE", "Europe/Kyiv")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def today_iso() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
