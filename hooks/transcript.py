"""
Shared JSONL transcript parser for Claude Code and Cursor hooks.

Supported line formats:
  - Cursor:  {"role": "user", "message": {"content": [...]}}
  - Claude:  {"type": "user", "message": {"role": "user", "content": "..."}}
  - Claude:  {"type": "assistant", "message": {"role": "assistant", "content": [...]}}
  - Flat:    {"role": "user", "content": "..."}
  - Nested:  {"message": {"role": "assistant", "content": "..."}}

OpenCode uses its own TypeScript plugin (memory-compiler.ts) and does not use this module.
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_MAX_TURNS = 30
DEFAULT_MAX_CONTEXT_CHARS = 15_000


def _resolve_role(entry: dict, msg: dict) -> str:
    role = entry.get("role") or msg.get("role", "")
    if role in ("user", "assistant"):
        return role
    entry_type = entry.get("type", "")
    if entry_type in ("user", "assistant"):
        return entry_type
    return ""


def _extract_text(content: object) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text)
            elif isinstance(block, str) and block.strip():
                text_parts.append(block)
        return "\n".join(text_parts)

    return ""


def extract_conversation_context(
    transcript_path: Path,
    *,
    max_turns: int = DEFAULT_MAX_TURNS,
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> tuple[str, int]:
    turns: list[str] = []

    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                if line:
                    turns.append(f"**Assistant:** {line}\n")
                continue

            if not isinstance(entry, dict):
                continue

            msg = entry.get("message", {})
            if isinstance(msg, dict):
                role = _resolve_role(entry, msg)
                content = _extract_text(msg.get("content", entry.get("content", "")))
            else:
                role = _resolve_role(entry, {})
                content = _extract_text(entry.get("content", ""))

            if role not in ("user", "assistant"):
                continue

            if content.strip():
                label = "User" if role == "user" else "Assistant"
                turns.append(f"**{label}:** {content.strip()}\n")

    recent = turns[-max_turns:]
    context = "\n".join(recent)

    if len(context) > max_context_chars:
        context = context[-max_context_chars:]
        boundary = context.find("\n**")
        if boundary > 0:
            context = context[boundary + 1 :]

    return context, len(recent)
