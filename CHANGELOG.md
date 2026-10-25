# Changelog

All notable changes to this project will be documented in this file.

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
