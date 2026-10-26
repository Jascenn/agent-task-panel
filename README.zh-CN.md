<div align="center">

<img src="docs/appicon.png" width="112" alt="AgentTaskPanel">

# AgentTaskPanel

### 一块悬浮面板，看清你所有 AI Agent 的任务状态

**Codex 跑到哪了？Claude Code 完成了没？**<br>
不用再挨个窗口翻。一块常驻面板实时聚合本机所有 AI Agent 的会话状态，<br>
任务结束自动通知，点卡片直接跳回对应的 Agent。

[![Release](https://img.shields.io/github/v/release/Jascenn/agent-task-panel?label=release&color=111111)](https://github.com/Jascenn/agent-task-panel/releases/latest)
[![Stars](https://img.shields.io/github/stars/Jascenn/agent-task-panel?style=flat&color=111111)](https://github.com/Jascenn/agent-task-panel/stargazers)
[![License](https://img.shields.io/badge/license-MIT-111111)](LICENSE)
![macOS](https://img.shields.io/badge/macOS-13%2B-000000?logo=apple&logoColor=white)

**[下载最新版](https://github.com/Jascenn/agent-task-panel/releases/latest)** · [功能](#功能) · [支持的 App](#支持的-app) · [从源码构建](#从源码构建) · English · *[README](README.md)*

| 磨砂模式 | 纯色模式 | 透明模式 |
|---|---|---|
| ![磨砂](docs/screenshots/screenshot-frost.jpg) | ![纯色](docs/screenshots/screenshot-solid.jpg) | ![透明](docs/screenshots/screenshot-clear.jpg) |

</div>

## 安装

1. 从 [Releases](https://github.com/Jascenn/agent-task-panel/releases/latest) 下载最新版 `AgentTaskPanel-vX.Y.Z.dmg`（文件名以 Release 页面为准）
2. 打开 DMG，把 🤖 AgentTaskPanel 拖进旁边的 Applications 文件夹
3. 首次启动会请求通知权限，允许即可

本地数据服务随 App 自动启动，菜单栏 🤖 图标实时显示执行中任务数。DMG 内附带中英双语「安装说明.txt」。

> App 使用 ad-hoc 签名（无付费开发者证书）。首次打开若提示「无法验证开发者」：右键 App → 打开，或终端执行 `xattr -dr com.apple.quarantine /Applications/AgentTaskPanel.app`。

## 功能

- **实时状态**：会话文件 120 秒内有写入 = 执行中；有完成标记 = 已完成；其余 = 空闲
- **菜单栏常驻**：单色模板图标 + 执行中数量，菜单含显示面板 / 置顶 / 开机自启 / 刷新 / 退出
- **服务守护**：每 5 秒健康检查本地 API，服务意外退出自动拉起，面板不再卡「未响应」
- **三态筛选**：点统计卡筛选执行中/已完成/空闲，再点取消
- **渠道色点**：任务前圆点用各 Agent 专属色，一眼认出来源
- **三态背景**：毛玻璃 → 全透明 → 纯色；透明模式下红绿灯和按钮自动隐藏，鼠标移入浮现
- **置顶悬浮**：📌 悬浮在所有窗口（含全屏 Space）之上
- **渠道配置**：⚙️ 勾选哪些 App 显示/隐藏，保存到 `~/.agent-panel-config.json`
- **任务跳转**：点卡片通过 URL scheme 跳回对应 Agent（codex://、cue:// 等）
- **完成通知**：任务从执行中变已完成时发系统通知
- **开机自启**：菜单一键开关，通过 LaunchAgent 实现

## 支持的 App

**编程 Agent**（读取本地会话文件，展示真实明细）：

| Agent | 状态 | 任务详情 | 数据来源 |
|---|---|---|---|
| Codex | ✅ 完整 | ✅ 最近对话/进展 | `~/.codex/sessions` JSONL |
| Claude Code | ✅ 完整 | ✅ 最近回复 | `~/.claude/projects` JSONL |
| Cue | ✅ 完整 | ✅ 实时工作文本 | `~/Library/Application Support/Cue/SessionStore/sessions.sqlite` |
| Grok Bot | ✅ 完整 | ✅ 会话最近消息 | `~/Library/Application Support/Grok Bot/sand-client-persistence/*.blob` |

**对话类 Agent**：

| Agent | 状态 | 任务详情 | 数据来源 |
|---|---|---|---|
| Today | ✅ 完整 | ✅ 最近聊天标题 + 活跃度 | `~/Library/Application Support/ai.today.macos.app/chat_*.sqlite` |
| Muse | ⚠️ 仅在线 | ❌ 任务在厂商服务端执行 | 进程检测 |
| ChatGPT | ⚠️ 仅在线 | ❌ 任务在厂商服务端执行 | 进程检测 |

「完整」= 面板读取本地会话文件，能显示真实任务标题和最近内容。

## 隐私

面板只**读取**上面列出的路径来推断会话状态，从不写它们、从不上传任何数据、完全离线可用。唯一涉及网络的端点是 `127.0.0.1:8765` —— 它自己的本地 API。

## 从源码构建

```bash
git clone https://github.com/Jascenn/agent-task-panel.git
cd agent-task-panel
zsh scripts/build.sh
open AgentTaskPanel.app
```

要求：macOS 13+，Xcode Command Line Tools（`xcode-select --install`）。

也可以直接浏览器打开面板：`http://127.0.0.1:8765`。

## 配置文件

`~/.agent-panel-config.json`（面板 ⚙️ 菜单可视化配置）：

```json
{ "hidden": ["today"] }
```

## 已知限制

- Muse / ChatGPT 的任务在服务端执行，只能显示"应用在线"，本地无任务明细
- 会话标题取自首条用户消息，注入的系统上下文（AGENTS.md 等）已自动过滤
- App 暂为 ad-hoc 签名，取得 Apple 开发者账号后会接入正式签名 + 公证

## 开发者文档

构建、签名、发布流程见 [docs/dev/BUILD-RELEASE.zh-CN.md](docs/dev/BUILD-RELEASE.zh-CN.md)。

提交与安全规则见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [SECURITY.md](SECURITY.md)。

## License

[MIT](LICENSE) © 2026 Jascenn
