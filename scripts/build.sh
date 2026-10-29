#!/bin/zsh
# 构建 AgentTaskPanel.app：Swift 外壳 + 本地数据服务 + 前端页面
# 用法：仓库根目录执行 zsh scripts/build.sh（产物在仓库根 AgentTaskPanel.app）
set -e
cd "$(dirname "$0")/.."

# 最低支持 macOS 12（Monterey）。不显式指定的话，swiftc 会把 minos 设成
# 构建机当前系统版本，别人装了直接闪退。
MIN_MACOS="${MIN_MACOS:-12.0}"
# 默认出 Universal Binary（Apple Silicon + Intel）；ARCHS="arm64" 可只编本机架构
ARCHS="${ARCHS:-arm64 x86_64}"

rm -rf AgentTaskPanel.app
mkdir -p AgentTaskPanel.app/Contents/MacOS AgentTaskPanel.app/Contents/Resources
cp resources/Info.plist AgentTaskPanel.app/Contents/Info.plist
cp resources/AppIcon.icns AgentTaskPanel.app/Contents/Resources/AppIcon.icns

tmp_bin=$(mktemp -d)
trap 'rm -rf "$tmp_bin"' EXIT
built=()
for arch in ${=ARCHS}; do
  swiftc src/main.swift -o "$tmp_bin/AgentTaskPanel-$arch" \
    -target "$arch-apple-macos$MIN_MACOS" \
    -framework Cocoa -framework WebKit -framework UserNotifications
  built+=("$tmp_bin/AgentTaskPanel-$arch")
done
if [[ ${#built[@]} -eq 1 ]]; then
  cp "${built[1]}" AgentTaskPanel.app/Contents/MacOS/AgentTaskPanel
else
  lipo -create "${built[@]}" -output AgentTaskPanel.app/Contents/MacOS/AgentTaskPanel
fi

cp resources/panel.html AgentTaskPanel.app/Contents/Resources/agent-task-dashboard.html
cp src/server.py AgentTaskPanel.app/Contents/Resources/server.py
cp src/platforms.py AgentTaskPanel.app/Contents/Resources/platforms.py
# ad-hoc 签名：无需开发者证书，避免浏览器下载后被 Gatekeeper 判为"文件已损坏"
codesign --force --deep --sign - AgentTaskPanel.app
echo "Built: $(pwd)/AgentTaskPanel.app"
