"""
SessionStart hook - injects knowledge base context into every conversation.

This is the "context injection" layer. When Claude Code starts a session,
this hook reads the knowledge base index and recent daily log, then injects
them as additional context so Claude always "remembers" what it has learned.

Configure in .claude/settings.json:
{
    "hooks": {
        "SessionStart": [{
            "matcher": "",
            "command": "uv run --directory andrej-karpathy-llm-memory python hooks/session-start.py"
        }]
    }
}
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
from config import DAILY_DIR, INDEX_FILE

MAX_CONTEXT_CHARS = 20_000
MAX_LOG_LINES = 30


def get_recent_log() -> str:
    today = datetime.now(timezone.utc).astimezone()

    for offset in range(2):
        date = today - timedelta(days=offset)
        date_str = date.strftime("%Y-%m-%d")
        # Collect all daily files for this date: YYYY-MM-DD.md, YYYY-MM-DD_claude.md, etc.
        log_files = sorted(DAILY_DIR.glob(f"{date_str}*.md")) if DAILY_DIR.exists() else []
        if log_files:
            all_lines: list[str] = []
            for log_path in log_files:
                all_lines.extend(log_path.read_text(encoding="utf-8").splitlines())
            recent = all_lines[-MAX_LOG_LINES:] if len(all_lines) > MAX_LOG_LINES else all_lines
            return "\n".join(recent)

    return "(no recent daily log)"


def build_context() -> str:
    parts = []

    today = datetime.now(timezone.utc).astimezone()
    parts.append(f"## Today\n{today.strftime('%A, %B %d, %Y')}")

    if INDEX_FILE.exists():
        wiki_index = INDEX_FILE.read_text(encoding="utf-8")
        parts.append(f"## Project Wiki\n\n{wiki_index}")

    recent_log = get_recent_log()
    parts.append(f"## Recent Daily Log\n\n{recent_log}")

    context = "\n\n---\n\n".join(parts)

    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n...(truncated)"

    return context


def main():
    context = build_context()

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
