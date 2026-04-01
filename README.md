# GitHub 仓库批量管理

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

基于 Personal Access Token 列出你在 GitHub 上的仓库，支持 Web 界面勾选与终端交互式批量删除（需 `delete_repo` 等权限）。Web 端使用 **Flask** + **Vue 3** + **Element Plus**（CDN），暗色主题。

本项目**以 MIT 许可证开源**（见仓库根目录 [`LICENSE`](LICENSE)），可自由使用、修改与再分发；**软件按「原样」提供，不含任何明示或默示担保**（详见许可证全文）。

## 功能概览

- **登录**：使用 PAT 登录，服务端调用 `GET /user` 校验令牌。
- **仓库列表**：分页拉取 `GET /user/repos`，支持按最近更新时间或全名 ASCII 排序（服务端）。
- **安全选项**：可开启「禁止删除非 fork」，避免误删自有仓库。
- **刷新列表**：在保持当前排序与选项的前提下重新从 GitHub 拉取数据。
- **批量删除**：勾选仓库 → 确认对话框中输入大写 `DELETE` → 提交删除；Classic 令牌若无 `delete_repo` 会在页面上给出提示。
- **命令行工具**：同一套 `github_repo_service` 逻辑，支持列表、交互多选、`--dry-run` 等。

## 技术栈

| 类别 | 说明 |
|------|------|
| 后端 | Python 3.10+，Flask 3，httpx |
| 前端（Web） | Vue 3、Element Plus 2（jsDelivr CDN），无前端构建步骤 |
| CLI | Rich、Questionary |

## 安装

```bash
git clone https://github.com/<你的用户名>/del_github_reposities.git
cd del_github_reposities
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 运行 Web 服务

```bash
export FLASK_SECRET_KEY="请替换为随机长字符串"   # 生产环境必填，用于会话签名
python app.py
```

默认监听 `http://127.0.0.1:9050`。浏览器打开首页，输入 PAT 登录即可。

也可用环境变量覆盖监听地址与调试模式：

| 变量 | 含义 | 默认 |
|------|------|------|
| `FLASK_HOST` | 监听地址 | `127.0.0.1` |
| `FLASK_PORT` | 端口 | `9050` |
| `FLASK_DEBUG` | 是否开启调试（`1` / `true` / `yes`） | 关闭 |
| `FLASK_SECRET_KEY` | Flask 会话密钥 | 未设置时每次启动随机生成（重启会登出） |
| `FLASK_SESSION_PERMANENT` | 若设置非空，会话使用「永久」Cookie 策略 | 未设置 |

## 命令行工具

依赖环境变量 **`GITHUB_TOKEN`**（与 Web 无关，仅 CLI 使用）：

```bash
export GITHUB_TOKEN="ghp_xxxxxxxx"
python delete_github_repos_cli.py --list-only          # 仅列出
python delete_github_repos_cli.py --sort ascii         # 按全名排序
python delete_github_repos_cli.py --forbid-delete-non-fork   # 只允许删 fork
python delete_github_repos_cli.py --dry-run            # 演练，不真正删除
```

## Personal Access Token 权限说明

- **列出与查看仓库**：至少需要能访问 `GET /user` 与 `GET /user/repos` 的权限（一般 `repo` 范围会包含）。
- **删除仓库**：
  - **Classic PAT**：除 `repo` 外需单独勾选 **`delete_repo`**。
  - **Fine-grained PAT**：需对目标仓库具备 **Administration** 等删除所需权限；组织仓库可能还需在令牌上完成 **SSO** 授权。

更细的图文说明见登录页右侧卡片（`templates/partials/gh-login-app-template.html`）。

## 安全提示

- PAT 等效于账户凭证，勿提交到 Git，勿在日志中打印。
- 本服务仅在会话中保存令牌；生产部署请使用 **HTTPS**、强随机 **`FLASK_SECRET_KEY`**，并限制访问来源（防火墙或反向代理鉴权）。
- 删除不可恢复，请先在测试仓库或 `--dry-run` 上验证流程。

## 项目结构（节选）

```
LICENSE                     # MIT 许可证全文
CONTRIBUTING.md             # 参与贡献说明
SECURITY.md                 # 安全报告方式
app.py                      # Flask 路由与会话
github_repo_service.py      # GitHub API 封装（列表、删除、Classic 删除权限提示）
delete_github_repos_cli.py  # 终端入口
requirements.txt
templates/
  base.html
  login.html
  repos.html
  partials/                 # Vue 片段模板
  static/js/                # gh-login.js、gh-repos.js
```

## 开源与贡献

- **许可证**：[MIT License](LICENSE) — Copyright (c) 2026 del_github_reposities contributors。你可以在遵守 MIT 条款的前提下使用、复制、修改与分发本软件；**版权声明与许可文本需保留在副本中**。
- **参与贡献**：请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)（Issue/PR 约定、代码风格、许可说明）。
- **安全问题**：请勿在公开 Issue 中披露可利用细节；请按 [SECURITY.md](SECURITY.md) 说明联系。

将 `LICENSE` 中的版权行改为你自己的姓名或组织名称，或保留「contributors」以表示集体版权，均可；与 GitHub 显示名一致即可。
