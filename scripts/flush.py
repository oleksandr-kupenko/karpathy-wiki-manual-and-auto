"""
Memory flush agent - extracts important knowledge from conversation context.

Spawned by session-end.py, pre-compact.py, or the OpenCode plugin as a background
process. Reads pre-extracted conversation context from a .md file, uses an LLM
to decide what's worth saving, and appends the result to today's daily log.

Provider logic:
  1. If flush-config.json sets "flush_provider": "claude" → Claude Agent SDK
  2. Else if DEEPSEEK_API_KEY is set (in env or .env) → DeepSeek API (cheap)
  3. Else → Claude Agent SDK (fallback, uses Anthropic subscription)

Usage:
    uv run python flush.py <context_file.md> <session_id> [agent]

agent: optional identifier for the source AI tool, e.g. "claude", "cursor_ai",
       "opencode". When provided, the daily log is written to
       YYYY-MM-DD_<agent>.md instead of YYYY-MM-DD.md.
"""

from __future__ import annotations

import os
os.environ["CLAUDE_INVOKED_BY"] = "memory_flush"

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
STATE_FILE = SCRIPTS_DIR / "last-flush.json"
LOG_FILE = SCRIPTS_DIR / "flush.log"
FLUSH_CONFIG_FILE = ROOT / "flush-config.json"
ENV_FILE = ROOT / ".env"

sys.path.insert(0, str(SCRIPTS_DIR))
from config import DAILY_DIR

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def load_env() -> None:
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


def resolve_provider() -> str:
    cfg_provider = "auto"
    if FLUSH_CONFIG_FILE.exists():
        try:
            cfg = json.loads(FLUSH_CONFIG_FILE.read_text(encoding="utf-8"))
            cfg_provider = cfg.get("flush_provider", "auto")
        except (json.JSONDecodeError, OSError):
            pass

    if cfg_provider == "claude":
        return "claude"
    if cfg_provider == "deepseek":
        return "deepseek"

    load_env()
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek"
    return "claude"


def load_flush_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_flush_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state), encoding="utf-8")


def append_to_daily_log(content: str, section: str = "Session", agent: str | None = None) -> None:
    today = datetime.now(timezone.utc).astimezone()
    date_str = today.strftime("%Y-%m-%d")
    filename = f"{date_str}_{agent}.md" if agent else f"{date_str}.md"
    log_path = DAILY_DIR / filename

    if not log_path.exists():
        DAILY_DIR.mkdir(parents=True, exist_ok=True)
        agent_label = f" [{agent}]" if agent else ""
        log_path.write_text(
            f"# Daily Log: {date_str}{agent_label}\n\n## Sessions\n\n## Memory Maintenance\n\n",
            encoding="utf-8",
        )

    time_str = today.strftime("%H:%M")
    entry = f"### {section} ({time_str})\n\n{content}\n\n"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)


FLUSH_PROMPT = """Review the conversation context below and respond with a concise summary
of important items that should be preserved in the daily log.
Do NOT use any tools — just return plain text.

Format your response as a structured daily log entry with these sections:

**Context:** [One line about what the user was working on]

**Key Exchanges:**
- [Important Q&A or discussions]

**Decisions Made:**
- [Any decisions with rationale]

**Lessons Learned:**
- [Gotchas, patterns, or insights discovered]

**Action Items:**
- [Follow-ups or TODOs mentioned]

Skip anything that is:
- Routine tool calls or file reads
- Content that's trivial or obvious
- Trivial back-and-forth or clarification exchanges

Only include sections that have actual content. If nothing is worth saving,
respond with exactly: FLUSH_OK

## Conversation Context

{context}"""


async def run_flush_deepseek(context: str) -> str:
    from openai import OpenAI

    load_env()
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return "FLUSH_ERROR: DEEPSEEK_API_KEY not set (check .env)"

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": FLUSH_PROMPT.format(context=context)}],
            temperature=0.3,
            max_tokens=2000,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        import traceback
        logging.error("DeepSeek API error: %s\n%s", e, traceback.format_exc())
        return f"FLUSH_ERROR: {type(e).__name__}: {e}"


async def run_flush_claude(context: str) -> str:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        query,
    )

    response = ""

    try:
        async for message in query(
            prompt=FLUSH_PROMPT.format(context=context),
            options=ClaudeAgentOptions(
                cwd=str(ROOT),
                allowed_tools=[],
                max_turns=2,
            ),
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response += block.text
            elif isinstance(message, ResultMessage):
                pass
    except Exception as e:
        import traceback
        logging.error("Claude Agent SDK error: %s\n%s", e, traceback.format_exc())
        response = f"FLUSH_ERROR: {type(e).__name__}: {e}"

    return response


async def run_flush(context: str) -> str:
    provider = resolve_provider()
    logging.info("Using flush provider: %s", provider)

    if provider == "deepseek":
        return await run_flush_deepseek(context)
    return await run_flush_claude(context)


COMPILE_AFTER_HOUR = 18


def maybe_trigger_compilation() -> None:
    import subprocess as _sp

    now = datetime.now(timezone.utc).astimezone()
    if now.hour < COMPILE_AFTER_HOUR:
        return

    date_str = now.strftime("%Y-%m-%d")
    # All daily files for today: YYYY-MM-DD.md, YYYY-MM-DD_claude.md, etc.
    today_logs = list(DAILY_DIR.glob(f"{date_str}*.md")) if DAILY_DIR.exists() else []

    compile_state_file = SCRIPTS_DIR / "state.json"
    if compile_state_file.exists() and today_logs:
        try:
            from hashlib import sha256
            compile_state = json.loads(compile_state_file.read_text(encoding="utf-8"))
            ingested = compile_state.get("ingested", {})
            # If ALL today's logs are already ingested with unchanged hashes → skip
            all_ingested = all(
                log_path.name in ingested
                and ingested[log_path.name].get("hash")
                == sha256(log_path.read_bytes()).hexdigest()[:16]
                for log_path in today_logs
            )
            if all_ingested:
                return
        except (json.JSONDecodeError, OSError):
            pass

    compile_script = SCRIPTS_DIR / "compile.py"
    if not compile_script.exists():
        return

    logging.info("End-of-day compilation triggered (after %d:00)", COMPILE_AFTER_HOUR)

    cmd = ["uv", "run", "--directory", str(ROOT), "python", str(compile_script)]

    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = _sp.CREATE_NEW_PROCESS_GROUP | _sp.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True

    try:
        log_handle = open(str(SCRIPTS_DIR / "compile.log"), "a")
        _sp.Popen(cmd, stdout=log_handle, stderr=_sp.STDOUT, cwd=str(ROOT), **kwargs)
    except Exception as e:
        logging.error("Failed to spawn compile.py: %s", e)


def main():
    if len(sys.argv) < 3:
        logging.error("Usage: %s <context_file.md> <session_id> [agent]", sys.argv[0])
        sys.exit(1)

    context_file = Path(sys.argv[1])
    session_id = sys.argv[2]
    agent = sys.argv[3] if len(sys.argv) > 3 else None

    logging.info("flush.py started for session %s, agent=%s, context: %s", session_id, agent, context_file)

    if not context_file.exists():
        logging.error("Context file not found: %s", context_file)
        return

    state = load_flush_state()
    if (
        state.get("session_id") == session_id
        and time.time() - state.get("timestamp", 0) < 60
    ):
        logging.info("Skipping duplicate flush for session %s", session_id)
        context_file.unlink(missing_ok=True)
        return

    context = context_file.read_text(encoding="utf-8").strip()
    if not context:
        logging.info("Context file is empty, skipping")
        context_file.unlink(missing_ok=True)
        return

    logging.info("Flushing session %s: %d chars", session_id, len(context))

    response = asyncio.run(run_flush(context))

    if "FLUSH_OK" in response:
        logging.info("Result: FLUSH_OK")
        append_to_daily_log(
            "FLUSH_OK - Nothing worth saving from this session", "Memory Flush", agent
        )
    elif "FLUSH_ERROR" in response:
        logging.error("Result: %s", response)
        append_to_daily_log(response, "Memory Flush", agent)
    else:
        logging.info("Result: saved to daily log (%d chars)", len(response))
        append_to_daily_log(response, "Session", agent)

    save_flush_state({"session_id": session_id, "timestamp": time.time()})

    context_file.unlink(missing_ok=True)

    maybe_trigger_compilation()

    logging.info("Flush complete for session %s", session_id)


if __name__ == "__main__":
    main()
