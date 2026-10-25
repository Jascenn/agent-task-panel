# Contributing / 贡献指南

Thanks for your interest in contributing! / 欢迎参与贡献！

## Dev setup / 开发环境

```bash
git clone https://github.com/Jascenn/agent-task-panel.git
cd agent-task-panel
zsh scripts/build.sh
open AgentTaskPanel.app
```

Requires macOS 13+ and Xcode Command Line Tools. / 需要 macOS 13+ 和 Xcode Command Line Tools。

## Project layout / 项目结构

| File | Purpose |
|---|---|
| `src/main.swift` | Native shell: NSPanel, menu bar item, pin watcher, service watchdog |
| `src/server.py` | Local data service: scans agent session files, serves `127.0.0.1:8765` |
| `web/panel.html` | Panel frontend (single file, no dependencies) |
| `scripts/build.sh` | Build + ad-hoc sign |
| `docs/BUILD-RELEASE.md` | Release workflow (中文) |

## Before opening a PR / 提交 PR 前

1. `zsh scripts/build.sh` passes and the app runs / 构建通过且 App 能跑
2. Test with at least one real agent session / 用至少一个真实 Agent 会话实测
3. Do not commit local paths, API keys, or session data / 不要提交本机路径、API key、会话数据
4. New user-facing features: update both `README.md` and `README.zh-CN.md` / 面向用户的新功能需同步更新中英 README
5. Version bumps: update `Info.plist` and `CHANGELOG.md` / 版本变更需同步更新 Info.plist 和 CHANGELOG

## Style / 代码风格

- Swift: comments in 中文 (project convention), 4-space indent
- Python: PEP 8, stdlib only (no pip dependencies by design)
- Frontend: single HTML file, no build step
