import importlib.util
import pathlib
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SPEC = importlib.util.spec_from_file_location("agent_panel_server", ROOT / "src/server.py")
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)
from platforms import detect_runtime


class NormalizeTaskTests(unittest.TestCase):
    def test_normalizes_core_fields_and_preserves_extensions(self):
        task = server.normalize_task({
            "agent": "codex",
            "title": "  Fix   release  ",
            "cwd": None,
            "status": "unexpected",
            "mtime": "12.5",
            "link": None,
            "recent": None,
            "complete_at": "2026-10-29T00:00:00Z",
        })

        self.assertEqual(task["agent"], "codex")
        self.assertEqual(task["title"], "Fix release")
        self.assertEqual(task["cwd"], "")
        self.assertEqual(task["status"], "idle")
        self.assertEqual(task["mtime"], 12.5)
        self.assertEqual(task["link"], "")
        self.assertEqual(task["recent"], "")
        self.assertEqual(task["recent_at"], "")
        self.assertEqual(task["complete_at"], "2026-10-29T00:00:00Z")
        self.assertRegex(task["task_id"], r"^[0-9a-f]{16}$")

    def test_task_id_distinguishes_duplicate_titles(self):
        base = {"agent": "codex", "title": "好", "status": "running", "mtime": 1}
        first = server.normalize_task({**base, "link": "codex://threads/one"})
        second = server.normalize_task({**base, "link": "codex://threads/two"})

        self.assertNotEqual(first["task_id"], second["task_id"])
        self.assertEqual(first["task_id"], server.normalize_task({
            **base,
            "link": "codex://threads/one",
        })["task_id"])

    def test_missing_agent_is_rejected(self):
        self.assertIsNone(server.normalize_task({"title": "orphan"}))


class TasksResponseTests(unittest.TestCase):
    def setUp(self):
        server._cache = {"data": [], "mtime": 0}
        server._prev_tasks.clear()
        self.patches = [
            mock.patch.object(server, "load_config", return_value={"hidden": []}),
            mock.patch.object(server, "scan_claude", return_value=[]),
            mock.patch.object(server, "scan_apps", return_value=[]),
            mock.patch.object(server, "scan_dsh", return_value=[]),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        server._prev_tasks.clear()

    @staticmethod
    def codex_task(status="running"):
        return {
            "agent": "codex",
            "title": "好",
            "cwd": "/tmp/project",
            "status": status,
            "mtime": 10,
            "link": "codex://threads/one",
            "recent": "working",
            "recent_at": "",
        }

    def test_response_is_versioned_and_normalized(self):
        with mock.patch.object(server, "scan_codex", return_value=[self.codex_task()]):
            result = server.tasks()

        self.assertEqual(result["api_version"], 1)
        self.assertEqual(result["finished"], [])
        self.assertEqual(len(result["tasks"]), 1)
        self.assertEqual(result["tasks"][0]["status"], "running")

    def test_finished_transition_uses_stable_task_id(self):
        with mock.patch.object(server, "scan_codex", return_value=[self.codex_task()]):
            first = server.tasks()
        task_id = first["tasks"][0]["task_id"]

        server._cache["mtime"] = 0
        with mock.patch.object(
            server,
            "scan_codex",
            return_value=[self.codex_task("done")],
        ):
            second = server.tasks()

        self.assertEqual(second["finished"], [{
            "task_id": task_id,
            "agent": "codex",
            "title": "好",
        }])


class PlatformGuardTests(unittest.TestCase):
    def test_native_apps_are_skipped_outside_macos(self):
        runtime = detect_runtime(system="Linux", home="/tmp/example")
        with mock.patch.object(server, "RUNTIME", runtime):
            self.assertEqual(server.scan_apps(), [])


if __name__ == "__main__":
    unittest.main()
