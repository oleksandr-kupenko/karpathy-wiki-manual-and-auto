"""
Query the knowledge base using index-guided retrieval (no RAG).

Usage:
    uv run python query.py "How should I handle auth redirects?"
    uv run python query.py "What patterns do I use for API design?" --file-back
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from config import INDEX_FILE, LOG_FILE, WIKI_DIR, now_iso
from utils import list_wiki_pages, load_state, read_wiki_index, save_state

ROOT_DIR = Path(__file__).resolve().parent.parent


def read_all_wiki_content() -> str:
    parts = [f"## INDEX\n\n{read_wiki_index()}"]
    for page in list_wiki_pages():
        rel = page.relative_to(WIKI_DIR)
        content = page.read_text(encoding="utf-8")
        parts.append(f"## {rel}\n\n{content}")
    return "\n\n---\n\n".join(parts)


async def run_query(question: str, file_back: bool = False) -> str:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        query,
    )

    wiki_content = read_all_wiki_content()

    tools = ["Read", "Glob", "Grep"]
    if file_back:
        tools.extend(["Write", "Edit"])

    file_back_instructions = ""
    if file_back:
        timestamp = now_iso()
        file_back_instructions = f"""

## File Back Instructions

After answering, create a wiki page in `wiki/concepts/` or `wiki/features/` (whichever is more appropriate) with the answer, then update `{INDEX_FILE.name}` and append to `{LOG_FILE.name}`.
"""

    prompt = f"""You are a knowledge base query engine. Answer the user's question by
consulting the knowledge base below.

## How to Answer

1. Read the INDEX section first - it lists every article with a one-line summary
2. Identify 3-10 articles that are relevant to the question
3. Read those articles carefully (they're included below)
4. Synthesize a clear, thorough answer
5. Cite your sources using [[wikilinks]]
6. If the knowledge base doesn't contain relevant information, say so honestly

## Knowledge Base

{wiki_content}

## Question

{question}
{file_back_instructions}"""

    answer = ""
    cost = 0.0

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                cwd=str(ROOT_DIR.parent),
                system_prompt={"type": "preset", "preset": "claude_code"},
                allowed_tools=tools,
                permission_mode="acceptEdits",
                max_turns=15,
            ),
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        answer += block.text
            elif isinstance(message, ResultMessage):
                cost = message.total_cost_usd or 0.0
    except Exception as e:
        answer = f"Error querying knowledge base: {e}"

    state = load_state()
    state["total_cost"] = state.get("total_cost", 0.0) + cost
    save_state(state)

    return answer


def main():
    parser = argparse.ArgumentParser(description="Query the knowledge base")
    parser.add_argument("question", help="The question to ask")
    parser.add_argument(
        "--file-back",
        action="store_true",
        help="File the answer back into the knowledge base",
    )
    args = parser.parse_args()

    print(f"Question: {args.question}")
    print(f"File back: {'yes' if args.file_back else 'no'}")
    print("-" * 60)

    answer = asyncio.run(run_query(args.question, file_back=args.file_back))
    print(answer)


if __name__ == "__main__":
    main()
