import json
import pathlib
import plistlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class ReleaseMetadataTests(unittest.TestCase):
    def test_package_versions_match(self):
        plist = plistlib.loads((ROOT / "resources" / "Info.plist").read_bytes())
        desktop = json.loads((ROOT / "desktop" / "package.json").read_text())
        lock = json.loads((ROOT / "desktop" / "package-lock.json").read_text())

        versions = {
            "Info.plist CFBundleVersion": plist["CFBundleVersion"],
            "Info.plist CFBundleShortVersionString": plist["CFBundleShortVersionString"],
            "desktop/package.json": desktop["version"],
            "desktop/package-lock.json": lock["version"],
            "desktop/package-lock.json root": lock["packages"][""]["version"],
        }
        self.assertEqual(set(versions.values()), {desktop["version"]}, versions)

    def test_release_workflow_publishes_all_platforms(self):
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()

        for value in (
            "macos-universal.dmg",
            "win-x64.exe",
            "linux-x86_64.AppImage",
            "SHA256SUMS",
        ):
            self.assertIn(value, workflow)



class WorkflowRunnerTests(unittest.TestCase):
    """Workflows 必须只用当前可解析的 runner 标签。

    macos-14 的 arm64 镜像已下线，`runs-on: macos-14` 会在 0 步内失败并报
    "The configuration 'macos-14-arm64-us-default' is not supported"，
    因为这类 job 从不执行任何步骤，很容易被误当成测试失败。
    """

    RETIRED = ("macos-12", "macos-13", "macos-14")
    WORKFLOWS = ROOT / ".github" / "workflows"

    def test_no_retired_macos_runner_labels(self):
        offenders = []
        for path in sorted(self.WORKFLOWS.glob("*.yml")):
            text = path.read_text()
            for line_no, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for label in self.RETIRED:
                    # 只匹配完整的标签，避免 macos-14 命中 macos-140 之类
                    if re.search(rf"(?<![\w.-]){re.escape(label)}(?![\w.-])", line):
                        offenders.append(f"{path.name}:{line_no}: {stripped}")
        self.assertEqual(offenders, [], "retired macOS runner labels:\n" + "\n".join(offenders))

    def test_macos_jobs_pin_a_supported_version(self):
        for path in sorted(self.WORKFLOWS.glob("*.yml")):
            text = path.read_text()
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or "runs-on:" not in stripped:
                    continue
                if "macos" not in stripped:
                    continue
                self.assertRegex(
                    stripped,
                    r"macos-(15|26|latest)",
                    f"{path.name}: unsupported macOS runner -> {stripped}",
                )


if __name__ == "__main__":
    unittest.main()
