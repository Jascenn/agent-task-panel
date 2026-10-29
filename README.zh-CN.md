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
![macOS](https://img.shields.io/badge/macOS-12%2B-000000?logo=apple&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-x64-000000?logo=windows&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-x64-000000?logo=linux&logoColor=white)

**[项目主页](https://agentpanel.lingyi.tools/)** · [下载最新版](https://github.com/Jascenn/agent-task-panel/releases/latest) · [功能](#功能) · [支持的 App](#支持的-app) · [从源码构建](#从源码构建) · English · *[README](README.md)*

| 透明模式 | 纯色模式 | 毛玻璃模式 |
|---|---|---|
| ![白底透明](docs/screenshots/screenshot-clear.jpg) | ![纯色](docs/screenshots/screenshot-solid.jpg) | ![毛玻璃](docs/screenshots/screenshot-frost.jpg) |

</div>

## 安装

> **平台测试状态：目前只有 macOS 版本经过实际使用测试。**
> Windows x64 和 Linux x64 已由 CI 构建并完成打包冒烟检查，但尚未在真实 Windows/Linux
> 设备上验证，请先按预览版对待。

从 [Releases](https://github.com/Jascenn/agent-task-panel/releases/latest) 下载对应平台的安装包：

| 平台 | 安装包 |
|---|---|
| macOS 12+ | `AgentTaskPanel-0.4.0-macos-universal.dmg` |
| Windows x64 | `AgentTaskPanel-0.4.0-win-x64.exe` |
| Linux x64 | `AgentTaskPanel-0.4.0-linux-x86_64.AppImage` |

**macOS**：打开 DMG，把 🤖 AgentTaskPanel 拖进 Applications。若提示「无法验证开发者」，
右键 App → 打开，或终端执行
`xattr -dr com.apple.quarantine /Applications/AgentTaskPanel.app`。

**Windows**：运行安装程序。安装包暂未做代码签名，SmartScreen 可能要求确认。

**Linux**：先添加执行权限，再启动：

```bash
chmod +x AgentTaskPanel-0.4.0-linux-x86_64.AppImage
./AgentTaskPanel-0.4.0-linux-x86_64.AppImage
```

本地数据服务随 App 自动启动。macOS 菜单栏 🤖 图标实时显示执行中任务数；Windows 和
Linux 使用托盘图标。每个 Release 都附带并校验 `SHA256SUMS`。

## 功能

- **实时状态**：每个 Agent 按自身回合边界判断执行中/已完成/空闲，自适应超时只用于降级异常挂起
- **菜单栏常驻**：单色模板图标 + 执行中数量，菜单含显示面板 / 置顶 / 开机自启 / 刷新 / 退出
- **服务守护**：每 5 秒健康检查本地 API，服务意外退出自动拉起，面板不再卡「未响应」
- **三态筛选**：点统计卡筛选执行中/已完成/空闲，再点取消
- **渠道色点**：任务前圆点用各 Agent 专属色，一眼认出来源
- **三态背景**：全透明 → 纯色 → 毛玻璃；透明模式下红绿灯和按钮自动隐藏，鼠标移入浮现
- **默认鼠标穿透**：面板不吃点击，不挡你浏览其他页面。鼠标划过时淡到 12% 让路但仍穿透；按 ⌥⌘A（或点菜单栏）才恢复交互，鼠标离开 1.2 秒后自动回到穿透
- **置顶悬浮**：📌 悬浮在所有窗口（含全屏 Space）之上
- **渠道配置**：⚙️ 勾选哪些 App 显示/隐藏，保存到 `~/.agent-panel-config.json`
- **任务跳转**：点卡片通过 URL scheme 跳回对应 Agent（codex://、cue:// 等）
- **完成通知**：任务从执行中变已完成时发系统通知
- **开机自启**：菜单一键开关，通过 LaunchAgent 实现

## v0.4.0 更新

- **三平台同版发布**：同一个 tag 产出 macOS Universal DMG、Windows x64 安装包和 Linux x64 AppImage
- **后端随包分发**：Windows/Linux 安装包内含 Python 服务，无需另外安装 Python
- **共享任务契约**：桌面客户端使用版本化本地 API，任务状态规则与 macOS 一致
- **下载可校验**：每个 Release 附带 `SHA256SUMS`，上传后自动回查
- **测试范围**：macOS 已实测；Windows/Linux 目前是 CI 构建的预览版，尚未实机验证

→ 完整历史：[CHANGELOG.md](CHANGELOG.md)

## 支持的 App

**编程 Agent**（读取本地会话文件，展示真实明细）：

| Agent | 状态 | 任务详情 | 数据来源 |
|---|---|---|---|
| Codex | ✅ 完整 | ✅ 最近对话/进展 | `~/.codex/sessions` JSONL |
| Claude Code | ✅ 完整 | ✅ 最近回复 | `~/.claude/projects` JSONL |
| DeepSeek Harness | ✅ 完整 | ✅ 会话标题 + 首条提问 | `~/.dsh/sessions` zstd JSONL |
| Cue | ✅ 完整 | ✅ 实时工作文本 | `~/Library/Application Support/Cue/SessionStore/sessions.sqlite` |
| Grok Bot | ✅ 完整 | ✅ 会话最近消息 | `~/Library/Application Support/Grok Bot/sand-client-persistence/*.blob` |

**对话类 Agent**：

| Agent | 状态 | 任务详情 | 数据来源 |
|---|---|---|---|
| Today | ✅ 完整 | ✅ 最近聊天标题 + 活跃度 | `~/Library/Application Support/ai.today.macos.app/chat_*.sqlite` |
| Today CN | ✅ 完整 | ✅ 最近聊天标题 + 活跃度 | `Today 2.app`（同结构，国内版） |
| Muse | ⚠️ 仅在线 | ❌ 任务在厂商服务端执行 | 进程检测 |
| ChatGPT | ⚠️ 仅在线 | ❌ 任务在厂商服务端执行 | 进程检测 |

「完整」= 面板读取本地会话文件，能显示真实任务标题和最近内容。

Cue、Grok Bot、Today、Muse、ChatGPT 仅支持 macOS。Windows/Linux 只显示 Codex、
Claude Code 和 DeepSeek Harness，其他渠道依赖 macOS 专有的本地存储或 URL scheme。

## 隐私

面板只**读取**上面列出的路径来推断会话状态，从不写它们、从不上传任何数据、完全离线可用。唯一涉及网络的端点是 `127.0.0.1:8765` —— 它自己的本地 API。

## 从源码构建

**macOS（原生 Swift App）**

```bash
git clone https://github.com/Jascenn/agent-task-panel.git
cd agent-task-panel
zsh scripts/build.sh
open AgentTaskPanel.app
```

要求：macOS 12+（Apple Silicon 或 Intel），Xcode Command Line Tools（`xcode-select --install`）。

也可以直接浏览器打开面板：`http://127.0.0.1:8765`。

**Windows / Linux（Electron 桌面壳）**

```bash
cd desktop
npm ci
python3 -m pip install pyinstaller
node scripts/sync-resources.mjs
npm run backend
npm test
npm run dist
```

要求 Node.js 22.12+、Python 3.12。产物在 `desktop/dist/`。Windows 安装包需在 Windows
上构建，AppImage 需在 Linux 上构建。

## 官网自动部署

`docs/` 目录的改动合并到 `main` 后，会通过 GitHub Actions 自动部署到 Cloudflare Pages。
工作流位于 `.github/workflows/deploy-pages.yml`，使用仅限 Cloudflare Pages 的 API Token
（GitHub Secret：`CLOUDFLARE_API_TOKEN`）和账户 ID（GitHub Variable：
`CLOUDFLARE_ACCOUNT_ID`），仓库内不会保存任何 Cloudflare 凭据。

## 安全自动化

CodeQL 会在 Pull Request、`main` 和每周计划任务中扫描 Swift、Python 与 GitHub Actions。
Dependabot 漏洞提醒和自动安全修复已启用；发布 tag 前会校验三平台安装包、随包后端和
合并校验和，上传后还会再次检查 Release 资产。

## 配置文件

`~/.agent-panel-config.json`（面板 ⚙️ 菜单可视化配置）：

```json
{ "hidden": ["today"] }
```

## 已知限制

- Muse / ChatGPT 的任务在服务端执行，只能显示"应用在线"，本地无任务明细
- 会话标题取自首条用户消息，注入的系统上下文（AGENTS.md 等）已自动过滤
- App 暂为 ad-hoc 签名，取得 Apple 开发者账号后会接入正式签名 + 公证
- Windows/Linux 当前仅发布 x64；暂不提供 Windows ARM64
- 目前只有 macOS 经过实际使用测试；Windows/Linux 是 CI 构建的预览版，尚未实机验证

## 开发者文档

构建、签名、发布流程见 [docs/dev/BUILD-RELEASE.zh-CN.md](docs/dev/BUILD-RELEASE.zh-CN.md)。

提交与安全规则见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [SECURITY.md](SECURITY.md)。

## License

[MIT](LICENSE) © 2026 Jascenn
