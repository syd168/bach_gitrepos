#!/usr/bin/env python3
"""
List GitHub repositories, multi-select for batch deletion with confirmation.
Set GITHUB_TOKEN to a personal access token with delete_repo scope.
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx
import questionary
from questionary import Choice
from rich.console import Console
from rich.table import Table

from github_repo_service import (
    Repo,
    delete_repos_with_results,
    fetch_all_repos,
    get_classic_token_delete_warning,
    sort_repos,
)

console = Console()


def build_table(repos: list[Repo], title: str) -> Table:
    t = Table(title=title, show_lines=False)
    t.add_column("#", style="dim", justify="right")
    t.add_column("仓库", style="cyan")
    t.add_column("私有", justify="center")
    t.add_column("Fork", justify="center")
    t.add_column("归档", justify="center")
    t.add_column("说明", max_width=40)
    for i, r in enumerate(repos, 1):
        t.add_row(
            str(i),
            r.full_name,
            "是" if r.private else "否",
            "是" if r.fork else "否",
            "是" if r.archived else "否",
            (r.description or "")[:80] or "—",
        )
    return t


def select_repos_interactive(
    repos: list[Repo],
    *,
    forbid_delete_non_fork: bool,
) -> list[Repo]:
    if not repos:
        console.print("[yellow]没有可选仓库。[/yellow]")
        return []

    if forbid_delete_non_fork:
        selectable = [r for r in repos if r.fork]
        blocked = [r for r in repos if not r.fork]
        if blocked:
            console.print(
                f"[dim]已启用「禁止删除非 fork 仓库」：{len(blocked)} 个自有仓库不可选。[/dim]"
            )
        repos = selectable

    if not repos:
        console.print("[yellow]当前设置下没有可删除的仓库（仅 fork 可选）。[/yellow]")
        return []

    choices: list[Choice] = []
    for r in repos:
        extra = " [fork]" if r.fork else ""
        label = f"{r.full_name}{extra}"
        choices.append(Choice(title=label, value=r))

    result = questionary.checkbox(
        "勾选要删除的仓库（空格切换，回车确认）:",
        choices=choices,
        qmark=">",
    ).ask()

    if result is None:
        return []
    return list(result)


def confirm_deletion(selected: list[Repo], *, dry_run: bool) -> bool:
    if not selected:
        return False

    console.print("\n[bold red]即将删除以下仓库（不可恢复）：[/bold red]")
    for r in selected:
        console.print(f"  • {r.full_name}")

    if dry_run:
        console.print("\n[green]--dry-run：未执行删除。[/green]")
        return False

    typed = questionary.text(
        '输入 DELETE 以确认删除（区分大小写）:',
        validate=lambda t: True if t == "DELETE" else "必须输入 DELETE",
    ).ask()

    return typed == "DELETE"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="列出并批量删除 GitHub 仓库（需 GITHUB_TOKEN，含 delete_repo 权限）",
    )
    parser.add_argument(
        "--forbid-delete-non-fork",
        action="store_true",
        help="禁止删除非 fork 仓库（仅允许删除 fork）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只展示选择与确认流程，不调用删除接口",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="仅列出仓库，不进入删除流程",
    )
    parser.add_argument(
        "--sort",
        choices=("updated", "ascii"),
        default="updated",
        help="列表排序：updated=最近更新时间（接口默认）；ascii=按 owner/repo 全名字典序（码点序）",
    )
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        console.print("[red]请设置环境变量 GITHUB_TOKEN[/red]")
        return 1

    warn = get_classic_token_delete_warning(token)
    if warn:
        console.print(f"[yellow]{warn}[/yellow]")
    console.print("[dim]正在获取仓库列表…[/dim]")
    try:
        all_repos = fetch_all_repos(token)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]API 错误: {e.response.status_code} {e.response.text[:500]}[/red]")
        return 1
    except httpx.RequestError as e:
        console.print(f"[red]网络错误: {e}[/red]")
        return 1

    all_repos = sort_repos(all_repos, args.sort)
    sort_hint = "最近更新" if args.sort == "updated" else "全名 ASCII 序"
    title = f"共 {len(all_repos)} 个仓库（排序：{sort_hint}）"
    console.print(build_table(all_repos, title))

    if args.list_only:
        return 0

    selected = select_repos_interactive(
        all_repos,
        forbid_delete_non_fork=args.forbid_delete_non_fork,
    )
    if not selected:
        console.print("[dim]未选择任何仓库，退出。[/dim]")
        return 0

    if not confirm_deletion(selected, dry_run=args.dry_run):
        console.print("[yellow]已取消。[/yellow]")
        return 0

    names = [r.full_name for r in selected]
    if args.dry_run:
        console.print("[green]--dry-run：未执行删除。[/green]")
        return 0

    results = delete_repos_with_results(
        token,
        names,
        forbid_delete_non_fork=args.forbid_delete_non_fork,
    )

    failed = 0
    shown_403_hint = False
    for row in results:
        fn = row["full_name"]
        if row.get("ok"):
            console.print(f"[green]已删除[/green] {fn}")
        elif row.get("skipped"):
            console.print(f"[yellow]跳过[/yellow] {fn}: {row.get('error', '')}")
        else:
            failed += 1
            err = row.get("error", "")
            console.print(f"[red]删除失败[/red] {fn}\n    {err}")
            if "403:" in err or err.startswith("403"):
                if not shown_403_hint:
                    shown_403_hint = True
                    console.print(
                        "[dim]403 常见原因：Classic PAT 未勾选 delete_repo；"
                        "Fine-grained 令牌需对该仓库有 Administration；"
                        "组织仓库可能需在令牌上完成 SSO 授权。[/dim]"
                    )

    if failed:
        console.print(f"\n[yellow]失败 {failed} 个[/yellow]")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
