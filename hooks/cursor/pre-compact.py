"""
preCompact hook for Cursor AI - saves conversation before context compression.

When Cursor's context window fills up, it compacts (summarizes and discards detail).
This hook fires BEFORE that happens, extracting conversation context and spawning
flush.py to extract knowledge that would otherwise be lost.

The hook itself does NO API calls — only local file I/O for speed (<10s).

Configure in .cursor/hooks.json:
{
    "version": 1,
    "hooks": {
        "preCompact": [{
            "command": "uv run --directory karpathy-wiki-manual-and-auto python hooks/cursor/pre-compact.py",
            "timeout": 10
        }]
    }
}

stdin payload (from Cursor):
{
    "hook_event_name": "preCompact",
    "session_id": "<id>",
    "transcript_path": "<path or null>",
    "trigger": "auto",
    "context_usage_percent": 85,
    "context_tokens": 120000,
    "context_window_size": 128000,
    "message_count": 45,
    "messages_to_compact": 30,
    "is_first_compaction": true
}

Output (stdout):
{
    "user_message": "<optional message shown when compaction runs>"
}
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# hooks/cursor/pre-compact.py → hooks/cursor/ → hooks/ → karpathy-wiki-manual-and-auto/
ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = ROOT / "scripts"
STATE_DIR = SCRIPTS_DIR

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(ROOT / "hooks"))
from config import DAILY_DIR
from transcript import extract_conversation_context  # noqa: F401

logging.basicConfig(
    filename=str(SCRIPTS_DIR / "flush.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [cursor/pre-compact] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

MAX_TURNS = 30
MAX_CONTEXT_CHARS = 15_000
MIN_TURNS_TO_FLUSH = 5




def main() -> None:
    try:
        hook_input: dict = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError, EOFError) as e:
        logging.error("Failed to parse stdin: %s", e)
        return

    session_id = hook_input.get("session_id", "unknown")
    transcript_path_str = hook_input.get("transcript_path", "")
    context_pct = hook_input.get("context_usage_percent", "?")

    logging.info("preCompact fired: session=%s context_usage=%s%%", session_id, context_pct)

    if not transcript_path_str or not isinstance(transcript_path_str, str):
        logging.info("SKIP: no transcript path")
        return

    transcript_path = Path(transcript_path_str)
    if not transcript_path.exists():
        logging.info("SKIP: transcript missing: %s", transcript_path_str)
        return

    try:
        context, turn_count = extract_conversation_context(
            transcript_path,
            max_turns=MAX_TURNS,
            max_context_chars=MAX_CONTEXT_CHARS,
        )
    except Exception as e:
        logging.error("Context extraction failed: %s", e)
        return

    if not context.strip():
        logging.info("SKIP: empty context")
        return

    if turn_count < MIN_TURNS_TO_FLUSH:
        logging.info("SKIP: only %d turns (min %d)", turn_count, MIN_TURNS_TO_FLUSH)
        return

    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    context_file = STATE_DIR / f"cursor-flush-context-{session_id}-{timestamp}.md"
    context_file.write_text(context, encoding="utf-8")

    flush_script = SCRIPTS_DIR / "flush.py"
    cmd = [
        "uv", "run", "--directory", str(ROOT),
        "python", str(flush_script),
        str(context_file), session_id, "cursor_ai",
    ]

    creation_flags = __import__("subprocess").CREATE_NO_WINDOW if sys.platform == "win32" else 0

    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        logging.info(
            "Spawned flush.py for session %s (%d turns, %d chars)",
            session_id, turn_count, len(context),
        )
    except Exception as e:
        logging.error("Failed to spawn flush.py: %s", e)

    # Optional: show a message to the user when compaction runs
    print(json.dumps({"user_message": "Knowledge saved to wiki before compaction."}))


if __name__ == "__main__":
    main()
