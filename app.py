#!/usr/bin/env python3
"""Flask Web 界面（Element Plus CDN）：列出仓库、勾选、确认后批量删除。"""

from __future__ import annotations

import os
import secrets

import httpx
from flask import Flask, flash, redirect, render_template, request, session, url_for

from github_repo_service import (
    delete_repos_with_results,
    fetch_all_repos,
    get_classic_token_delete_warning,
    sort_repos,
)

# 静态资源放在 templates/static/，与 Jinja 模板同目录树，URL 仍为 /static/...
app = Flask(__name__, static_folder="templates/static", static_url_path="/static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)


def _token() -> str | None:
    t = session.get("github_token")
    return t.strip() if isinstance(t, str) and t.strip() else None


@app.route("/")
def index():
    if _token():
        return redirect(url_for("repos"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    token = (request.form.get("token") or "").strip()
    if not token:
        flash("请输入 Personal Access Token。", "warning")
        return redirect(url_for("index"))
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            r.raise_for_status()
    except httpx.HTTPStatusError as e:
        flash(f"令牌无效或权限不足：{e.response.status_code}", "danger")
        return redirect(url_for("index"))
    except httpx.RequestError as e:
        flash(f"网络错误：{e}", "danger")
        return redirect(url_for("index"))

    session["github_token"] = token
    session.permanent = bool(os.environ.get("FLASK_SESSION_PERMANENT"))
    flash("已登录。", "success")
    return redirect(url_for("repos"))


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("github_token", None)
    flash("已退出。", "info")
    return redirect(url_for("index"))


@app.route("/repos")
def repos():
    token = _token()
    if not token:
        return redirect(url_for("index"))

    sort_mode = request.args.get("sort") or "updated"
    if sort_mode not in ("updated", "ascii"):
        sort_mode = "updated"
    # 默认开启：无 forbid 参数时视为 "1"；显式传 forbid=0 可关闭
    forbid_non_fork = request.args.get("forbid", "1") == "1"

    warn = get_classic_token_delete_warning(token)
    try:
        all_repos = sort_repos(fetch_all_repos(token), sort_mode)
    except httpx.HTTPStatusError as e:
        flash(f"获取仓库列表失败：{e.response.status_code} {e.response.text[:300]}", "danger")
        return render_template(
            "repos.html",
            repos=[],
            sort_mode=sort_mode,
            forbid_non_fork=forbid_non_fork,
            classic_warn=warn,
            total=0,
            sort_hint="",
        )
    except httpx.RequestError as e:
        flash(f"网络错误：{e}", "danger")
        return render_template(
            "repos.html",
            repos=[],
            sort_mode=sort_mode,
            forbid_non_fork=forbid_non_fork,
            classic_warn=warn,
            total=0,
            sort_hint="",
        )

    rows = [r.to_row() for r in all_repos]
    sort_hint = "最近更新" if sort_mode == "updated" else "全名 ASCII 序"
    return render_template(
        "repos.html",
        repos=rows,
        sort_mode=sort_mode,
        forbid_non_fork=forbid_non_fork,
        classic_warn=warn,
        total=len(rows),
        sort_hint=sort_hint,
    )


@app.route("/repos/delete", methods=["POST"])
def delete_repos():
    token = _token()
    if not token:
        flash("请先登录。", "warning")
        return redirect(url_for("index"))

    confirm = (request.form.get("confirm") or "").strip()
    if confirm != "DELETE":
        flash("确认失败：请在弹窗中输入大写 DELETE。", "danger")
        return redirect(url_for("repos"))

    full_names = request.form.getlist("full_name")
    if not full_names:
        flash("未选择任何仓库。", "warning")
        return redirect(url_for("repos"))

    forbid_delete_non_fork = request.form.get("forbid_delete_non_fork") == "1"

    results = delete_repos_with_results(
        token,
        full_names,
        forbid_delete_non_fork=forbid_delete_non_fork,
    )

    ok_n = sum(1 for r in results if r.get("ok"))
    skip_n = sum(1 for r in results if r.get("skipped"))
    err_rows = [r for r in results if not r.get("ok") and not r.get("skipped")]

    if ok_n:
        flash(f"已成功删除 {ok_n} 个仓库。", "success")
    if skip_n:
        flash(f"已跳过 {skip_n} 个（禁止删除非 fork 或策略限制）。", "secondary")
    if err_rows:
        parts = [f"{r['full_name']}: {r.get('error', '')}" for r in err_rows[:12]]
        extra = f" 等共 {len(err_rows)} 个" if len(err_rows) > 12 else ""
        flash(f"删除失败 {len(err_rows)} 个 — " + "；".join(parts) + extra, "danger")
        flash(
            "若出现 403：Classic 令牌需勾选 delete_repo；Fine-grained 需对该仓库有 Administration；"
            "组织仓库可能需完成 SSO 授权。",
            "info",
        )

    return redirect(url_for("repos"))


if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "9050"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug)
