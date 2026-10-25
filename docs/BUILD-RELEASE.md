# 构建、签名与发布备注

本文档记录 AgentTaskPanel 从改完代码到发布新版本的完整流程，命令可直接复制执行。

## 目录

- [日常构建（本机使用）](#日常构建本机使用)
- [发布新版本（打 tag + DMG + Release）](#发布新版本打-tag--dmg--release)
- [签名说明：ad-hoc vs 正式签名](#签名说明ad-hoc-vs-正式签名)
- [买了 Apple 开发者账号后要做什么](#买了-apple-开发者账号后要做什么)
- [常见问题](#常见问题)

---

## 日常构建（本机使用）

改完代码后重新构建并替换本机已安装的 App：

```bash
cd /path/to/agent-task-panel

# 1. 构建（build.sh 内含 ad-hoc 签名）
zsh build.sh

# 2. 停掉正在运行的 App 和数据服务
pkill -f "AgentTaskPanel.app/Contents/MacOS/AgentTaskPanel" 2>/dev/null
pkill -f "AgentTaskPanel.app/Contents/Resources/server.py" 2>/dev/null
sleep 1

# 3. 覆盖安装到 /Applications
ditto AgentTaskPanel.app /Applications/AgentTaskPanel.app

# 4. 重新启动
open /Applications/AgentTaskPanel.app

# 5. 验证服务正常（应返回 JSON 任务数据）
curl -s http://127.0.0.1:8765/api/tasks | head -c 200
```

### 构建要求

- macOS 13+
- Xcode Command Line Tools：`xcode-select --install`
- 打 DMG 需要 create-dmg：`brew install create-dmg`

### App 图标

把 `AppIcon.icns` 放在仓库根目录，`build.sh` 会自动打包进 App；不放则使用系统默认图标。

---

## 发布新版本（打 tag + DMG + Release）

前提：本机 `/Applications/AgentTaskPanel.app` 已经是验证过能正常跑的新版本（先走一遍上面的"日常构建"再发布，不要发布没实测的版本）。

### 1. 更新版本号（三处保持一致）

```bash
# ① Info.plist：CFBundleShortVersionString 和 CFBundleVersion
vim Info.plist

# ② CHANGELOG.md：在文件顶部加新版本条目
vim CHANGELOG.md
```

### 2. 提交代码并打 tag

```bash
git add -A
git commit -m "Release v0.X.Y: <一句话说明>"
git push origin main

git tag v0.X.Y
git push origin v0.X.Y
```

### 3. 打 DMG

```bash
# 先给 /Applications 里已验证的 App 做 ad-hoc 签名（build.sh 已含此步，
# 若是直接用 /Applications 的 App 可跳过）
codesign --force --deep --sign - /Applications/AgentTaskPanel.app

# 准备 staging 目录并生成 DMG
rm -rf /tmp/dmg-stage
mkdir -p /tmp/dmg-stage
ditto /Applications/AgentTaskPanel.app /tmp/dmg-stage/AgentTaskPanel.app

create-dmg \
  --volname "AgentTaskPanel" \
  --window-size 560 360 \
  --icon-size 110 \
  --icon "AgentTaskPanel.app" 150 180 \
  --app-drop-link 410 180 \
  /tmp/AgentTaskPanel-v0.X.Y.dmg \
  /tmp/dmg-stage
```

### 4. 验证 DMG（发布前必做）

```bash
# 挂载并确认里面有 App 和 Applications 快捷方式
hdiutil attach /tmp/AgentTaskPanel-v0.X.Y.dmg -nobrowse -quiet
ls /Volumes/AgentTaskPanel/
hdiutil detach /Volumes/AgentTaskPanel -quiet
```

### 5. 创建 GitHub Release 并上传

```bash
gh release create v0.X.Y /tmp/AgentTaskPanel-v0.X.Y.dmg \
  --title "v0.X.Y — <标题>" \
  --notes "$(cat <<'EOF'
<更新内容，参考 CHANGELOG>

### 下载
- **AgentTaskPanel-v0.X.Y.dmg**（推荐）：拖拽安装

### 说明
- 首次打开若提示「无法验证开发者」：右键 App → 打开
EOF
)"

# 验证 Release 资产
gh release view v0.X.Y --json assets --jq '[.assets[] | {name, size}]'
```

---

## 签名说明：ad-hoc vs 正式签名

| | ad-hoc（当前） | Developer ID 签名 + 公证 |
|---|---|---|
| 需要 | 无 | Apple 开发者账号 $99/年 |
| 首次打开 | 需右键 → 打开一次 | 双击直接开 |
| 「文件已损坏」报错 | 不会出现 | 不会出现 |
| 适用 | 自用 / 开源分发 | 面向大众分发 |

ad-hoc 签名解决的是「从浏览器下载后报文件已损坏」——那是无签名 bundle 被 quarantine 属性拦截的典型症状。它不能消除「无法验证开发者」弹窗，那个只有付费开发者证书 + 公证能解决。

---

## 买了 Apple 开发者账号后要做什么

### 1. 确认证书

登录开发者账号后在 Xcode 或 https://developer.apple.com/account/resources/certificates 下载 **Developer ID Application** 证书，装进钥匙串。确认：

```bash
security find-identity -v -p codesigning
# 应看到一行: 1) XXXXXXXX "Developer ID Application: Your Name (TEAMID)"
```

### 2. 改 build.sh 里的签名命令

把最后一行：

```bash
codesign --force --deep --sign - AgentTaskPanel.app
```

换成：

```bash
codesign --force --deep --sign "Developer ID Application: Your Name (TEAMID)" AgentTaskPanel.app
# 若有 entitlements 需求（本 App 暂无），再加 --entitlements entitlements.plist
```

### 3. 公证（notarization）

```bash
# 先把 App 压成 zip（公证对象是 zip 不是 app）
ditto -c -k --keepParent AgentTaskPanel.app /tmp/AgentTaskPanel-notarize.zip

# 提交公证（首次需用 App 专用密码或 API key 登录，按提示存进钥匙串）
xcrun notarytool submit /tmp/AgentTaskPanel-notarize.zip \
  --apple-id "你的AppleID" --team-id "TEAMID" --password "app专用密码" \
  --wait

# 公证通过后把票据钉进 App
xcrun stapler staple AgentTaskPanel.app
xcrun stapler validate AgentTaskPanel.app
```

### 4. 验证

```bash
codesign --verify --deep --strict AgentTaskPanel.app && echo "签名 OK"
spctl -a -vv AgentTaskPanel.app
# 应输出: accepted  source=Notarized Developer ID
```

公证通过后，用户双击打开不会再有任何弹窗，README 和 Release notes 里「无法验证开发者」的提示可以删掉。

---

## 常见问题

### 用户反馈「文件已损坏，移到废纸篓」

说明下载的是旧版未签名的包（v0.2.0 之前的 zip），让用户重新下载最新 DMG。或者临时绕过（不建议写进 README）：

```bash
xattr -dr com.apple.quarantine /Applications/AgentTaskPanel.app
```

### 用户反馈「无法验证开发者」

右键点击 App → 打开 → 再点打开；或 系统设置 → 隐私与安全性 → 底部点「仍要打开」。每个用户只需做一次。

### 菜单栏图标不显示 / 数字不更新

```bash
# 检查数据服务是否在跑
curl -s http://127.0.0.1:8765/api/tasks | head -c 100

# 检查 App 进程
pgrep -fl AgentTaskPanel

# 都正常但不显示 → 重启 App
pkill -f "AgentTaskPanel.app/Contents/MacOS/AgentTaskPanel"
open /Applications/AgentTaskPanel.app
```

### 修改了前端页面但没生效

前端是 `agent-task-dashboard.html`，build.sh 会拷进 App bundle，改完必须重新 build + 覆盖安装，浏览器访问 `http://127.0.0.1:8765` 时记得强刷（Cmd+Shift+R）避免缓存。

### pkill / rm 被安全工具拦截

本机如装了安全类工具可能拦截 pkill，改用：

```bash
osascript -e 'quit app "AgentTaskPanel"'
```
