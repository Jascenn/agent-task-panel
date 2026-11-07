import importlib.util
import json
import pathlib
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SPEC = importlib.util.spec_from_file_location("agent_panel_server", ROOT / "src/server.py")
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


SESSION = "/tmp/dsh/sess-1/session.v4.jsonl.zstd"
T0 = 1_700_000_000.0


def _session_bytes(turn_open=True):
    events = [
        {"type": "session/title", "data": {"title": "Demo"}, "timestamp": "2026-11-07T07:00:00Z"},
        {"type": "user/message", "data": {"content": [{"text": "do the thing"}]},
         "timestamp": "2026-11-07T07:00:05Z"},
        {"type": "turn/start", "timestamp": "2026-11-07T07:00:06Z"},
    ]
    if not turn_open:
        events.append({"type": "turn/end", "timestamp": "2026-11-07T07:05:00Z"})
    return ("\n".join(json.dumps(e) for e in events) + "\n").encode()


class DshZombieStatusTests(unittest.TestCase):
    def setUp(self):
        server._file_cache["dsh"].clear()
        self.addCleanup(server._file_cache["dsh"].clear)

    def _scan(self, now, content=None, mtime=T0):
        content = _session_bytes() if content is None else content
        done = mock.Mock(stdout=content)
        with mock.patch.object(server.glob, "glob", return_value=[SESSION]), \
             mock.patch.object(server.os.path, "getmtime", return_value=mtime), \
             mock.patch.object(server.subprocess, "run", return_value=done), \
             mock.patch.object(server.time, "time", return_value=now):
            return server.scan_dsh()

    def test_zombie_demoted_on_cache_hit_after_process_exits(self):
        """回合开着、mtime 不再变化 → 缓存命中时仍要按当前时间重算僵尸降级。"""
        first = self._scan(T0 + 10)
        self.assertEqual(first[0]["status"], "running")

        # mtime 没变（进程已崩，不再写文件），但时间已经过去很久
        later = self._scan(T0 + 10 + server.ZOMBIE_DEFAULT + 1)
        self.assertEqual(later[0]["status"], "idle")

    def test_open_turn_stays_running_while_recent(self):
        self._scan(T0 + 10)
        self.assertEqual(self._scan(T0 + 20)[0]["status"], "running")

    def test_closed_turn_is_done(self):
        tasks = self._scan(T0 + 10, content=_session_bytes(turn_open=False))
        self.assertEqual(tasks[0]["status"], "done")

    def test_cache_stores_facts_not_status(self):
        self._scan(T0 + 10)
        _, cached = server._file_cache["dsh"][SESSION]
        self.assertNotIn("status", cached)
        self.assertIn("turn_open", cached)


if __name__ == "__main__":
    unittest.main()
