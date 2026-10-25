# AgentTaskPanel 项目文档

> macOS 悬浮任务面板：聚合本机所有 AI Agent 的会话/任务状态。仓库：[Jascenn/agent-task-panel](https://github.com/Jascenn/agent-task-panel)

## 文档索引

| 文档 | 内容 |
|---|---|
| [01-项目概述.md](01-项目概述.md) | 项目是什么、解决什么问题、能力边界 |
| [02-架构说明.md](02-架构说明.md) | 三层架构、数据流、通信链路 |
| [03-核心功能.md](03-核心功能.md) | 会话扫描、状态推断、面板交互、渠道配置 |
| [04-模块参考.md](04-模块参考.md) | main.swift / server.py / panel.html 的模块清单 |
| [05-配置说明.md](05-配置说明.md) | 运行时配置文件、常量、端口 |
| [06-开发与发布.md](06-开发与发布.md) | 构建、本地安装、打 tag 发版 |

## 快速上手

```bash
# 构建（产物在仓库根 AgentTaskPanel.app）
zsh scripts/build.sh

# 启动后验证数据服务
curl -s http://127.0.0.1:8765/api/tasks | head -c 200
```

## 相关文档（项目内已有）

- `docs/dev/BUILD-RELEASE.zh-CN.md` — 构建、签名与发布流程的完整版
- `docs/install/install-notes-template.txt` — DMG 内附带的安装说明
- Obsidian 项目主档：`/Users/jascen/Documents/Obsidian-Tech/projects/agent-task-panel/README.md`
