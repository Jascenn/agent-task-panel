#!/usr/bin/env python3
# 本地任务聚合服务：扫描 Codex / Claude Code 会话，输出 JSON
import json, os, glob, time, re, struct, sqlite3, subprocess, datetime, hashlib
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from platforms import detect_runtime

HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent-task-dashboard.html")

RUNTIME = detect_runtime()
HOME = RUNTIME.home
CODEX_DIR = RUNTIME.codex_dir
CLAUDE_DIR = RUNTIME.claude_dir
DSH_DIR = RUNTIME.dsh_dir
PIN_FLAG = RUNTIME.pin_flag
CONFIG_PATH = RUNTIME.config_path
PID_PATH = RUNTIME.pid_path
API_VERSION = 1
TASK_STATUSES = {"running", "done", "idle"}

# 构建标识：App 启动时用同一个算法算自己 bundle 里 server.py 的指纹并传进来。
# 端口上若跑着指纹不同的旧进程（重装后常见），App 会杀掉它再拉起新服务，
# 否则面板会静默显示旧代码产出的数据。
def build_id(path):
    h = 0xcbf29ce484222325
    try:
        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(65536)
                if not chunk:
                    break
                for b in chunk:
                    h = ((h ^ b) * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    except OSError:
        return "0"
    return "%016x" % h

BUILD_ID = "0"
SCAN_AGE = 24 * 3600     # 只看 24 小时内的会话

# 僵尸判定：有"执行中"信号但会话已无进展 → 进程已崩/已退出，降级 idle。
# 阈值按会话自身的事件间隔自适应（p90 × 4），并用上下限夹住。
# 实测回合内静默 p95=287s / p99=1032s，所以下限取 600s，避免把长构建误判成僵尸。
ZOMBIE_MIN = 600
ZOMBIE_MAX = 3600
ZOMBIE_FACTOR = 4
ZOMBIE_DEFAULT = 900     # 历史样本不足时的兜底

_cache = {"data": [], "mtime": 0.0}   # 短缓存，避免轮询间隔重复扫描
# 完成通知：服务端对比 running→done，避免面板关窗时 WKWebView 节流漏发
# 完成通知按稳定 task_id 对比，避免同一 Agent 下重复标题互相覆盖。
_prev_tasks = {}

# 增量缓存：文件路径 -> (mtime, 解析结果)；未变化的文件直接复用
_file_cache = {"codex": {}, "claude": {}, "dsh": {}}

def first_text(text):
    return re.sub(r"\s+", " ", str(text)).strip()[:60]


def normalize_task(task):
    """把各渠道的扫描结果收敛成跨平台客户端可依赖的任务契约。"""
    agent = str(task.get("agent") or "").strip()
    if not agent:
        return None
    title = first_text(task.get("title") or "") or "未命名任务"
    cwd = str(task.get("cwd") or "")
    link = str(task.get("link") or "")
    status = str(task.get("status") or "idle")
    if status not in TASK_STATUSES:
        status = "idle"
    try:
        mtime = float(task.get("mtime") or 0)
    except (TypeError, ValueError):
        mtime = 0.0
    identity = "\x1f".join((agent, link, cwd, title))
    normalized = {
        **task,
        "task_id": hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16],
        "agent": agent,
        "title": title,
        "cwd": cwd,
        "status": status,
        "mtime": mtime,
        "link": link,
        "recent": str(task.get("recent") or ""),
        "recent_at": str(task.get("recent_at") or ""),
    }
    return normalized


def parse_ts(value):
    """ISO8601 → epoch 秒；无法解析返回 None。"""
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def zombie_threshold(timestamps):
    """按会话自身的事件间隔算僵尸阈值：p90 * 4，夹在 600~3600 秒之间。

    自适应只用于识别"有执行中信号但已无写入"的僵尸进程，
    不参与正常完成判断——完成一律由各渠道的显式边界事件决定。
    """
    gaps = [b - a for a, b in zip(timestamps, timestamps[1:]) if 0 < b - a < 3600]
    if len(gaps) < 3:
        return ZOMBIE_DEFAULT
    gaps.sort()
    p90 = gaps[int(len(gaps) * 0.9)]
    return max(ZOMBIE_MIN, min(ZOMBIE_MAX, p90 * ZOMBIE_FACTOR))


def demote_if_zombie(status, mtime, threshold, now=None):
    """有执行中信号但长时间无写入 → idle（进程大概率已退出）。"""
    if status != "running":
        return status
    now = time.time() if now is None else now
    return "idle" if now - mtime > threshold else status


def load_config():
    try:
        with open(CONFIG_PATH) as fh:
            return json.load(fh)
    except Exception:
        return {}


def clean_title(text):
    # 跳过注入的 AGENTS.md / system-reminder 等非用户输入
    text = str(text)
    s = text.lstrip()
    if s.startswith(("# AGENTS.md", "<INSTRUCTIONS>", "<system-reminder>", "<environment_context>", "<external_", "# Files mentioned")):
        return None
    # markdown 前缀 / 系统角色文本 / 报错日志开头的"消息"不是合理任务名
    if s.startswith(("## ", "# ", "**", "You are ", "<", "{", "```")):
        return None
    if s.startswith("<in-app-browser-context") or "source=\"ambient-ui-state\"" in s[:200]:
        # 环境状态块后面跟着真实请求，取正文末段
        tail = re.split(r"</in-app-browser-context>", s)[-1].strip()
        if tail and not tail.startswith("<"):
            return first_text(tail)
        return None
    return first_text(text)

# ============ App 型 agent ============
# 进程名 -> (显示名, deep link, 是否有本地明细)
# Today 两个版本：进程名 Today 2 = 国内版；两个同时在跑才区分 id，单独在跑统称 today
APP_AGENTS = {
    "ChatGPT": ("ChatGPT", "codex://", False),
    "Grok Bot": ("Grok Bot", "sand://", False),
    "Muse": ("Muse", "hatch://", False),
    "Cue": ("Cue", "cue://", True),
    "Today": ("Today", "today://", True),
    "Today 2": ("Today 国内", "today://", False),
}

# 本地会话型渠道在所有平台可用。
BASE_AGENTS = [
    {"id": "codex", "name": "Codex"},
    {"id": "claude", "name": "Claude Code"},
    {"id": "deepseek", "name": "DeepSeek Harness"},
]

# 这些条目依赖 macOS 应用目录和进程名。
NATIVE_APP_AGENTS = [
    {"id": "chatgpt", "name": "ChatGPT"},
    {"id": "grok-bot", "name": "Grok Bot"},
    {"id": "muse", "name": "Muse"},
    {"id": "cue", "name": "Cue"},
    {"id": "today", "name": "Today（单版本时）"},
    {"id": "today-intl", "name": "Today Intl"},
    {"id": "today-cn", "name": "Today CN"},
]

def all_agents(runtime=RUNTIME):
    agents = list(BASE_AGENTS)
    if runtime.supports_native_apps:
        agents.extend(NATIVE_APP_AGENTS)
    return agents


# 全渠道清单（配置面板用）：即使当前无任务也应可配置
ALL_AGENTS = all_agents()

def proc_alive(name):
    if not RUNTIME.supports_native_apps:
        return False
    r = subprocess.run(["pgrep", "-x", name], capture_output=True)
    if r.returncode == 0:
        return True
    r = subprocess.run(["pgrep", "-f", f"Applications/{name}.app"], capture_output=True)
    return r.returncode == 0


def _cue_str(blob, key):
    # Cue 自定义二进制：'c'+len(字节) 后跟 UTF-16LE 文本；'"'+len 后跟 ASCII
    i = blob.find(key)
    if i < 0:
        return None
    j = i + len(key)
    if blob[j:j+1] == b"\x00":
        j += 1
    try:
        if blob[j:j+1] == b"c":
            n = blob[j+1]
            return blob[j+2:j+2+n].decode("utf-16-le", errors="ignore").strip() or None
        if blob[j:j+1] == b'"':
            n = blob[j+1]
            return blob[j+2:j+2+n].decode("utf-8", errors="ignore").strip() or None
    except Exception:
        return None
    return None


def scan_cue():
    # cache_events: statusUpdate(agentStatus/brief/description) + subtaskLiveStatus(text)
    db = os.path.expanduser("~/Library/Application Support/Cue/SessionStore/sessions.sqlite")
    sessions = {}
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        for sid, ts, rec in con.execute(
                "SELECT session, timestamp, record FROM cache_events ORDER BY timestamp"):
            st = sessions.setdefault(sid, {"mtime": 0})
            st["mtime"] = max(st["mtime"], ts / 1000)
            if rec.find(b"statusUpdate") > 0:
                s = _cue_str(rec, b"agentStatus")
                if s:
                    st["status"] = s
                for k, key in (("brief", b"brief"), ("desc", b"description")):
                    v = _cue_str(rec, key)
                    if v:
                        st[k] = v
            if rec.find(b"subtaskLiveStatus") > 0:
                t = _cue_str(rec, b"text")
                if t:
                    st["live"] = t
        for meta, in con.execute("SELECT metadata FROM cache_sessions"):
            m = re.search(rb"[A-Za-z0-9]{21}", meta[:60])
            t = _cue_str(meta, b"title")
            if m and t:
                sid = m.group(0).decode()
                if sid in sessions:
                    sessions[sid]["title"] = t
        con.close()
    except Exception:
        return []
    out = []
    now = time.time()
    for sid, st in sessions.items():
        if now - st["mtime"] > SCAN_AGE or not (st.get("title") or st.get("brief")):
            continue
        # Cue 自带 agentStatus 三态：running / waiting / stopped
        agent_status = st.get("status", "")
        if agent_status == "running":
            status = "running"
        elif agent_status == "waiting":
            # 等用户或等外部资源，不是完成——旧代码把它算成 done，是假通知来源
            status = "idle"
        elif agent_status == "stopped":
            status = "done"
        else:
            # 没有状态事件的老会话：只能靠写入时间兜底
            status = "running" if now - st["mtime"] < ZOMBIE_DEFAULT else "idle"
        recent = st.get("live") or st.get("desc") or st.get("brief") or ""
        # title 缺失时用会话 id 短码，brief 留给副标题（brief 是状态描述不是标题）
        out.append({"agent": "cue", "title": st.get("title") or "Cue · " + sid[:6],
                    "cwd": "", "status": status,
                    "mtime": st["mtime"], "link": "cue://", "recent": recent, "recent_at": ""})
    return out


def scan_grok():
    # Electron blob 持久化：JSON rows 含会话标题/最近消息/活动时间
    d = os.path.expanduser("~/Library/Application Support/Grok Bot/sand-client-persistence")
    files = sorted(glob.glob(os.path.join(d, "*.blob")), key=os.path.getmtime)
    rows = {}
    for f in files[-8:]:
        try:
            for r in json.loads(open(f, "rb").read()).get("value", {}).get("rows", []):
                if isinstance(r, dict) and r.get("id"):
                    rows[r["id"]] = r
        except Exception:
            continue
    out = []
    now = time.time()
    for r in rows.values():
        act = r.get("lastActivityAt") or r.get("updatedAt")
        if not act:
            continue
        mtime = act / 1000 if act > 1e12 else act
        if now - mtime > SCAN_AGE:
            continue
        last = r.get("lastEntry") or {}
        recent = first_text(last.get("text") or (last.get("sessionPreview") or {}).get("text", "")) if isinstance(last, dict) else ""
        # Grok 的 blob 里没有 role/完成字段（awaitingUserResponse 实测全为 null），
        # 只有一个 lastActivityAt。用僵尸兜底窗口判断：窗口内算执行中，超过算已完成。
        if r.get("awaitingUserResponse"):
            status = "idle"
        elif now - mtime < ZOMBIE_DEFAULT:
            status = "running"
        else:
            status = "done"
        out.append({"agent": "grok-bot", "title": first_text(r.get("name") or r.get("title") or "Grok 会话"),
                    "cwd": "", "status": status, "mtime": mtime, "link": "sand://",
                    "recent": recent, "recent_at": ""})
    return out

def scan_apps():
    if not RUNTIME.supports_native_apps:
        return []
    out = []
    today_intl_alive = proc_alive("Today")
    today_cn_alive = proc_alive("Today 2")
    today_split = today_intl_alive and today_cn_alive
    # Today: chat sqlite 最近活动（文件名含设备 hash，动态发现）
    today_dbs = sorted(
        glob.glob(os.path.expanduser(
            "~/Library/Application Support/ai.today.macos.app/chat_*.sqlite")),
        key=os.path.getmtime)
    today_db = today_dbs[-1] if today_dbs else None
    today_title, today_mtime = None, 0
    today_last_role, today_wire_state = "", ""
    try:
        con = sqlite3.connect(f"file:{today_db}?mode=ro", uri=True)
        for (payload,) in con.execute(
                "SELECT payload FROM chatMessage ORDER BY messageIndex DESC LIMIT 40"):
            try:
                d = json.loads(payload)
            except Exception:
                continue
            ts = d.get("createdAt", 0) / 1000
            if ts > today_mtime:
                today_mtime = ts
                # 最后一条消息的角色：assistant 已回复=完成，user 等回复=执行中
                today_last_role = d.get("role") or ""
                today_wire_state = d.get("wireState") or ""
            if d.get("role") == "user" and not today_title:
                parts = d.get("parts") or [{}]
                t = parts[0].get("text", "")
                if t and not t.startswith("<"):
                    today_title = first_text(t)
        con.close()
    except Exception:
        pass
    for proc, (name, link, detail) in APP_AGENTS.items():
        alive = proc_alive(proc)
        if not alive:
            continue
        if proc == "Today" and today_mtime:
            age = time.time() - today_mtime
            if today_last_role == "assistant" and today_wire_state == "completed":
                status = "done"
            elif today_last_role == "user":
                # 用户发了消息、助手还没回：执行中（超时则降级 idle）
                status = demote_if_zombie("running", today_mtime, ZOMBIE_DEFAULT)
            else:
                status = "idle"
            agent_id = "today-intl" if today_split else "today"
            display = "Today Intl" if today_split else "Today"
            out.append({"agent": agent_id, "title": today_title or "今日助手", "cwd": "",
                        "status": status, "mtime": today_mtime,
                        # 两个版本都注册 today://，点击必须带 bundle id 才能落到正确 App
                        "link": "today://" if not today_split else "today://?bundle=ai.today.macos.app"})
        else:
            if proc == "Today 2":
                agent_id, display = ("today-cn", "Today CN") if today_split else ("today", "Today")
                # 单版本时装的是哪个就是哪个：Today 2 存在则 bundle 固定
                today_link = "today://?bundle=ai.today.macos.app.cn"
            else:
                agent_id = proc.lower().replace(" ", "-")
                display = name
                today_link = link
            # 无本地明细的 app 型 agent：任务在服务端执行，本地只能确认进程活跃
            # 状态用 running 表示"应用在线"，副标题注明数据边界，避免伪造空闲/完成
            out.append({"agent": agent_id, "title": f"{display} 运行中", "cwd": "",
                        "status": "running", "mtime": time.time(),
                        "link": today_link, "recent": "应用在线 · 无本地任务明细", "recent_at": ""})
    # Cue / Grok 有本地明细：扫描真实会话（进程退出后 24h 记录仍可见）
    out.extend(scan_cue())
    out.extend(scan_grok())
    # 有真实明细的渠道去掉"应用在线"占位条目，避免重复
    scanned = {t["agent"] for t in out if t.get("recent") != "应用在线 · 无本地任务明细"}
    out = [t for t in out if t["agent"] not in scanned or t.get("recent") != "应用在线 · 无本地任务明细"]
    return out


def _dsh_proc_alive():
    # 主进程名带空格，pgrep -x 匹配不到；按路径匹配
    r = subprocess.run(["pgrep", "-f", "DeepSeek Harness.app/Contents/MacOS/DeepSeek Harness$"],
                       capture_output=True)
    return r.returncode == 0


def scan_dsh():
    # DeepSeek Harness 会话：zstd 压缩的 v4 jsonl；turn/start → turn/end 是回合边界
    out = []
    now = time.time()
    for f in glob.glob(os.path.join(DSH_DIR, "*", "*", "session.v4.jsonl.zstd")):
        mtime = os.path.getmtime(f)
        if now - mtime > SCAN_AGE:
            continue
        cached = _file_cache["dsh"].get(f)
        if cached and cached[0] == mtime:
            out.append(cached[1])
            continue
        title, recent = None, ""
        turn_open, turn_ts = False, []
        try:
            raw = subprocess.run(["zstd", "-dc", f], capture_output=True, timeout=10).stdout
        except Exception:
            raw = b""
        for line in raw.decode("utf-8", "ignore").splitlines():
            head = line[:600]
            if not ('"session/title"' in head or '"user/message"' in head
                    or '"turn/start"' in head or '"turn/end"' in head):
                continue
            try:
                j = json.loads(line)
            except Exception:
                continue
            t, d = j.get("type"), j.get("data") or {}
            ts = parse_ts(j.get("timestamp") or j.get("time") or d.get("timestamp"))
            if ts:
                turn_ts.append(ts)
            if t == "session/title" and not title and d.get("title"):
                title = first_text(d["title"])
            elif t == "user/message" and not recent:
                parts = d.get("content") or [{}]
                txt = parts[0].get("text", "") if isinstance(parts[0], dict) else ""
                # 跳过运行时上下文/系统注入的伪用户消息
                if txt and not txt.startswith(("<", "Current runtime", "Current DSH")):
                    recent = first_text(txt)
            elif t == "turn/start":
                turn_open = True
            elif t == "turn/end":
                turn_open = False
        if not (title or recent):
            continue
        if turn_open:
            # 回合开着但久无写入 → 进程大概率已退出
            status = demote_if_zombie("running", mtime, zombie_threshold(turn_ts))
        else:
            status = "done"
        # 状态在读取时计算，缓存里存的是快照；mtime 未变则状态也不会变
        task = {"agent": "deepseek", "title": title or recent or "DeepSeek 会话",
                "cwd": "", "status": status,
                "mtime": mtime, "link": "dsh://",
                "recent": recent if title else "", "recent_at": ""}
        _file_cache["dsh"][f] = (mtime, task)
        out.append(task)
    return out

def parse_codex_file(f):
    tid = re.search(r"-([0-9a-f-]{36})\.jsonl$", f)
    title, cwd, complete_at, last_ev = None, None, "", ""
    recent, recent_at = "", ""
    # 回合边界用事件顺序判断，而不是比较时间戳：
    # task_complete 之后还会写 token_count 等统计事件，比时间戳会失效。
    turn_open = False
    ev_ts = []
    try:
        with open(f, errors="ignore") as fh:
            for line in fh:
                head = line[:600]
                if not ('turn_context' in head or 'user_message' in head or 'item_completed' in head
                        or 'task_complete' in head or 'task_started' in head or 'turn_aborted' in head):
                    continue
                try:
                    j = json.loads(line)
                except Exception:
                    continue
                ts = j.get("timestamp", "")
                p = j.get("payload", {}) or {}
                ts_epoch = parse_ts(ts)
                if ts_epoch:
                    ev_ts.append(ts_epoch)
                if j.get("type") == "turn_context" and not cwd:
                    cwd = p.get("cwd")
                if j.get("type") == "event_msg":
                    pt = p.get("type")
                    if pt == "task_started":
                        turn_open = True
                    elif pt == "task_complete":
                        turn_open = False
                        complete_at = ts
                    elif pt == "turn_aborted":
                        # 用户中断也视为回合结束
                        turn_open = False
                    if pt == "user_message" and not title:
                        title = clean_title(p.get("message", ""))
                    if pt == "user_message":
                        t2 = clean_title(p.get("message", ""))
                        if t2:
                            recent, recent_at = t2, ts
                    if pt == "item_completed" and not title:
                        item = p.get("item") or {}
                        if item.get("type") in ("message", "UserMessage") and item.get("role") in ("user", None):
                            for c in item.get("content") or []:
                                txt = c.get("text") if isinstance(c, dict) else None
                                if txt:
                                    t2 = clean_title(txt)
                                    if t2:
                                        title = t2
                                    break
                    if pt == "item_completed":
                        item = p.get("item") or {}
                        for c in item.get("content") or []:
                            txt = c.get("text") if isinstance(c, dict) else None
                            if txt and item.get("role") != "user":
                                recent, recent_at = first_text(txt), ts
                                break
                    if ts:
                        last_ev = ts
    except OSError:
        pass
    # 无标题会话用项目目录名兜底，避免"(Codex 会话)"占位
    fallback = "/".join((cwd or "").rstrip("/").split("/")[-2:]) if cwd else "Codex 会话"
    return [{
        "agent": "codex", "title": title or fallback, "cwd": cwd or "",
        "mtime": os.path.getmtime(f),
        "link": ("codex://threads/" + tid.group(1)) if tid else "codex://",
        "complete_at": complete_at, "last_ev": last_ev,
        "turn_open": turn_open, "ev_ts": ev_ts,
        "recent": recent, "recent_at": recent_at,
    }]

def scan_codex():
    now = time.time()
    out = []
    for f in glob.glob(os.path.join(CODEX_DIR, "**/*.jsonl"), recursive=True):
        mtime = os.path.getmtime(f)
        if now - mtime > SCAN_AGE:
            continue
        cached = _file_cache["codex"].get(f)
        if cached and cached[0] == mtime:
            r = cached[1]
        else:
            r = parse_codex_file(f)
            _file_cache["codex"][f] = (mtime, r)
        for t in r:
            t = dict(t)
            t["mtime"] = os.path.getmtime(f)
            if t["turn_open"]:
                # 回合开着：正常是执行中，久无写入则判定进程已退出
                t["status"] = demote_if_zombie("running", t["mtime"], zombie_threshold(t["ev_ts"]))
            elif t["complete_at"]:
                t["status"] = "done"
            else:
                # 没有回合边界的旧会话（未产生 task_started/task_complete）
                t["status"] = "running" if now - t["mtime"] < ZOMBIE_DEFAULT else "idle"
            t.pop("turn_open", None)
            t.pop("ev_ts", None)
            out.append(t)
    return out

def parse_claude_file(f):
    title, cwd, last_user_ts, last_asst_ts = None, None, "", ""
    recent, recent_at = "", ""
    # 最后一条消息的角色 + 最后一条 assistant 的 stop_reason 决定回合状态：
    # end_turn/stop_sequence = 已回复完；tool_use = 还在跑工具；最后是 user = 等回复
    last_role, last_stop_reason = "", ""
    ev_ts = []
    is_sidechain = False
    try:
        with open(f, errors="ignore") as fh:
            for line in fh:
                head = line[:300]
                if not ('cwd' in head or '"user"' in head or '"assistant"' in head or 'summary' in head):
                    continue
                try:
                    j = json.loads(line)
                except Exception:
                    continue
                t = j.get("type")
                if j.get("isSidechain") is True:
                    is_sidechain = True
                if cwd is None:
                    cwd = j.get("cwd")
                ts = j.get("timestamp", "")
                ts_epoch = parse_ts(ts)
                if ts_epoch:
                    ev_ts.append(ts_epoch)
                if t == "user":
                    last_role = "user"
                    c = (j.get("message") or {}).get("content")
                    if isinstance(c, str) and not title and not c.startswith("<"):
                        title = first_text(c)
                    if ts:
                        last_user_ts = ts
                elif t == "assistant" and ts:
                    last_role = "assistant"
                    last_stop_reason = (j.get("message") or {}).get("stop_reason") or ""
                    last_asst_ts = ts
                    c = (j.get("message") or {}).get("content")
                    if isinstance(c, list):
                        for blk in c:
                            txt = blk.get("text") if isinstance(blk, dict) else None
                            if txt:
                                recent, recent_at = first_text(txt), ts
                                break
    except OSError:
        pass
    if not title:
        return []
    if is_sidechain:
        return []
    # 工作流 harness 会持续生成两类噪音会话：
    #   1) cwd 落在 ~/.claude/projects 里的元会话（"关于会话的会话"）
    #   2) 首条用户消息以 [Workflow harness — …] 开头的派发任务
    # 实测这类文件一分钟能刷出十几条，会把任务列表冲垮。
    if cwd and os.path.abspath(cwd).startswith(os.path.abspath(CLAUDE_DIR)):
        return []
    if title.startswith("[Workflow harness"):
        return []
    # 标题退化成 "-" 之类的噪音（首条消息是 shell 回显）
    if len(title.strip(" -\t")) < 2:
        return []
    # 首条消息是命令路径回显（如 claude 自身报错 "fork: Resource temporarily unavailable"）
    if title.startswith("/") and "/bin/" in title[:80]:
        return []
    return [{"agent": "claude", "title": title, "cwd": cwd or "", "mtime": os.path.getmtime(f),
             "link": "", "last_user": last_user_ts, "last_asst": last_asst_ts,
             "last_role": last_role, "stop_reason": last_stop_reason, "ev_ts": ev_ts,
             "recent": recent, "recent_at": recent_at}]

def scan_claude():
    now = time.time()
    out = []
    for f in glob.glob(os.path.join(CLAUDE_DIR, "**/*.jsonl"), recursive=True):
        # 子 agent 的转录单独写成 agent-*.jsonl，不是用户任务，混进来会让列表翻倍
        if os.path.basename(f).startswith("agent-"):
            continue
        mtime = os.path.getmtime(f)
        if now - mtime > SCAN_AGE:
            continue
        cached = _file_cache["claude"].get(f)
        if cached and cached[0] == mtime:
            r = cached[1]
        else:
            r = parse_claude_file(f)
            _file_cache["claude"][f] = (mtime, r)
        for t in r:
            t = dict(t)
            last_role, stop_reason = t["last_role"], t["stop_reason"]
            if last_role == "assistant" and stop_reason in ("end_turn", "stop_sequence"):
                t["status"] = "done"
            elif last_role == "user" or stop_reason == "tool_use":
                # 用户已发消息等回复，或还在跑工具：执行中；久无写入则进程已退
                t["status"] = demote_if_zombie("running", t["mtime"], zombie_threshold(t["ev_ts"]))
            else:
                t["status"] = "idle"
            t.pop("last_role", None)
            t.pop("stop_reason", None)
            t.pop("ev_ts", None)
            out.append(t)
    return out

def tasks():
    now = time.time()
    if now - _cache["mtime"] < 3:
        data = _cache["data"]
    else:
        all_t = scan_codex() + scan_claude() + scan_apps() + scan_dsh()
        all_t = [t for t in (normalize_task(task) for task in all_t) if t is not None]
        all_t.sort(key=lambda x: -x["mtime"])
        _cache["data"] = all_t
        _cache["mtime"] = now
        data = all_t
    hidden = set(load_config().get("hidden", []))
    visible = [t for t in data if t["agent"] not in hidden]
    # 状态对比用全量数据（隐藏渠道也该发完成通知）
    now_tasks = {}
    for t in data:
        now_tasks[t["task_id"]] = t
    finished = []
    for task_id, previous in _prev_tasks.items():
        current = now_tasks.get(task_id)
        if previous["status"] == "running" and current and current["status"] == "done":
            agent = current["agent"]
            if agent not in hidden:
                finished.append({
                    "task_id": task_id,
                    "agent": agent,
                    "title": current["title"],
                })
    _prev_tasks.clear()
    _prev_tasks.update({t["task_id"]: t for t in data})
    return {"api_version": API_VERSION, "tasks": visible, "finished": finished}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def _send(self, code, body, ctype="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            with open(HTML_PATH, "rb") as fh:
                self._send(200, fh.read().decode("utf-8"), ctype="text/html; charset=utf-8")
        elif path == "/api/tasks":
            result = tasks()
            self._send(200, json.dumps({**result, "pin": os.path.exists(PIN_FLAG)}))
        elif path == "/api/config":
            self._send(200, json.dumps({
                "api_version": API_VERSION,
                "agents": ALL_AGENTS,
                **load_config(),
            }))
        elif path == "/api/health":
            self._send(200, json.dumps({
                "api_version": API_VERSION,
                "platform": RUNTIME.id,
                "pid": os.getpid(),
                "build": BUILD_ID,
            }))
        else:
            self._send(404, "{}")
    def do_POST(self):
        if urlparse(self.path).path == "/api/pin":
            if os.path.exists(PIN_FLAG):
                os.remove(PIN_FLAG)
            else:
                open(PIN_FLAG, "w").close()
            self._send(200, json.dumps({"ok": True}))
        elif urlparse(self.path).path == "/api/config":
            try:
                d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                if not isinstance(d.get("hidden"), list):
                    raise ValueError
                json.dump({"hidden": d["hidden"]}, open(CONFIG_PATH, "w"))
                _cache["mtime"] = 0  # 立即生效
                self._send(200, json.dumps({"ok": True}))
            except Exception:
                self._send(400, json.dumps({"ok": False}))

if __name__ == "__main__":
    BUILD_ID = build_id(os.path.abspath(__file__))
    if "--build" in sys.argv:
        try:
            BUILD_ID = sys.argv[sys.argv.index("--build") + 1] or BUILD_ID
        except IndexError:
            pass
    try:
        with open(PID_PATH, "w") as fh:
            fh.write(str(os.getpid()))
    except OSError:
        pass
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
