<div align="center">

<img src="docs/appicon.png" width="112" alt="AgentTaskPanel">

# AgentTaskPanel

### One floating panel for every AI Agent's task status

**Where is Codex? Did Claude Code finish?**<br>
Stop alt-tabbing. One always-on panel aggregates every AI agent's session state —<br>
you get a notification when a task finishes, and clicking a card jumps straight back to that agent.

[![Release](https://img.shields.io/github/v/release/Jascenn/agent-task-panel?label=release&color=111111)](https://github.com/Jascenn/agent-task-panel/releases/latest)
[![Stars](https://img.shields.io/github/stars/Jascenn/agent-task-panel?style=flat&color=111111)](https://github.com/Jascenn/agent-task-panel/stargazers)
[![License](https://img.shields.io/badge/license-MIT-111111)](LICENSE)
![macOS](https://img.shields.io/badge/macOS-12%2B-000000?logo=apple&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-x64-000000?logo=windows&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-x64-000000?logo=linux&logoColor=white)

**[Website](https://agentpanel.lingyi.tools/)** · [Download](https://github.com/Jascenn/agent-task-panel/releases/latest) · [Features](#features) · [Supported apps](#supported-apps) · [Build from source](#build-from-source) · [简体中文](README.zh-CN.md)

| Clear | Solid | Frost |
|---|---|---|
| ![Clear on white](docs/screenshots/screenshot-clear.jpg) | ![Solid](docs/screenshots/screenshot-solid.jpg) | ![Frost](docs/screenshots/screenshot-frost.jpg) |

</div>

## Install

> **Platform testing status:** only the macOS build has been tested in real use.
> Windows x64 and Linux x64 are built and smoke-tested in CI, but have not yet been
> validated on real Windows or Linux machines. Please treat them as preview builds.

Download the package for your platform from [Releases](https://github.com/Jascenn/agent-task-panel/releases/latest):

| Platform | Package |
|---|---|
| macOS 12+ | `AgentTaskPanel-0.4.0-macos-universal.dmg` |
| Windows x64 | `AgentTaskPanel-0.4.0-win-x64.exe` |
| Linux x64 | `AgentTaskPanel-0.4.0-linux-x86_64.AppImage` |

**macOS**: open the DMG and drag 🤖 AgentTaskPanel into Applications. If macOS says it
"cannot be verified", right-click the app → Open, or run
`xattr -dr com.apple.quarantine /Applications/AgentTaskPanel.app`.

**Windows**: run the installer. SmartScreen may ask you to confirm because the build is not
code-signed.

**Linux**: make the AppImage executable, then launch it:

```bash
chmod +x AgentTaskPanel-0.4.0-linux-x86_64.AppImage
./AgentTaskPanel-0.4.0-linux-x86_64.AppImage
```

The local data service starts with the app. On macOS, a 🤖 menu bar item shows the number of
running tasks; Windows and Linux have a tray icon. All builds verify `SHA256SUMS` before release.

## Features

- **Live status**: each agent's own turn boundaries decide running / done / idle; an adaptive stale-session timeout only downgrades abandoned runs
- **Menu bar item**: monochrome template icon with a live running-task count; menu offers show panel / pin / launch-at-login / refresh / quit
- **Crash-proof data service**: a watchdog health-checks the local API every 5 s and silently relaunches it if it dies
- **Three-state filters**: click a stat card to filter running / done / idle, click again to clear
- **Per-agent color dots**: each task carries its agent's accent color, so you can tell sources apart at a glance
- **Three background modes**: clear → solid → frost; in clear mode the traffic lights and buttons auto-hide and reappear on hover
- **Click-through by default**: the panel never eats your clicks. Hovering it fades to 12% and still passes clicks through; press ⌥⌘A (or the menu bar item) to make it interactive, and it returns to click-through 1.2 s after the pointer leaves
- **Pin-to-top**: 📌 keeps the panel floating above everything, including full-screen Spaces
- **Channel visibility**: ⚙️ toggle which apps appear, saved to `~/.agent-panel-config.json`
- **Jump back**: click a card to open the agent via its URL scheme (`codex://`, `cue://`, …)
- **Finish notifications**: a system notification fires when a task transitions running → done
- **Launch at login**: one toggle in the menu, implemented as a LaunchAgent

## What's new in v0.4.0

- **Three platforms, one release**: macOS Universal DMG, Windows x64 installer, and Linux x64 AppImage are built from the same tag
- **Bundled backend**: Windows and Linux packages include the Python service, so no separate Python install is required
- **Shared task contract**: desktop clients use the versioned local API and the same task state rules as macOS
- **Verified downloads**: every release includes `SHA256SUMS` and is checked after upload
- **Platform test status**: macOS is tested; Windows and Linux are CI-built preview builds, not yet validated on real devices

→ Full history: [CHANGELOG.md](CHANGELOG.md)

## Supported apps

**Coding agents** (real session detail from local files):

| Agent | Status | Detail | Data source |
|---|---|---|---|
| Codex | ✅ Full | ✅ recent prompts / progress | `~/.codex/sessions` JSONL |
| Claude Code | ✅ Full | ✅ recent reply | `~/.claude/projects` JSONL |
| DeepSeek Harness | ✅ Full | ✅ session title + first prompt | `~/.dsh/sessions` zstd JSONL |
| Cue | ✅ Full | ✅ live working text | `~/Library/Application Support/Cue/SessionStore/sessions.sqlite` |
| Grok Bot | ✅ Full | ✅ session last message | `~/Library/Application Support/Grok Bot/sand-client-persistence/*.blob` |

**Chat agents**:

| Agent | Status | Detail | Data source |
|---|---|---|---|
| Today | ✅ Full | ✅ last chat title + activity | `~/Library/Application Support/ai.today.macos.app/chat_*.sqlite` |
| Today CN | ✅ Full | ✅ last chat title + activity | `Today 2.app` (same schema, CN build) |
| Muse | ⚠️ Online only | ❌ sessions live on the vendor's server | process detection |
| ChatGPT | ⚠️ Online only | ❌ sessions live on the vendor's server | process detection |

"Full" = the panel reads local session files and shows real task titles plus recent activity.

Cue, Grok Bot, Today, Muse and ChatGPT are macOS-only. On Windows and Linux, only Codex,
Claude Code and DeepSeek Harness are shown because the other channels depend on macOS-specific
storage or URL schemes.

## Privacy

The panel only **reads** the paths listed above to infer session state. It never writes to them, never uploads anything, and works fully offline. The only network endpoint is `127.0.0.1:8765` — its own local API.

## Build from source

**macOS (native Swift app)**

```bash
git clone https://github.com/Jascenn/agent-task-panel.git
cd agent-task-panel
zsh scripts/build.sh
open AgentTaskPanel.app
```

Requires macOS 12+ (Apple Silicon or Intel) and Xcode Command Line Tools (`xcode-select --install`).

You can also open the panel in a browser at `http://127.0.0.1:8765`.

**Windows / Linux (Electron shell)**

```bash
cd desktop
npm ci
python3 -m pip install pyinstaller
node scripts/sync-resources.mjs
npm run backend
npm test
npm run dist
```

Requires Node.js 22.12+ and Python 3.12. Packages are written to `desktop/dist/`. Build the
Windows installer on Windows and the AppImage on Linux.

## Website deployment

Changes under `docs/` are deployed to Cloudflare Pages automatically after they land on `main`.
The workflow is `.github/workflows/deploy-pages.yml`; it uses a Pages-only API token stored in the
repository secret `CLOUDFLARE_API_TOKEN` and the account ID stored in the repository variable
`CLOUDFLARE_ACCOUNT_ID`. No Cloudflare credentials are committed to the repository.

## Security automation

CodeQL analyzes Swift, Python and GitHub Actions on pull requests, `main`, and a weekly schedule.
Dependabot vulnerability alerts and automated security fixes are enabled. Release tags are
published only after all three platform packages, bundled backends, and the combined checksums
have been verified.

## Configuration

`~/.agent-panel-config.json` (editable via the panel's ⚙️ menu):

```json
{ "hidden": ["today"] }
```

## Known limitations

- Muse / ChatGPT execute tasks server-side, so only "app online" can be shown — no local task detail exists
- Session titles come from the first user message; injected system context (AGENTS.md etc.) is filtered out
- The app is ad-hoc signed; Developer ID signing + notarization is planned once there's an Apple developer account
- Windows and Linux support x64 only; Windows ARM64 is not currently published
- Only macOS has been tested in real use; Windows and Linux are CI-built preview builds without real-device validation

## Docs

Build, signing and release workflow: [docs/dev/BUILD-RELEASE.zh-CN.md](docs/dev/BUILD-RELEASE.zh-CN.md) (中文)

Submission and safety rules: [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md)

## License

[MIT](LICENSE) © 2026 Jascenn
