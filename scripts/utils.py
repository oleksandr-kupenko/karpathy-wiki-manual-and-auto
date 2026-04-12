"""Shared utilities for the unified knowledge base."""

import hashlib
import json
import re
from pathlib import Path

from config import (
    DAILY_DIR,
    INDEX_FILE,
    RAW_DIR,
    STATE_FILE,
    WIKI_DIR,
    WIKI_SUBDIRS,
)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"ingested": {}, "total_cost": 0.0}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def extract_wikilinks(content: str) -> list[str]:
    return re.findall(r"\[\[([^\]]+)\]\]", content)


def wiki_page_exists(link: str) -> bool:
    for subdir in WIKI_SUBDIRS:
        path = WIKI_DIR / subdir / f"{link}.md"
        if path.exists():
            return True
    return (WIKI_DIR / f"{link}.md").exists()


def read_wiki_index() -> str:
    if INDEX_FILE.exists():
        return INDEX_FILE.read_text(encoding="utf-8")
    return ""


def list_wiki_pages() -> list[Path]:
    pages = []
    for subdir in WIKI_SUBDIRS:
        d = WIKI_DIR / subdir
        if d.exists():
            pages.extend(sorted(d.glob("*.md")))
    return pages


def list_source_files(source_type: str = "all") -> list[Path]:
    """List source files from daily/ and/or raw/.

    source_type: 'all', 'daily', 'raw'
    """
    files = []
    if source_type in ("all", "daily") and DAILY_DIR.exists():
        files.extend(sorted(DAILY_DIR.glob("*.md")))
    if source_type in ("all", "raw") and RAW_DIR.exists():
        files.extend(sorted(RAW_DIR.rglob("*.md")))
    return files


def count_inbound_links(target: str, exclude_file: Path | None = None) -> int:
    count = 0
    for article in list_wiki_pages():
        if article == exclude_file:
            continue
        content = article.read_text(encoding="utf-8")
        if f"[[{target}]]" in content:
            count += 1
    return count


def get_article_word_count(path: Path) -> int:
    content = path.read_text(encoding="utf-8")
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3:]
    return len(content.split())
