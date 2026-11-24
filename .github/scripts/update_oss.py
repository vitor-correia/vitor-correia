#!/usr/bin/env python3
"""Updates the Open Source Contributions section in README.md using GitHub Search API."""

import json
import os
import re
import urllib.parse
import urllib.request

USERNAME = os.environ.get("GITHUB_USERNAME", "vitor-correia")
TOKEN = os.environ.get("GITHUB_TOKEN")
README_PATH = os.environ.get("README_PATH", "README.md")

START_MARKER = "<!--START_SECTION:oss-->"
END_MARKER = "<!--END_SECTION:oss-->"


def fetch_upstream_prs(username: str):
    items = []
    for page in range(1, 4):
        query = f"is:pr author:{username} -user:{username}"
        params = urllib.parse.urlencode(
            {"q": query, "sort": "created", "order": "desc", "per_page": 100, "page": page}
        )
        url = f"https://api.github.com/search/issues?{params}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "profile-oss-updater/1.0",
                "Accept": "application/vnd.github+json",
            },
        )
        if TOKEN:
            req.add_header("Authorization", f"Bearer {TOKEN}")

        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        batch = data.get("items", [])
        items.extend(batch)
        if len(batch) < 100:
            break
    return items


def escape_md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_table(rows, date_header: str) -> str:
    lines = [
        f"| Repository | Pull Request | {date_header} |",
        "| --- | --- | --- |",
    ]
    for pr in rows:
        repo = pr["repo"]
        repo_link = f"[{repo}](https://github.com/{repo})"
        pr_link = f"[{escape_md(pr['title'])}]({pr['url']})"
        lines.append(f"| {repo_link} | {pr_link} | {pr['date']} |")
    return "\n".join(lines)


def render_section(raw_items) -> str:
    merged = []
    opened = []
    repos = set()

    for it in raw_items:
        repo_url = it.get("repository_url", "")
        repo = "/".join(repo_url.split("/")[-2:])
        pr_info = it.get("pull_request") or {}
        merged_at = pr_info.get("merged_at")
        state = it.get("state")

        if merged_at:
            repos.add(repo)
            merged.append(
                {
                    "repo": repo,
                    "title": it.get("title", ""),
                    "url": it.get("html_url", ""),
                    "date": merged_at[:10],
                }
            )
        elif state == "open":
            repos.add(repo)
            opened.append(
                {
                    "repo": repo,
                    "title": it.get("title", ""),
                    "url": it.get("html_url", ""),
                    "date": (it.get("created_at") or "")[:10],
                }
            )

    total = len(merged) + len(opened)
    badges = [
        f'<img src="https://img.shields.io/badge/Upstream%20PRs-{total}-1F6FEB?style=flat-square" alt="Upstream PRs">',
    ]
    if merged:
        badges.append(
            f'<img src="https://img.shields.io/badge/Merged-{len(merged)}-8957E5?style=flat-square" alt="Merged PRs">'
        )
    if opened:
        badges.append(
            f'<img src="https://img.shields.io/badge/Open-{len(opened)}-2EA043?style=flat-square" alt="Open PRs">'
        )
    badges.append(
        f'<img src="https://img.shields.io/badge/Projects-{len(repos)}-0284C7?style=flat-square" alt="Projects">'
    )

    parts = [" ".join(badges)]

    if merged:
        summary = f"<b>Merged</b> · {len(merged)} pull request{'s' if len(merged) != 1 else ''}"
        parts.append(
            f"<details open>\n<summary>{summary}</summary>\n\n{build_table(merged[:20], 'Merged')}\n\n</details>"
        )

    if opened:
        open_attr = " open" if not merged or len(opened) <= 10 else ""
        summary = f"<b>Open / Under Review</b> · {len(opened)} pull request{'s' if len(opened) != 1 else ''}"
        parts.append(
            f"<details{open_attr}>\n<summary>{summary}</summary>\n\n{build_table(opened[:20], 'Opened')}\n\n</details>"
        )

    return "\n\n".join(parts)


def main():
    raw_items = fetch_upstream_prs(USERNAME)
    section = render_section(raw_items)

    with open(README_PATH, "r", encoding="utf-8") as f:
        readme = f.read()

    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        re.DOTALL,
    )
    replacement = f"{START_MARKER}\n{section}\n{END_MARKER}"
    updated, count = pattern.subn(replacement, readme, count=1)
    if count == 0:
        raise RuntimeError(f"Markers {START_MARKER} / {END_MARKER} not found in {README_PATH}")

    if updated != readme:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(updated)
        print("README.md updated.")
    else:
        print("No changes to README.md.")


if __name__ == "__main__":
    main()
