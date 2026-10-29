import json
import pathlib
import plistlib
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


if __name__ == "__main__":
    unittest.main()
