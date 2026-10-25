# Security Policy / 安全策略

## Data handling / 数据处理

AgentTaskPanel runs fully locally. It reads agent session files under your home directory (paths listed in the README), serves a UI on `127.0.0.1:8765`, and makes no outbound requests. Nothing is uploaded.

AgentTaskPanel 完全本地运行：只读取主目录下 Agent 会话文件（路径见 README），UI 服务于 `127.0.0.1:8765`，无任何对外请求，不上传任何数据。

## Reporting a vulnerability / 报告漏洞

If you find a security issue (e.g. the local API serving more than intended, path traversal in server.py), please open a [private security advisory](https://github.com/Jascenn/agent-task-panel/security/advisories/new) instead of a public issue.

如果发现安全问题（例如本地 API 暴露面过大、server.py 存在路径穿越），请通过 [私密安全通告](https://github.com/Jascenn/agent-task-panel/security/advisories/new) 报告，不要开公开 issue。

## Known design boundaries / 已知设计边界

- The local API has no authentication by design — it binds to `127.0.0.1` only and reads task metadata. Other local users/processes on your Mac can read the same data
- The app is ad-hoc signed; builds from GitHub Actions use ephemeral runners
