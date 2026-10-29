# 本地 API 契约 v1

该契约是 macOS 面板与未来 Windows/Linux 客户端共用的数据边界。核心字段在 v1 内保持向后兼容；
渠道可以附加更多字段，但客户端不能依赖未写入本契约的字段。

## `GET /api/tasks`

```json
{
  "api_version": 1,
  "pin": true,
  "tasks": [
    {
      "task_id": "d5f3c31f52b6a63c",
      "agent": "codex",
      "title": "修复发布校验",
      "cwd": "/path/to/project",
      "status": "running",
      "mtime": 1793257504.38,
      "link": "codex://threads/example",
      "recent": "正在运行 CI 检查",
      "recent_at": "2026-10-29T07:04:46.655Z"
    }
  ],
  "finished": [
    {
      "task_id": "d5f3c31f52b6a63c",
      "agent": "codex",
      "title": "修复发布校验"
    }
  ]
}
```

| Field | Type | Meaning |
|---|---|---|
| `api_version` | integer | 契约版本，当前为 `1` |
| `pin` | boolean | 面板是否置顶 |
| `tasks` | array | 当前可见任务 |
| `finished` | array | 本轮从 `running` 变为 `done` 的任务，每个转换只下发一次 |
| `task_id` | string | 由 agent、link、cwd、title 派生的稳定 16 位标识 |
| `agent` | string | 渠道 id，与 `GET /api/config` 一致 |
| `title` | string | 主标题 |
| `cwd` | string | 工作目录；应用型 Agent 可为空 |
| `status` | enum | `running` / `done` / `idle` |
| `mtime` | number | 最近活动 Unix 时间戳 |
| `link` | string | 点击任务时使用的 deep link；可为空 |
| `recent` | string | 副标题或最近一条进展 |
| `recent_at` | string | 最近进展的 ISO8601 时间；未知时为空字符串 |

机器可读定义：[`docs/api/tasks-v1.schema.json`](../api/tasks-v1.schema.json)。

## `GET /api/config`

返回 `api_version`、可选渠道清单 `agents` 和当前隐藏渠道 `hidden`。

## `GET /api/health`

返回 `api_version`、`platform`、`pid` 和构建指纹 `build`。

## 兼容规则

- 新增可选字段属于兼容变更。
- 删除字段、改名或修改状态枚举属于破坏性变更，必须提升 `api_version`。
- 同一 `task_id` 在一次运行内应保持稳定，用于完成通知和客户端选择状态。
