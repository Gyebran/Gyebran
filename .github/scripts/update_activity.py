from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

USERNAME = "Gyebran"
IGNORED_REPOS = {"Gyebran/Gyebran"}
MAX_LINES = 5
README_PATH = Path("README.md")


def github_request(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Gyebran-profile-readme-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def repo_link(repo: str) -> str:
    return f"https://github.com/{repo}"


def format_event(event: dict) -> str | None:
    event_type = event.get("type", "")
    repo = event.get("repo", {}).get("name", "")
    payload = event.get("payload", {}) or {}

    if not repo or repo in IGNORED_REPOS:
        return None

    repo_md = f"[{repo}]({repo_link(repo)})"

    if event_type == "PushEvent":
        count = payload.get("size") or len(payload.get("commits", [])) or 1
        suffix = "s" if count != 1 else ""
        return f"↗ Pushed {count} commit{suffix} to {repo_md}"

    if event_type == "CreateEvent":
        ref_type = payload.get("ref_type") or "repository"
        ref = payload.get("ref")
        if ref_type == "repository" or not ref:
            return f"+ Created {repo_md}"
        return f"+ Created {ref_type} `{ref}` in {repo_md}"

    if event_type == "PullRequestEvent":
        pr = payload.get("pull_request", {})
        number = pr.get("number") or payload.get("number")
        url = pr.get("html_url") or repo_link(repo)
        action = str(payload.get("action", "updated")).replace("_", " ").capitalize()
        return f"↗ {action} PR [#{number}]({url}) in {repo_md}" if number else f"↗ {action} a PR in {repo_md}"

    if event_type == "IssuesEvent":
        issue = payload.get("issue", {})
        number = issue.get("number")
        url = issue.get("html_url") or repo_link(repo)
        action = str(payload.get("action", "updated")).replace("_", " ").capitalize()
        return f"• {action} issue [#{number}]({url}) in {repo_md}" if number else f"• {action} an issue in {repo_md}"

    if event_type == "WatchEvent":
        return f"☆ Starred {repo_md}"

    if event_type == "ForkEvent":
        forkee = payload.get("forkee", {})
        fork_name = forkee.get("full_name")
        fork_url = forkee.get("html_url")
        if fork_name and fork_url:
            return f"↗ Forked {repo_md} to [{fork_name}]({fork_url})"
        return f"↗ Forked {repo_md}"

    if event_type == "ReleaseEvent":
        release = payload.get("release", {})
        tag = release.get("tag_name") or "a release"
        url = release.get("html_url") or repo_link(repo)
        return f"+ Published [{tag}]({url}) in {repo_md}"

    if event_type == "PullRequestReviewEvent":
        pr = payload.get("pull_request", {})
        number = pr.get("number") or payload.get("number")
        url = pr.get("html_url") or repo_link(repo)
        return f"✓ Reviewed PR [#{number}]({url}) in {repo_md}" if number else f"✓ Reviewed a PR in {repo_md}"

    return None


def main() -> None:
    events = github_request(f"https://api.github.com/users/{USERNAME}/events/public?per_page=100")

    lines: list[str] = []
    for event in events:
        line = format_event(event)
        if line and line not in lines:
            lines.append(line)
        if len(lines) >= MAX_LINES:
            break

    if not lines:
        lines = ["No recent public activity available yet."]

    activity_block = "\n".join(f"{index}. {line}" for index, line in enumerate(lines, start=1))

    jakarta = timezone(timedelta(hours=7))
    updated_at = datetime.now(jakarta).strftime("%A, %B %d, %Y · %H:%M WIB")

    readme = README_PATH.read_text(encoding="utf-8")
    readme = re.sub(
        r"<!--RECENT_ACTIVITY:start-->.*?<!--RECENT_ACTIVITY:end-->",
        f"<!--RECENT_ACTIVITY:start-->\n{activity_block}\n<!--RECENT_ACTIVITY:end-->",
        readme,
        flags=re.DOTALL,
    )
    readme = re.sub(
        r"<!--RECENT_ACTIVITY:last_update-->.*?<!--RECENT_ACTIVITY:last_update_end-->",
        f"<!--RECENT_ACTIVITY:last_update-->\nLast updated: {updated_at}\n<!--RECENT_ACTIVITY:last_update_end-->",
        readme,
        flags=re.DOTALL,
    )

    README_PATH.write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()
