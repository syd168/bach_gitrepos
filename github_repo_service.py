"""GitHub 仓库列表与删除（CLI 与 Web 共用）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

GITHUB_API = "https://api.github.com"


def format_github_http_error(response: httpx.Response) -> str:
    """Readable message from GitHub API error body (JSON or raw)."""
    code = response.status_code
    try:
        data = response.json()
        if isinstance(data, dict):
            msg = data.get("message") or ""
            if msg:
                doc = data.get("documentation_url")
                if doc:
                    return f"{code}: {msg}\n    {doc}"
                return f"{code}: {msg}"
    except Exception:
        pass
    text = (response.text or "").strip()
    if text:
        return f"{code}: {text[:500]}"
    return str(code)


def get_classic_token_delete_warning(token: str) -> str | None:
    """若 Classic PAT 未包含 delete_repo，返回提示文案；否则 None。"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{GITHUB_API}/user", headers=headers)
            r.raise_for_status()
    except Exception:
        return None
    scopes_raw = (r.headers.get("X-OAuth-Scopes") or "").strip()
    if not scopes_raw:
        return None
    scope_list = {s.strip() for s in scopes_raw.split(",") if s.strip()}
    if "delete_repo" in scope_list:
        return None
    return (
        "当前 Classic 个人令牌未包含 delete_repo，删除仓库通常会返回 403。"
        "请到 GitHub → Settings → Developer settings → Personal access tokens "
        "中编辑或新建令牌并勾选 delete_repo。"
    )


@dataclass
class Repo:
    name: str
    full_name: str
    private: bool
    fork: bool
    archived: bool
    description: str | None

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> Repo:
        return cls(
            name=d["name"],
            full_name=d["full_name"],
            private=d["private"],
            fork=d["fork"],
            archived=d.get("archived", False),
            description=d.get("description"),
        )

    def to_row(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name,
            "name": self.name,
            "private": self.private,
            "fork": self.fork,
            "archived": self.archived,
            "description": self.description or "",
        }


def _api_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def fetch_repo(token: str, full_name: str) -> Repo:
    with httpx.Client(timeout=60.0) as client:
        r = client.get(f"{GITHUB_API}/repos/{full_name}", headers=_api_headers(token))
        r.raise_for_status()
        return Repo.from_api(r.json())


def fetch_all_repos(token: str) -> list[Repo]:
    repos: list[Repo] = []
    url: str | None = f"{GITHUB_API}/user/repos"
    first_page_params = {"per_page": 100, "sort": "updated"}
    first = True

    with httpx.Client(timeout=60.0) as client:
        while url:
            r = client.get(
                url,
                headers=_api_headers(token),
                params=first_page_params if first else None,
            )
            first = False
            r.raise_for_status()
            for item in r.json():
                repos.append(Repo.from_api(item))
            url = _next_page_url(r.headers.get("Link", ""))

    return repos


def _next_page_url(link_header: str) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        part = part.strip()
        if 'rel="next"' in part:
            url = part.split(";")[0].strip()
            if url.startswith("<") and url.endswith(">"):
                return url[1:-1]
    return None


def sort_repos(repos: list[Repo], sort_mode: str) -> list[Repo]:
    if sort_mode == "updated":
        return list(repos)
    if sort_mode == "ascii":
        return sorted(repos, key=lambda r: r.full_name)
    raise ValueError(f"unknown sort mode: {sort_mode}")


def delete_repo(token: str, full_name: str) -> None:
    with httpx.Client(timeout=60.0) as client:
        r = client.delete(
            f"{GITHUB_API}/repos/{full_name}",
            headers=_api_headers(token),
        )
        r.raise_for_status()


def delete_repos_with_results(
    token: str,
    full_names: list[str],
    *,
    forbid_delete_non_fork: bool,
) -> list[dict[str, Any]]:
    """逐个删除并返回每条结果；forbid_delete_non_fork 为真时跳过非 fork。"""
    results: list[dict[str, Any]] = []
    for name in full_names:
        if forbid_delete_non_fork:
            try:
                info = fetch_repo(token, name)
                if not info.fork:
                    results.append(
                        {
                            "full_name": name,
                            "ok": False,
                            "skipped": True,
                            "error": "已启用「禁止删除非 fork」，跳过自有仓库",
                        }
                    )
                    continue
            except httpx.HTTPStatusError as e:
                results.append(
                    {
                        "full_name": name,
                        "ok": False,
                        "error": format_github_http_error(e.response),
                    }
                )
                continue
            except httpx.RequestError as e:
                results.append(
                    {"full_name": name, "ok": False, "error": str(e)}
                )
                continue
        try:
            delete_repo(token, name)
            results.append({"full_name": name, "ok": True})
        except httpx.HTTPStatusError as e:
            results.append(
                {
                    "full_name": name,
                    "ok": False,
                    "error": format_github_http_error(e.response),
                }
            )
        except httpx.RequestError as e:
            results.append({"full_name": name, "ok": False, "error": str(e)})
    return results
