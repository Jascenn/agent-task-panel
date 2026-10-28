# 任务状态判定

面板把每个会话归到三态之一：**执行中（running）/ 已完成（done）/ 空闲（idle）**。
原则：**能读到显式边界事件就用事件，读不到才用超时兜底。**

## 各渠道信号

| 渠道 | 执行中 | 已完成 | 空闲 | 数据来源 |
|---|---|---|---|---|
| Codex | 最后一个 `task_started` 晚于 `task_complete` | 最后一个事件是 `task_complete` / `turn_aborted` | 回合开着但超时无写入 | `~/.codex/sessions/**/*.jsonl` |
| Claude Code | 最后一条是 user 消息，或最后一条 assistant 的 `stop_reason=tool_use` | 最后一条 assistant 的 `stop_reason=end_turn`/`stop_sequence` | 无有效信号且超时 | `~/.claude/projects/**/*.jsonl` |
| DeepSeek Harness | 有 `turn/start` 无 `turn/end` | 最后一个事件是 `turn/end` | 回合开着但超时 | `~/.dsh/sessions/**/session.v4.jsonl.zstd` |
| Cue | `agentStatus=running` | `agentStatus=stopped` | `agentStatus=waiting` | `SessionStore/sessions.sqlite` |
| Today | 最后一条消息 role=user | role=assistant 且 `wireState=completed` | 其他 | `chat_*.sqlite` |
| Grok Bot | `lastActivityAt` 在兜底窗口内 | 超过窗口 | `awaitingUserResponse` 为真 | `sand-client-persistence/*.blob` |

Grok 的 blob 里没有 role/完成字段（实测 `awaitingUserResponse` 全为 `null`），
只能靠活动时间兜底，属于已知精度上限。

## 自适应僵尸超时

有「执行中」信号、但会话长时间没有新写入时，说明进程可能已经退出：

```
阈值 = clamp(p90(该会话历史事件间隔) × 4, 600s, 3600s)
```

- 只用于**降级**（running → idle），不参与正常完成判断
- 下限 600s 来自实测：Codex 回合内静默 p95=287s、p99=1032s，
  阈值取 300s 会把 4.8% 的正常长任务误判成僵尸
- 历史样本不足 3 个间隔时用 900s 兜底
- 降级成 idle **不会**触发「任务完成」通知（只有 running → done 才通知）

## 通知

服务端 `_prev_status` 对比上一轮状态，`running → done` 才进入 `finished` 数组，
每条只发一次；前端只负责弹窗。这样面板窗口关闭（WKWebView 节流）也不会漏发。

## 已知噪音与过滤

Claude Code 会产生两类非用户任务的会话，都在 `parse_claude_file` 里过滤：

1. 子 agent 转录：文件名 `agent-*.jsonl`，且 `isSidechain=true`
2. 工作流 harness：cwd 落在 `~/.claude/projects` 内，或首条用户消息以
   `[Workflow harness — ` 开头；这类文件实测一分钟能刷出十几条

另外标题退化成 `-` 或命令路径回显（`/…/bin/…`）的会话也丢弃。

## 验证方法

```bash
cd <repo>
python3 - <<'PY'
import sys, collections
sys.path.insert(0, 'src'); import server
server._cache['mtime'] = 0
t = server.tasks()['tasks']
print(len(t), dict(collections.Counter(x['status'] for x in t)))
print(dict(collections.Counter(x['agent'] for x in t)))
PY
```

改完状态逻辑至少要确认三件事：总数稳定（不随时间暴涨）、三态分布合理、
没有 `Workflow harness` / 标题为 `-` 的条目。
