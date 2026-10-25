# Changelog

All notable changes to this project will be documented in this file.

## [0.2.3] - 2026-10-26

### Added
- Standard macOS app menu bar (About / Settings ⌘, / Refresh data ⌘R / Hide / Quit; Window and Help menus with ⌘M show panel)

### Fixed
- Repo restructure follow-up: panel.html is a bundled asset and now lives in `resources/`
- Removed the "Other AI apps" section from the READMEs (Noi is not an agent)
## [0.2.2] - 2026-10-26

### Added
- Window position memory: the panel reopens exactly where you left it (standard NSWindow frame autosave)

### Changed
- App icon: custom macOS-style squircle icon (task cards + status dots) replacing the placeholder

## [0.2.1] - 2026-10-26

### Fixed
- Data service auto-restart: a watchdog health-checks the local API every 5 s and relaunches server.py if it dies; previously a crashed server left the panel stuck on "service not responding" until manual restart
- Error banner now shows the correct command (`python3 server.py` from the repo root)

### Changed
- Menu bar icon replaced with a monochrome SF Symbol template image that adapts to light/dark menu bars; running-task count stays as text next to it

## [0.2.0] - 2026-10-25

### Added
- Menu bar item (🤖) showing live running-task count, polling the local API every 10 s
- Menu bar menu: show panel / pin toggle / launch-at-login toggle / refresh data / quit
- Closing the window now hides the panel instead of quitting while the menu bar item is active; reopen it from the menu bar

## [0.1.0] - 2026-10-25

First working release, daily-driver quality.

### Added
- Floating panel (Swift NSPanel) aggregating AI agent task status from local session files
- Real session detail scanning:
  - Codex (`~/.codex/sessions` JSONL): status from task_complete marker + file activity, recent progress as subtitle
  - Claude Code (`~/.claude/projects` JSONL): last user/assistant timestamps, recent reply as subtitle
  - Cue (`SessionStore/sessions.sqlite`): custom binary format reverse-engineered — agentStatus / brief / live subtask text
  - Grok Bot (`sand-client-persistence/*.blob`): session list with titles and last message
- Online-only agents (Muse, ChatGPT, Today, Noi): process detection with honest "app online, no local detail" subtitle
- Traffic-light status dots (green=running blink, gray=done, yellow=idle) with per-agent accent colors
- Three-state stat filters (running / done / idle), click again to clear
- Pin-to-top toggle (global floating level, verified via CGWindowList)
- Background modes: frost → clear → solid, persisted in localStorage
- Transparent mode: system traffic lights and all buttons auto-hide; hover re-shows (native NSTrackingArea + WKWebView message channel)
- Per-channel visibility config (`~/.agent-panel-config.json`) covering all 8 agents, including ones with no current tasks
- Click-through to agent via URL schemes (codex://, cue://, sand://, hatch://, today://, noi://), custom schemes intercepted in NavDelegate so the panel WebView never navigates away
- System notification when a task transitions running → done
- Launch-at-login toggle (LaunchAgent) and data-service refresh from Dock menu

### Fixed
- Pin watcher deallocated (weak self) so pinning silently never worked
- Drag strip hitTest swallowed clicks on stat cards below the titlebar
- Same-frame `location.href` deep links crashed the panel WebView
- Duplicate placeholder entries when a detail-scanned channel also matched process detection
- Server 500 after removing legacy Cue parsing (leftover reference)
- Inline opacity on pin/background buttons defeating hover-reveal CSS in transparent mode

### Known limitations
- Muse / ChatGPT / Today / Noi run tasks server-side; no local task detail available
- Session titles derive from the first user message; injected context (AGENTS.md etc.) is filtered heuristically
