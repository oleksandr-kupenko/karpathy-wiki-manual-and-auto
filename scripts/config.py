"""Path constants and configuration for the unified knowledge base.

Vault location is resolved, first match wins:
  1. WIKI_VAULT_PATH  — absolute path to the vault directory
  2. WIKI_VAULT_DIR   — vault directory name (relative to the compiler parent)
  3. "obsidian"       — default

Values are read from the environment and from the compiler's .env file, which is
loaded on import so overrides take effect for every entry point (hooks and
scripts). Existing environment variables always win (override=False).
"""

import os
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent

load_dotenv(ROOT_DIR / ".env")

PROJECT_DIR = ROOT_DIR.parent

VAULT_DIR = Path(os.environ.get(
    "WIKI_VAULT_PATH",
    str(PROJECT_DIR / os.environ.get("WIKI_VAULT_DIR", "obsidian")),
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
    "connections",
]

TIMEZONE = os.environ.get("WIKI_TIMEZONE", "Europe/Kyiv")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def today_iso() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
