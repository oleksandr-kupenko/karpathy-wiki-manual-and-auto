"""
sessionEnd hook for Cursor AI - captures conversation for memory extraction.

When a Cursor session ends, this hook reads transcript_path from the JSON
payload on stdin, extracts conversation context, and spawns flush.py as a
background process to extract knowledge into the daily log.

The hook itself does NO API calls — only local file I/O for speed (<10s).

Configure in .cursor/hooks.json:
{
    "version": 1,
    "hooks": {
        "sessionEnd": [{
            "command": "uv run --directory karpathy-wiki-manual-and-auto python hooks/cursor/session-end.py",
            "timeout": 10
        }]
    }
}

stdin payload (from Cursor):
{
    "hook_event_name": "sessionEnd",
    "session_id": "<id>",
    "transcript_path": "<path to JSONL transcript or null>",
    "reason": "completed",
    "workspace_roots": ["<path>"]
}

Output: fire-and-forget (Cursor logs but doesn't use the response).
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# hooks/cursor/session-end.py → hooks/cursor/ → hooks/ → karpathy-wiki-manual-and-auto/
ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = ROOT / "scripts"
STATE_DIR = SCRIPTS_DIR

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(ROOT / "hooks"))
from config import DAILY_DIR
from transcript import extract_conversation_context  # noqa: F401 (imported for side-effect: ensures config is loaded)

logging.basicConfig(
    filename=str(SCRIPTS_DIR / "flush.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [cursor/session-end] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

MAX_TURNS = 30
MAX_CONTEXT_CHARS = 15_000
MIN_TURNS_TO_FLUSH = 1




def main() -> None:
    try:
        hook_input: dict = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError, EOFError) as e:
        logging.error("Failed to parse stdin: %s", e)
        return

    session_id = hook_input.get("session_id", "unknown")
    transcript_path_str = hook_input.get("transcript_path", "")

    logging.info("sessionEnd fired: session=%s", session_id)

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
    context_file = STATE_DIR / f"cursor-session-flush-{session_id}-{timestamp}.md"
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


if __name__ == "__main__":
    main()
