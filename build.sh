#!/bin/zsh
# 构建 AgentTaskPanel.app：Swift 外壳 + 本地数据服务 + 前端页面
set -e
cd "$(dirname "$0")"
rm -rf AgentTaskPanel.app
mkdir -p AgentTaskPanel.app/Contents/MacOS AgentTaskPanel.app/Contents/Resources
cp Info.plist AgentTaskPanel.app/Contents/Info.plist
# 图标可选：把 AppIcon.icns 放到本目录即可
[ -f AppIcon.icns ] && cp AppIcon.icns AgentTaskPanel.app/Contents/Resources/
swiftc main.swift -o AgentTaskPanel.app/Contents/MacOS/AgentTaskPanel -framework Cocoa -framework WebKit -framework UserNotifications
cp agent-task-dashboard.html server.py AgentTaskPanel.app/Contents/Resources/
# ad-hoc 签名：无需开发者证书，避免浏览器下载后被 Gatekeeper 判为"文件已损坏"
codesign --force --deep --sign - AgentTaskPanel.app
echo "Built: $(pwd)/AgentTaskPanel.app"
