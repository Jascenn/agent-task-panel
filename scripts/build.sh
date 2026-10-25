#!/bin/zsh
# 构建 AgentTaskPanel.app：Swift 外壳 + 本地数据服务 + 前端页面
# 用法：仓库根目录执行 zsh scripts/build.sh（产物在仓库根 AgentTaskPanel.app）
set -e
cd "$(dirname "$0")/.."
rm -rf AgentTaskPanel.app
mkdir -p AgentTaskPanel.app/Contents/MacOS AgentTaskPanel.app/Contents/Resources
cp resources/Info.plist AgentTaskPanel.app/Contents/Info.plist
cp resources/AppIcon.icns AgentTaskPanel.app/Contents/Resources/AppIcon.icns
swiftc src/main.swift -o AgentTaskPanel.app/Contents/MacOS/AgentTaskPanel \
  -framework Cocoa -framework WebKit -framework UserNotifications
cp web/panel.html AgentTaskPanel.app/Contents/Resources/agent-task-dashboard.html
cp src/server.py AgentTaskPanel.app/Contents/Resources/server.py
# ad-hoc 签名：无需开发者证书，避免浏览器下载后被 Gatekeeper 判为"文件已损坏"
codesign --force --deep --sign - AgentTaskPanel.app
echo "Built: $(pwd)/AgentTaskPanel.app"
