import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from platforms import detect_runtime


class PlatformRuntimeTests(unittest.TestCase):
    def test_macos_paths_and_native_apps(self):
        runtime = detect_runtime(system="Darwin", home="/Users/example")

        self.assertEqual(runtime.id, "macos")
        self.assertTrue(runtime.supports_native_apps)
        self.assertEqual(runtime.codex_dir, "/Users/example/.codex/sessions")
        self.assertEqual(runtime.config_path, "/Users/example/.agent-panel-config.json")

    def test_linux_paths_disable_native_apps(self):
        runtime = detect_runtime(system="Linux", home="/home/example")

        self.assertEqual(runtime.id, "linux")
        self.assertFalse(runtime.supports_native_apps)
        self.assertEqual(runtime.claude_dir, "/home/example/.claude/projects")
        self.assertEqual(runtime.dsh_dir, "/home/example/.dsh/sessions")

    def test_windows_uses_userprofile(self):
        runtime = detect_runtime(
            system="Windows",
            env={"USERPROFILE": r"C:\Users\example"},
        )

        self.assertEqual(runtime.id, "windows")
        self.assertFalse(runtime.supports_native_apps)
        self.assertEqual(
            runtime.codex_dir,
            r"C:\Users\example\.codex\sessions",
        )


if __name__ == "__main__":
    unittest.main()
