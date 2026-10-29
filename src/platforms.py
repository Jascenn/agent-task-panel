"""跨平台运行时路径与能力描述。"""
from dataclasses import dataclass
import os
import ntpath
import platform
import posixpath
from typing import Mapping, Optional


@dataclass(frozen=True)
class PlatformRuntime:
    id: str
    home: str
    codex_dir: str
    claude_dir: str
    dsh_dir: str
    config_path: str
    pin_flag: str
    pid_path: str
    supports_native_apps: bool


def _platform_id(system: str) -> str:
    value = system.strip().lower()
    if value == "darwin":
        return "macos"
    if value == "windows":
        return "windows"
    return "linux"


def detect_runtime(
    system: Optional[str] = None,
    home: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
) -> PlatformRuntime:
    """构建当前平台的路径和能力集合；参数可用于无副作用测试。"""
    env = os.environ if env is None else env
    system = platform.system() if system is None else system
    platform_id = _platform_id(system)
    path = ntpath if platform_id == "windows" else posixpath
    home = os.path.expanduser(home or env.get("HOME") or env.get("USERPROFILE") or "~")
    return PlatformRuntime(
        id=platform_id,
        home=home,
        codex_dir=path.join(home, ".codex", "sessions"),
        claude_dir=path.join(home, ".claude", "projects"),
        dsh_dir=path.join(home, ".dsh", "sessions"),
        config_path=path.join(home, ".agent-panel-config.json"),
        pin_flag=path.join(home, ".agent-panel-pin"),
        pid_path=path.join(home, ".agent-panel-server.pid"),
        supports_native_apps=platform_id == "macos",
    )
