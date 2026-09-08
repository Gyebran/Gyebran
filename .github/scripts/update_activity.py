from __future__ import annotations

import html
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
METRICS_PATH = Path("assets/github-metrics.svg")


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


def format_event(event: dict) -> dict | None:
    event_type = event.get("type", "")
    repo = event.get("repo", {}).get("name", "")
    payload = event.get("payload", {}) or {}

    if not repo or repo in IGNORED_REPOS:
        return None

    result = {
        "label": "EVENT",
        "repo": repo,
        "repo_url": repo_link(repo),
        "detail": "Updated",
    }

    if event_type == "PushEvent":
        count = payload.get("size") or len(payload.get("commits", [])) or 1
        result.update(label="PUSH", detail=f"{count} commit{'s' if count != 1 else ''}")
        return result

    if event_type == "CreateEvent":
        ref_type = payload.get("ref_type") or "repository"
        ref = payload.get("ref")
        if ref_type == "repository" or not ref:
            result.update(label="CREATE", detail="repository created")
        else:
            result.update(label="CREATE", detail=f"{ref_type} {ref}")
        return result

    if event_type == "PullRequestEvent":
        pr = payload.get("pull_request", {})
        number = pr.get("number") or payload.get("number")
        action = str(payload.get("action", "updated")).replace("_", " ")
        detail = f"{action} PR #{number}" if number else f"{action} pull request"
        result.update(label="PR", detail=detail)
        return result

    if event_type == "IssuesEvent":
        issue = payload.get("issue", {})
        number = issue.get("number")
        action = str(payload.get("action", "updated")).replace("_", " ")
        detail = f"{action} issue #{number}" if number else f"{action} issue"
        result.update(label="ISSUE", detail=detail)
        return result

    if event_type == "WatchEvent":
        result.update(label="STAR", detail="starred repository")
        return result

    if event_type == "ForkEvent":
        result.update(label="FORK", detail="forked repository")
        return result

    if event_type == "ReleaseEvent":
        release = payload.get("release", {})
        tag = release.get("tag_name") or "release"
        result.update(label="RELEASE", detail=f"published {tag}")
        return result

    if event_type == "PullRequestReviewEvent":
        pr = payload.get("pull_request", {})
        number = pr.get("number") or payload.get("number")
        result.update(label="REVIEW", detail=f"reviewed PR #{number}" if number else "reviewed pull request")
        return result

    return None


def render_activity_table(events: list[dict]) -> str:
    rows = ["<table>", "<tr><th>EVENT</th><th>REPOSITORY</th><th>DETAIL</th></tr>"]

    for event in events:
        label = html.escape(event["label"])
        repo = html.escape(event["repo"])
        repo_url = html.escape(event["repo_url"], quote=True)
        detail = html.escape(event["detail"])
        rows.append(
            f'<tr><td><code>{label}</code></td>'
            f'<td><a href="{repo_url}"><b>{repo}</b></a></td>'
            f'<td>{detail}</td></tr>'
        )

    rows.append("</table>")
    return "\n".join(rows)


def render_metrics_svg(user: dict, repos: list[dict], updated_at: str) -> str:
    public_repos = int(user.get("public_repos", 0) or 0)
    followers = int(user.get("followers", 0) or 0)
    total_stars = sum(int(repo.get("stargazers_count", 0) or 0) for repo in repos if not repo.get("fork"))
    created_at = str(user.get("created_at", ""))
    since = created_at[:4] if len(created_at) >= 4 else "—"

    metrics = [
        ("PUBLIC REPOS", str(public_repos)),
        ("FOLLOWERS", str(followers)),
        ("TOTAL STARS", str(total_stars)),
        ("ON GITHUB SINCE", since),
    ]

    card_width = 214
    gap = 16
    start_x = 36
    cards = []
    for index, (label, value) in enumerate(metrics):
        x = start_x + index * (card_width + gap)
        cards.append(
            f'<rect x="{x}" y="78" width="{card_width}" height="108" rx="12" fill="#081710" stroke="#174c34"/>'
            f'<text x="{x + 18}" y="111" fill="#5c8374" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="12" font-weight="700">{html.escape(label)}</text>'
            f'<text x="{x + 18}" y="158" fill="#00ff9c" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="31" font-weight="800">{html.escape(value)}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="230" viewBox="0 0 1000 230" role="img" aria-labelledby="title desc">
  <title id="title">Gyebran GitHub live metrics</title>
  <desc id="desc">Self-hosted GitHub metrics refreshed automatically from the GitHub API.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#06120c"/><stop offset="1" stop-color="#091a12"/>
    </linearGradient>
    <pattern id="grid" width="22" height="22" patternUnits="userSpaceOnUse">
      <path d="M22 0H0V22" fill="none" stroke="#0f2d1f" stroke-width="1" opacity="0.36"/>
    </pattern>
  </defs>
  <rect x="1" y="1" width="998" height="228" rx="18" fill="url(#bg)" stroke="#174c34" stroke-width="2"/>
  <rect x="1" y="1" width="998" height="228" rx="18" fill="url(#grid)"/>
  <text x="36" y="43" fill="#86efac" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="17" font-weight="700">GITHUB://LIVE_TELEMETRY</text>
  <text x="872" y="43" fill="#00ff9c" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="13" font-weight="700">● SYNCED</text>
  {''.join(cards)}
  <text x="36" y="210" fill="#5c8374" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="11">UPDATED {html.escape(updated_at)}</text>
</svg>'''


def main() -> None:
    events_payload = github_request(f"https://api.github.com/users/{USERNAME}/events/public?per_page=100")
    user = github_request(f"https://api.github.com/users/{USERNAME}")
    repos = github_request(f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner&sort=updated")

    events: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for raw_event in events_payload:
        event = format_event(raw_event)
        if not event:
            continue
        key = (event["label"], event["repo"], event["detail"])
        if key in seen:
            continue
        seen.add(key)
        events.append(event)
        if len(events) >= MAX_LINES:
            break

    if not events:
        events = [{"label": "IDLE", "repo": "Gyebran", "repo_url": "https://github.com/Gyebran", "detail": "No recent public activity available"}]

    jakarta = timezone(timedelta(hours=7))
    now = datetime.now(jakarta)
    updated_at = now.strftime("%A, %B %d, %Y · %H:%M WIB")
    metrics_updated_at = now.strftime("%Y-%m-%d %H:%M WIB")

    readme = README_PATH.read_text(encoding="utf-8")
    readme = re.sub(
        r"<!--RECENT_ACTIVITY:start-->.*?<!--RECENT_ACTIVITY:end-->",
        f"<!--RECENT_ACTIVITY:start-->\n{render_activity_table(events)}\n<!--RECENT_ACTIVITY:end-->",
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
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(render_metrics_svg(user, repos, metrics_updated_at), encoding="utf-8")


if __name__ == "__main__":
    main()
