# AgentTaskPanel

macOS 悬浮任务面板：聚合本机所有 AI Agent 的会话/任务状态，实时显示"哪些在跑、跑到哪了"，任务卡点击直接跳回对应 Agent。

| 磨砂模式 | 纯色模式 | 透明模式 |
|---|---|---|
| ![磨砂](docs/screenshot-frost.jpg) | ![纯色](docs/screenshot-solid.jpg) | ![透明](docs/screenshot-clear.jpg) |

透明模式下红绿灯与功能按钮自动隐藏，鼠标移入窗口时浮现。

## 支持的 Agent

| Agent | 状态 | 详情（副标题） | 数据来源 |
|---|---|---|---|
| Codex | ✅ 真实 | ✅ 最近对话/进展 | `~/.codex/sessions` JSONL |
| Claude Code | ✅ 真实 | ✅ 最近回复 | `~/.claude/projects` JSONL |
| Cue | ✅ 真实 | ✅ 实时工作文本 | `~/Library/Application Support/Cue/SessionStore/sessions.sqlite` |
| Grok Bot | ✅ 真实 | ✅ 会话最近消息 | `~/Library/Application Support/Grok Bot/sand-client-persistence/*.blob` |
| Muse | ⚠️ 在线状态 | ❌ 无本地明细 | 进程检测（任务在 Meta 服务端执行） |
| ChatGPT | ⚠️ 在线状态 | ❌ 无本地明细 | 进程检测 |
| Today / Noi | ⚠️ 在线状态 | ❌ 无本地明细 | 进程检测 |

## 功能

- **状态推断**：会话文件 120 秒内有写入 = 执行中；有完成标记 = 已完成；其余 = 空闲
- **三态筛选**：点统计卡筛选执行中/已完成/空闲，再点取消
- **置顶**：📌 开关，全局悬浮（含全屏 Space）
- **背景三态**：毛玻璃 → 全透明 → 纯色；透明模式下红绿灯和所有按钮自动隐藏，鼠标移入浮现
- **渠道配置**：⚙️ 勾选哪些渠道显示/隐藏，保存到 `~/.agent-panel-config.json`
- **任务跳转**：点卡片通过 URL scheme 跳回对应 Agent（codex://、cue:// 等）
- **完成通知**：任务从执行中变已完成时发系统通知

## 构建与运行

```bash
git clone https://github.com/Jascenn/agent-task-panel.git
cd agent-task-panel
zsh build.sh
open AgentTaskPanel.app
```

要求：macOS 13+，Xcode Command Line Tools（swiftc）。

首次启动会请求通知权限；本地数据服务运行在 `http://127.0.0.1:8765`，也可以直接浏览器打开。

## 配置文件

`~/.agent-panel-config.json`：

```json
{ "hidden": ["today", "noi"] }
```

## 已知限制

- Muse / ChatGPT 等服务端执行的 Agent 只能显示"应用在线"，无法读取任务明细（本地无数据）
- 会话标题取自首条用户消息，注入的系统上下文（AGENTS.md 等）已自动过滤

## License

MIT
