"""Data fetchers for ECUST ORIGIN dashboard.

Public entry points (all return plain dicts / lists, fail-soft to empty):
  fetch_team_static(path)          -> team dict from data/team.json
  fetch_repos(org, token=None)     -> list of {name, stars, language, desc, url}
  fetch_contributors(org, token=None) -> list of {login, avatar_url, commits}
  fetch_heatmap(org, token=None)   -> list of 364 daily counts (oldest -> newest)

If GitHub API is unreachable, each function returns an empty / mock structure
so the renderer can still produce a valid PNG.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


GH_API = "https://api.github.com"

# Logins that should never appear in the contributors roll. GitHub App
# bots use a "[bot]" suffix; web-flow is the web editor's account.
_BOT_LOGIN_SUFFIX = "[bot]"
_KNOWN_NON_HUMAN = {"web-flow"}


def _is_bot(author: dict[str, Any]) -> bool:
    login = (author.get("login") or "").lower()
    if not login:
        return True
    if login.endswith(_BOT_LOGIN_SUFFIX):
        return True
    if login in _KNOWN_NON_HUMAN:
        return True
    if (author.get("type") or "").lower() == "bot":
        return True
    return False


def _headers(token: str | None) -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def fetch_team_static(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def fetch_repos(org: str, token: str | None = None) -> list[dict[str, Any]]:
    if requests is None:
        return []
    url = f"{GH_API}/orgs/{org}/repos"
    out: list[dict[str, Any]] = []
    page = 1
    while page <= 4:  # 4 pages = 400 repos cap
        try:
            r = requests.get(
                url,
                params={"per_page": 100, "page": page, "type": "public", "sort": "pushed"},
                headers=_headers(token),
                timeout=15,
            )
            if r.status_code != 200:
                break
            data = r.json() or []
        except Exception:
            break
        if not isinstance(data, list) or not data:
            break
        for repo in data:
            out.append({
                "name": repo.get("name", ""),
                "stars": int(repo.get("stargazers_count") or 0),
                "language": (repo.get("language") or "").strip(),
                "desc": (repo.get("description") or "").strip(),
                "url": repo.get("html_url", ""),
            })
        if len(data) < 100:
            break
        page += 1
    out.sort(key=lambda x: x["stars"], reverse=True)
    return out[:8]


def fetch_contributors(org: str, token: str | None = None) -> list[dict[str, Any]]:
    """Aggregate commits per author across all org repos in the last 90 days."""
    if requests is None:
        return []
    since = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    repos = fetch_repos(org, token)
    counts: dict[str, dict[str, Any]] = {}
    for repo in repos[:8]:  # cap to avoid rate limit
        try:
            r = requests.get(
                f"{GH_API}/repos/{org}/{repo['name']}/commits",
                params={"since": since, "per_page": 100},
                headers=_headers(token),
                timeout=15,
            )
            if r.status_code != 200:
                continue
            for c in r.json() or []:
                author_obj = c.get("author") or {}
                if _is_bot(author_obj):
                    continue
                login = (author_obj.get("login") or "").lower()
                if not login:
                    continue
                avatar = author_obj.get("avatar_url") or ""
                if login not in counts:
                    counts[login] = {"login": login, "avatar_url": avatar, "commits": 0}
                counts[login]["commits"] += 1
        except Exception:
            continue
    out = sorted(counts.values(), key=lambda x: x["commits"], reverse=True)[:8]
    return out


def fetch_heatmap(org: str, token: str | None = None) -> list[int]:
    """Return 364 daily commit counts across the org, ending today (UTC)."""
    days = 364
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)
    counts = [0] * days

    if requests is None:
        return counts
    repos = fetch_repos(org, token)
    for repo in repos[:6]:
        page = 1
        while page <= 5:
            try:
                r = requests.get(
                    f"{GH_API}/repos/{org}/{repo['name']}/commits",
                    params={"since": start.isoformat(), "until": today.isoformat(),
                            "per_page": 100, "page": page},
                    headers=_headers(token),
                    timeout=15,
                )
                if r.status_code != 200:
                    break
                data = r.json() or []
            except Exception:
                break
            if not isinstance(data, list) or not data:
                break
            for c in data:
                d = (c.get("commit", {}).get("author", {}) or {}).get("date", "")
                if not d:
                    continue
                try:
                    dt = datetime.fromisoformat(d.replace("Z", "+00:00")).date()
                except ValueError:
                    continue
                idx = (dt - start).days
                if 0 <= idx < days:
                    counts[idx] += 1
            if len(data) < 100:
                break
            page += 1
    return counts


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--org", default=os.environ.get("GH_ORG", "ECUST-Origin"))
    ap.add_argument("--token", default=os.environ.get("GH_TOKEN"))
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", default="data/repos.json")
    args = ap.parse_args()

    static = fetch_team_static(Path(args.data_dir) / "team.json")
    repos = fetch_repos(args.org, args.token)
    members = fetch_contributors(args.org, args.token)
    heat = fetch_heatmap(args.org, args.token)

    if static.get("repos_override"):
        repos = static["repos_override"]
    if static.get("members_override"):
        members = static["members_override"]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({
            "team": static.get("team", {}),
            "stack": static.get("stack", []),
            "recruit": static.get("recruit", {}),
            "repos": repos,
            "members": members,
            "heatmap": heat,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }, f, ensure_ascii=False, indent=2)
    print(f"wrote {args.out}: {len(repos)} repos, {len(members)} members, "
          f"{sum(heat)} commits over {len(heat)} days")
    return 0


if __name__ == "__main__":
    sys.exit(main())
