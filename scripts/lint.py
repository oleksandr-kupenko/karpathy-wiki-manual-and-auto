"""
Lint the knowledge base for structural and semantic health.

Usage:
    uv run python lint.py                    # all checks
    uv run python lint.py --structural-only  # skip LLM checks (faster, cheaper)
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from config import REPORTS_DIR, WIKI_DIR, now_iso, today_iso
from utils import (
    count_inbound_links,
    extract_wikilinks,
    file_hash,
    get_article_word_count,
    list_source_files,
    list_wiki_pages,
    load_state,
    save_state,
    wiki_page_exists,
)

ROOT_DIR = Path(__file__).resolve().parent.parent


def check_broken_links() -> list[dict]:
    issues = []
    for article in list_wiki_pages():
        content = article.read_text(encoding="utf-8")
        rel = article.relative_to(WIKI_DIR)
        for link in extract_wikilinks(content):
            if link.startswith("daily/") or link.startswith("raw/"):
                continue
            if not wiki_page_exists(link):
                issues.append({
                    "severity": "error",
                    "check": "broken_link",
                    "file": str(rel),
                    "detail": f"Broken link: [[{link}]] - target does not exist",
                })
    return issues


def check_orphan_pages() -> list[dict]:
    issues = []
    for article in list_wiki_pages():
        rel = article.relative_to(WIKI_DIR)
        link_target = str(rel).replace(".md", "").replace("\\", "/")
        inbound = count_inbound_links(link_target)
        if inbound == 0:
            issues.append({
                "severity": "warning",
                "check": "orphan_page",
                "file": str(rel),
                "detail": f"Orphan page: no other articles link to [[{link_target}]]",
            })
    return issues


def check_orphan_sources() -> list[dict]:
    state = load_state()
    ingested = state.get("ingested", {})
    issues = []
    for src_path in list_source_files("all"):
        if src_path.is_relative_to(WIKI_DIR.parent / "daily"):
            src_type = "daily"
            state_key = f"daily/{src_path.name}"
        else:
            src_type = "raw"
            state_key = f"raw/{src_path.relative_to(WIKI_DIR.parent / 'raw')}"
        if state_key not in ingested:
            issues.append({
                "severity": "warning",
                "check": "orphan_source",
                "file": state_key,
                "detail": f"Uncompiled source: {state_key}",
            })
    return issues


def check_stale_articles() -> list[dict]:
    state = load_state()
    ingested = state.get("ingested", {})
    issues = []
    for src_path in list_source_files("all"):
        if src_path.is_relative_to(WIKI_DIR.parent / "daily"):
            state_key = f"daily/{src_path.name}"
        else:
            state_key = f"raw/{src_path.relative_to(WIKI_DIR.parent / 'raw')}"
        if state_key in ingested:
            stored_hash = ingested[state_key].get("hash", "")
            current_hash = file_hash(src_path)
            if stored_hash != current_hash:
                issues.append({
                    "severity": "warning",
                    "check": "stale_article",
                    "file": state_key,
                    "detail": f"Stale: {state_key} has changed since last compilation",
                })
    return issues


def check_missing_backlinks() -> list[dict]:
    issues = []
    for article in list_wiki_pages():
        content = article.read_text(encoding="utf-8")
        rel = article.relative_to(WIKI_DIR)
        source_link = str(rel).replace(".md", "").replace("\\", "/")

        for link in extract_wikilinks(content):
            if link.startswith("daily/") or link.startswith("raw/"):
                continue
            if wiki_page_exists(link):
                target_path = WIKI_DIR / f"{link}.md"
                if not target_path.exists():
                    for subdir in (WIKI_DIR / s for s in ["architecture", "decisions", "bugs", "features", "concepts", "operations", "connections"]):
                        candidate = subdir / f"{link}.md"
                        if candidate.exists():
                            target_path = candidate
                            break
                if target_path.exists():
                    target_content = target_path.read_text(encoding="utf-8")
                    if f"[[{source_link}]]" not in target_content:
                        issues.append({
                            "severity": "suggestion",
                            "check": "missing_backlink",
                            "file": str(rel),
                            "detail": f"[[{source_link}]] links to [[{link}]] but not vice versa",
                            "auto_fixable": True,
                        })
    return issues


def check_sparse_articles() -> list[dict]:
    issues = []
    for article in list_wiki_pages():
        word_count = get_article_word_count(article)
        if word_count < 200:
            rel = article.relative_to(WIKI_DIR)
            issues.append({
                "severity": "suggestion",
                "check": "sparse_article",
                "file": str(rel),
                "detail": f"Sparse article: {word_count} words (minimum recommended: 200)",
            })
    return issues


async def check_contradictions() -> list[dict]:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        query,
    )

    parts = []
    for page in list_wiki_pages():
        rel = page.relative_to(WIKI_DIR)
        content = page.read_text(encoding="utf-8")
        parts.append(f"## {rel}\n\n{content}")
    wiki_content = "\n\n---\n\n".join(parts)

    prompt = f"""Review this knowledge base for contradictions, inconsistencies, or
conflicting claims across articles.

## Knowledge Base

{wiki_content}

## Instructions

Look for:
- Direct contradictions (article A says X, article B says not-X)
- Inconsistent recommendations (different articles recommend conflicting approaches)
- Outdated information that conflicts with newer entries

For each issue found, output EXACTLY one line in this format:
CONTRADICTION: [file1] vs [file2] - description of the conflict
INCONSISTENCY: [file] - description of the inconsistency

If no issues found, output exactly: NO_ISSUES

Do NOT output anything else - no preamble, no explanation, just the formatted lines."""

    response = ""
    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                cwd=str(ROOT_DIR),
                allowed_tools=[],
                max_turns=2,
            ),
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response += block.text
    except Exception as e:
        return [{"severity": "error", "check": "contradiction", "file": "(system)", "detail": f"LLM check failed: {e}"}]

    issues = []
    if "NO_ISSUES" not in response:
        for line in response.strip().split("\n"):
            line = line.strip()
            if line.startswith("CONTRADICTION:") or line.startswith("INCONSISTENCY:"):
                issues.append({
                    "severity": "warning",
                    "check": "contradiction",
                    "file": "(cross-article)",
                    "detail": line,
                })

    return issues


def generate_report(all_issues: list[dict]) -> str:
    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]
    suggestions = [i for i in all_issues if i["severity"] == "suggestion"]

    lines = [
        f"# Lint Report - {today_iso()}",
        "",
        f"**Total issues:** {len(all_issues)}",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        f"- Suggestions: {len(suggestions)}",
        "",
    ]

    for severity, issues, marker in [
        ("Errors", errors, "x"),
        ("Warnings", warnings, "!"),
        ("Suggestions", suggestions, "?"),
    ]:
        if issues:
            lines.append(f"## {severity}")
            lines.append("")
            for issue in issues:
                fixable = " (auto-fixable)" if issue.get("auto_fixable") else ""
                lines.append(f"- **[{marker}]** `{issue['file']}` - {issue['detail']}{fixable}")
            lines.append("")

    if not all_issues:
        lines.append("All checks passed. Knowledge base is healthy.")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Lint the knowledge base")
    parser.add_argument(
        "--structural-only",
        action="store_true",
        help="Skip LLM-based checks (contradictions) - faster and free",
    )
    args = parser.parse_args()

    print("Running knowledge base lint checks...")
    all_issues: list[dict] = []

    checks = [
        ("Broken links", check_broken_links),
        ("Orphan pages", check_orphan_pages),
        ("Orphan sources", check_orphan_sources),
        ("Stale articles", check_stale_articles),
        ("Missing backlinks", check_missing_backlinks),
        ("Sparse articles", check_sparse_articles),
    ]

    for name, check_fn in checks:
        print(f"  Checking: {name}...")
        issues = check_fn()
        all_issues.extend(issues)
        print(f"    Found {len(issues)} issue(s)")

    if not args.structural_only:
        print("  Checking: Contradictions (LLM)...")
        issues = asyncio.run(check_contradictions())
        all_issues.extend(issues)
        print(f"    Found {len(issues)} issue(s)")
    else:
        print("  Skipping: Contradictions (--structural-only)")

    report = generate_report(all_issues)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"lint-{today_iso()}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport saved to: {report_path}")

    state = load_state()
    state["last_lint"] = now_iso()
    save_state(state)

    errors = sum(1 for i in all_issues if i["severity"] == "error")
    warnings = sum(1 for i in all_issues if i["severity"] == "warning")
    suggestions = sum(1 for i in all_issues if i["severity"] == "suggestion")
    print(f"\nResults: {errors} errors, {warnings} warnings, {suggestions} suggestions")

    if errors > 0:
        print("\nErrors found - knowledge base needs attention!")
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
