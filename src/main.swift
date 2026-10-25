import Cocoa
import WebKit
import UserNotifications

// 置顶悬浮面板：加载任务面板页面（数据来自本地 server.py）
class PanelController: NSObject, NSWindowDelegate, WKScriptMessageHandler {
    let panel: NSPanel
    let webView: WKWebView
    let navDelegate: NavDelegate
    var chromeHost: ChromeHost?

    override init() {
        let size = NSSize(width: 400, height: 640)
        panel = NSPanel(
            contentRect: NSRect(origin: NSPoint(x: 0, y: 0), size: size),
            styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
            backing: .buffered, defer: false
        )
        panel.title = "Agent 任务面板"
        panel.titlebarAppearsTransparent = true
        panel.titleVisibility = .hidden
        // 保留标准标题栏（红绿灯），但标题文字隐藏，视觉接近无边框
        panel.titleVisibility = .hidden
        panel.isMovableByWindowBackground = true
        panel.isFloatingPanel = false          // 置顶由页面里的 📌 开关控制
        panel.level = .normal
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.hidesOnDeactivate = false
        panel.isOpaque = false
        panel.backgroundColor = .clear

        webView = WKWebView(frame: NSRect(origin: .zero, size: size))
        webView.autoresizingMask = [.width, .height]
        webView.setValue(false, forKey: "drawsBackground")   // 透明背景
        panel.contentView?.addSubview(webView)
        // 透明模式下隐藏系统红绿灯（网页切模式时经 chrome 消息通道通知）
        chromeHost = ChromeHost(panel: panel, webView: webView)
        // 拖动条必须在 webView 之上才能收到鼠标事件；覆盖顶部 40px 整条留白区
        // 右上角 150px 让点击穿透到网页（透明模式下 📌⚙️◐↻ 悬浮按钮在该区域）
        let dragStrip = DragView(frame: NSRect(x: 0, y: size.height - 40, width: size.width, height: 40))
        dragStrip.autoresizingMask = [.width, .minYMargin]
        panel.contentView?.addSubview(dragStrip)

        navDelegate = NavDelegate()
        super.init()
        navDelegate.owner = self
        webView.navigationDelegate = navDelegate
        webView.configuration.userContentController.add(self, name: "notify")
        webView.configuration.userContentController.add(self, name: "settings")
        webView.configuration.userContentController.add(self, name: "chrome")

        panel.center()
        // 位置/大小记忆：系统自动在 UserDefaults 里持久化窗口 frame，下次启动原位恢复
        panel.setFrameAutosaveName("AgentTaskPanelFrame")
        panel.delegate = self
    }

    func load() {
        if let url = URL(string: "http://127.0.0.1:8765/") { _ = webView.load(URLRequest(url: url)) }
    }

    func show() {
        panel.orderFrontRegardless()
        NSApp.activate(ignoringOtherApps: true)
    }

    func showSettings() {
        let alert = NSAlert()
        alert.messageText = "设置"
        alert.addButton(withTitle: Settings.autostart ? "关闭开机自启" : "开启开机自启")
        alert.addButton(withTitle: "刷新数据服务")
        alert.addButton(withTitle: "取消")
        let response = alert.runModal()
        if response == .alertFirstButtonReturn {
            Settings.autostart.toggle()
            let tip = NSAlert()
            tip.messageText = Settings.autostart ? "已开启开机自启" : "已关闭开机自启"
            tip.runModal()
        } else if response == .alertSecondButtonReturn {
            let proc = Process()
            proc.executableURL = URL(fileURLWithPath: "/usr/bin/pkill")
            proc.arguments = ["-f", "AgentTaskPanel.app/Contents/Resources/server.py"]
            try? proc.run()
        }
    }

    // 主菜单「设置…」入口：showSettings 是内部方法，包一层 @objc 供菜单 action 调用
    @objc func showSettingsViaMenu() { showSettings() }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        if message.name == "chrome" {
            chromeHost?.handle(message.body as? String)
            return
        }
        if message.name == "settings" {
            showSettings()
            return
        }
        guard message.name == "notify",
              let s = message.body as? String,
              let d = try? JSONSerialization.jsonObject(with: Data(s.utf8)) as? [String: String] else { return }
        let content = UNMutableNotificationContent()
        content.title = d["title"] ?? "任务完成"
        content.body = d["body"] ?? ""
        UNUserNotificationCenter.current().add(
            UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil))
    }

    func windowWillClose(_ notification: Notification) {
        // 有菜单栏常驻图标时关窗只隐藏面板，从菜单栏可再次打开；否则维持退出
        if MenuBarManager.shared.isActive {
            panel.orderOut(nil)
        } else {
            NSApp.terminate(nil)
        }
    }
}

// 菜单栏常驻图标：显示面板 / 置顶 / 自启 / 刷新 / 退出；执行中数量轮询显示在图标旁
class MenuBarManager: NSObject {
    static let shared = MenuBarManager()
    private var statusItem: NSStatusItem?
    private var timer: Timer?

    var isActive: Bool { statusItem != nil }

    func start(panel: NSPanel) {
        guard statusItem == nil else { return }
        let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        // SF Symbol 模板图：跟随菜单栏深浅色自动着色，比 emoji 在深色菜单栏下干净
        let cfg = NSImage.SymbolConfiguration(pointSize: 14, weight: .medium)
        if let img = NSImage(systemSymbolName: "rectangle.stack.badge.person.crop", accessibilityDescription: "Agent 任务")?
            .withSymbolConfiguration(cfg) {
            img.isTemplate = true
            item.button?.image = img
        } else {
            item.button?.title = "🤖"
        }
        item.menu = buildMenu(panel: panel)
        statusItem = item
        // 每 10 秒拉一次任务统计，执行中 > 0 时在图标旁显示数字
        timer = Timer.scheduledTimer(withTimeInterval: 10.0, repeats: true) { [weak self] _ in
            self?.refreshCount()
        }
        refreshCount()
    }

    private func buildMenu(panel: NSPanel) -> NSMenu {
        let menu = NSMenu()
        menu.delegate = self
        menu.autoenablesItems = false
        // 存引用供 menuNeedsUpdate 判断勾选状态
        menuPanel = panel
        return menu
    }

    weak var menuPanel: NSPanel?

    private func refreshCount() {
        URLSession.shared.dataTask(with: URL(string: "http://127.0.0.1:8765/api/tasks")!) { [weak self] data, _, _ in
            var running = 0
            if let data,
               let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let tasks = obj["tasks"] as? [[String: Any]] {
                running = tasks.filter { ($0["status"] as? String) == "running" }.count
            }
            DispatchQueue.main.async {
                guard let btn = self?.statusItem?.button else { return }
                // 图标常驻（模板图自动适配深浅色），执行中数量作文字跟在图标后
                let cfg = NSImage.SymbolConfiguration(pointSize: 14, weight: .medium)
                if let img = NSImage(systemSymbolName: "rectangle.stack.badge.person.crop", accessibilityDescription: "Agent 任务")?
                    .withSymbolConfiguration(cfg) {
                    img.isTemplate = true
                    btn.image = img
                }
                btn.title = running > 0 ? " \(running)" : ""
            }
        }.resume()
    }
}

extension MenuBarManager: NSMenuDelegate {
    func menuNeedsUpdate(_ menu: NSMenu) {
        menu.removeAllItems()
        let pinned = FileManager.default.fileExists(atPath: NSString(string: "~/.agent-panel-pin").expandingTildeInPath)
        let items: [(String, Selector?, NSControl.StateValue)] = [
            ("显示任务面板", #selector(showPanel), .off),
            ("置顶窗口", #selector(togglePin), pinned ? .on : .off),
            ("开机自启", #selector(toggleAutostart), Settings.autostart ? .on : .off),
            ("刷新数据", #selector(refreshData), .off),
            ("退出", #selector(NSApplication.terminate(_:)), .off),
        ]
        for (idx, entry) in items.enumerated() {
            if idx == items.count - 1 { menu.addItem(.separator()) }
            let it = NSMenuItem(title: entry.0, action: entry.1, keyEquivalent: "")
            it.target = self
            it.state = entry.2
            it.isEnabled = true
            menu.addItem(it)
        }
    }
    @objc func showPanel() {
        menuPanel?.orderFrontRegardless()
        NSApp.activate(ignoringOtherApps: true)
    }
    @objc func togglePin() {
        let flag = NSString(string: "~/.agent-panel-pin").expandingTildeInPath
        if FileManager.default.fileExists(atPath: flag) {
            try? FileManager.default.removeItem(atPath: flag)
        } else {
            FileManager.default.createFile(atPath: flag, contents: nil)
        }
    }
    @objc func toggleAutostart() { Settings.autostart.toggle() }
    @objc func refreshData() {
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/usr/bin/pkill")
        proc.arguments = ["-f", "AgentTaskPanel.app/Contents/Resources/server.py"]
        try? proc.run()
    }

    @objc func openGitHub() {
        NSWorkspace.shared.open(URL(string: "https://github.com/Jascenn/agent-task-panel")!)
    }
}

// 红绿灯显隐控制：透明模式全隐藏，鼠标移入面板时短暂浮现
// 继承 NSResponder 才能作为 NSTrackingArea owner 接收 mouseEntered/Exited
class ChromeHost: NSResponder {
    weak var panel: NSPanel?
    weak var webView: WKWebView?
    var tracking = false

    init(panel: NSPanel, webView: WKWebView) {
        super.init()
        self.panel = panel
        self.webView = webView
    }

    required init?(coder: NSCoder) { fatalError("not used") }

    func handle(_ payload: String?) {
        let hide = payload == "clear"
        DispatchQueue.main.async {
            guard let sv = self.panel?.standardWindowButton(.closeButton)?.superview else { return }
            sv.isHidden = hide
            if hide {
                self.startHoverTracking()
            } else {
                self.stopHoverTracking()
            }
        }
    }

    // 用 NSTrackingArea 监听鼠标进出面板，进出瞬间闪烁红绿灯 400ms 提供可见反馈
    func startHoverTracking() {
        guard !tracking, let content = panel?.contentView else { return }
        tracking = true
        content.addTrackingArea(NSTrackingArea(
            rect: NSRect(origin: .zero, size: content.bounds.size),
            options: [.mouseEnteredAndExited, .activeInKeyWindow, .inVisibleRect],
            owner: self))
        if let chrome = panel?.standardWindowButton(.closeButton)?.superview {
            chrome.alphaValue = 0
        }
    }

    func stopHoverTracking() {
        tracking = false
        panel?.contentView?.trackingAreas.forEach { panel?.contentView?.removeTrackingArea($0) }
        if let chrome = panel?.standardWindowButton(.closeButton)?.superview {
            chrome.isHidden = false
            chrome.alphaValue = 1
        }
    }

    override func mouseEntered(with event: NSEvent) {
        guard let chrome = panel?.standardWindowButton(.closeButton)?.superview else { return }
        chrome.isHidden = false
        chrome.alphaValue = 0.9
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(fadeOut), object: nil)
        perform(#selector(fadeOut), with: nil, afterDelay: 2.5)
    }

    override func mouseExited(with event: NSEvent) {
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(fadeOut), object: nil)
        fadeOut()
    }

    @objc func fadeOut() {
        panel?.standardWindowButton(.closeButton)?.superview?.alphaValue = 0
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) { [weak self] in
            if self?.panel?.standardWindowButton(.closeButton)?.superview?.alphaValue == 0 {
                self?.panel?.standardWindowButton(.closeButton)?.superview?.isHidden = true
            }
        }
    }
}

class NavDelegate: NSObject, WKNavigationDelegate {
    weak var owner: PanelController?

    // 页面里的 deep link（targetFrame == nil 的新窗口跳转）交给系统打开
    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        // 同帧导航的 codex:// 等自定义 scheme 也拦截：交给系统打开，避免 WebView 自身导航挂掉
        if let url = navigationAction.request.url,
           !["http", "https", "about", "file"].contains(url.scheme?.lowercased() ?? "") {
            NSWorkspace.shared.open(url)
            decisionHandler(.cancel)
            return
        }
        decisionHandler(.allow)
    }
}

// 顶部拖动条：捕获鼠标按下后交给窗口拖动
class DragView: NSView {
    // 顶部右侧按钮区宽度：该范围内不拦截，事件透传给 WebView
    static let passThroughWidth: CGFloat = 150
    override func hitTest(_ p: NSPoint) -> NSView? {
        guard let pLocal = superview.map({ convert(p, from: $0) }) else { return super.hitTest(p) }
        // 必须先判断点是否在本视图 frame 内，否则会吞掉下方统计卡/任务卡的点击
        guard bounds.contains(pLocal) else { return nil }
        if pLocal.x > bounds.width - DragView.passThroughWidth { return nil }
        return self
    }
    override func mouseDown(with event: NSEvent) {
        window?.performDrag(with: event)
    }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
}

// 轮询 pin 标志文件，切换置顶层级
class PinWatcher {
    var timer: Timer?
    let panel: NSPanel
    let flag = NSString(string: "~/.agent-panel-pin").expandingTildeInPath

    init(panel: NSPanel) {
        self.panel = panel
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            guard let self else { return }
            let pinned = FileManager.default.fileExists(atPath: self.flag)
            let want = pinned ? NSWindow.Level.floating : NSWindow.Level.normal
            if self.panel.level != want {
                self.panel.level = want
                if pinned { self.panel.orderFrontRegardless() }
            }
        }
    }
}

// 拉起本地数据服务（bundle 内的 server.py），已运行则跳过
func startServer() {
    let semaphore = DispatchSemaphore(value: 0)
    var ok = false
    URLSession.shared.dataTask(with: URL(string: "http://127.0.0.1:8765/api/tasks")!) { _, r, _ in
        ok = (r as? HTTPURLResponse)?.statusCode == 200
        semaphore.signal()
    }.resume()
    _ = semaphore.wait(timeout: .now() + 1)
    if ok { return }
    guard let py = Bundle.main.url(forResource: "server", withExtension: "py") else { return }
    let proc = Process()
    proc.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
    proc.arguments = [py.path]
    try? proc.run()
}

// 数据服务守护：server.py 是 App 子进程，一旦意外退出面板就会一直"未响应"。
// 每 5 秒健康检查，失败就重新拉起（拉起前先探活，避免服务忙时重复起进程）。
class ServerKeeper {
    var timer: Timer?
    var restarting = false

    static func probe() -> Bool {
        let semaphore = DispatchSemaphore(value: 0)
        var ok = false
        URLSession.shared.dataTask(with: URL(string: "http://127.0.0.1:8765/api/tasks")!) { _, r, _ in
            ok = (r as? HTTPURLResponse)?.statusCode == 200
            semaphore.signal()
        }.resume()
        _ = semaphore.wait(timeout: .now() + 2)
        return ok
    }

    static func launch() {
        guard let py = Bundle.main.url(forResource: "server", withExtension: "py") else { return }
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        proc.arguments = [py.path]
        try? proc.run()
    }

    func start() {
        timer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
            guard let self, !self.restarting else { return }
            if ServerKeeper.probe() { return }
            self.restarting = true
            ServerKeeper.launch()
            // 给服务 3 秒就绪窗口，期间跳过检查避免重复拉起
            DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in
                self?.restarting = false
            }
        }
    }
}


// ============ 设置项（defaults 持久化 + Dock 菜单） ============
let DOMAIN = "local.agent-task-panel"
enum Settings {
    static var autostart: Bool {
        get { UserDefaults(suiteName: DOMAIN)?.bool(forKey: "autostart") ?? false }
        set {
            UserDefaults(suiteName: DOMAIN)?.set(newValue, forKey: "autostart")
            let agentPath = NSHomeDirectory() + "/Library/LaunchAgents/local.agent-task-panel.plist"
            let fm = FileManager.default
            if newValue {
                let plist: [String: Any] = [
                    "Label": "local.agent-task-panel",
                    "ProgramArguments": ["/usr/bin/open", "-a", "/Applications/AgentTaskPanel.app"],
                    "RunAtLoad": true
                ]
                let dir = (agentPath as NSString).deletingLastPathComponent
                try? fm.createDirectory(atPath: dir, withIntermediateDirectories: true)
                let data = try? PropertyListSerialization.data(fromPropertyList: plist, format: .xml, options: 0)
                try? data?.write(to: URL(fileURLWithPath: agentPath))
                let proc = Process()
                proc.executableURL = URL(fileURLWithPath: "/bin/launchctl")
                proc.arguments = ["load", agentPath]
                try? proc.run()
            } else {
                try? fm.removeItem(atPath: agentPath)
                let proc = Process()
                proc.executableURL = URL(fileURLWithPath: "/bin/launchctl")
                proc.arguments = ["unload", agentPath]
                try? proc.run()
            }
        }
    }
}

// Dock 菜单：勾选项读写设置
class DockMenuDelegate: NSObject {
    let autostartItem = NSMenuItem(title: "开机自启", action: #selector(toggleAutostart), keyEquivalent: "")
}
var dockMenuDelegate = DockMenuDelegate()

extension DockMenuDelegate: NSApplicationDelegate, NSMenuDelegate {
    func applicationDockMenu(_ sender: NSApplication) -> NSMenu? {
        let menu = NSMenu()
        menu.delegate = self
        return menu
    }
    func menuNeedsUpdate(_ menu: NSMenu) {
        menu.removeAllItems()
        let a = NSMenuItem(title: "开机自启", action: #selector(toggleAutostart), keyEquivalent: "")
        a.target = self
        a.state = Settings.autostart ? .on : .off
        menu.addItem(a)
        let b = NSMenuItem(title: "刷新数据", action: #selector(refreshData), keyEquivalent: "r")
        b.target = self
        menu.addItem(b)
        menu.addItem(.separator())
        let q = NSMenuItem(title: "退出", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        menu.addItem(q)
    }
    @objc func toggleAutostart() { Settings.autostart.toggle() }
    @objc func refreshData() {
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/usr/bin/pkill")
        proc.arguments = ["-f", "AgentTaskPanel.app/Contents/Resources/server.py"]
        try? proc.run()
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.regular)
app.delegate = dockMenuDelegate

// ============ 应用主菜单（左上角 App 名菜单）：macOS 标准结构 ============
// NSApp 的 mainMenu 不设置时，App 菜单只有灰默认项；补齐 关于/设置/隐藏/退出 与系统快捷键
func buildAppMainMenu(panel: NSPanel, controller: PanelController) -> NSMenu {
    let main = NSMenu()

    // App 菜单（第一列，标题由系统自动取 CFBundleName）
    let appMenu = NSMenu()
    let about = NSMenuItem(title: "关于 AgentTaskPanel", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
    appMenu.addItem(about)
    appMenu.addItem(.separator())
    let settings = NSMenuItem(title: "设置…", action: #selector(PanelController.showSettingsViaMenu), keyEquivalent: ",")
    settings.target = controller
    appMenu.addItem(settings)
    let refresh = NSMenuItem(title: "刷新数据服务", action: #selector(DockMenuDelegate.refreshData), keyEquivalent: "r")
    refresh.target = dockMenuDelegate
    appMenu.addItem(refresh)
    appMenu.addItem(.separator())
    appMenu.addItem(NSMenuItem(title: "隐藏 AgentTaskPanel", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h"))
    let hideOthers = NSMenuItem(title: "隐藏其他", action: #selector(NSApplication.hideOtherApplications(_:)), keyEquivalent: "h")
    hideOthers.keyEquivalentModifierMask = [.command, .option]
    appMenu.addItem(hideOthers)
    appMenu.addItem(NSMenuItem(title: "显示全部", action: #selector(NSApplication.unhideAllApplications(_:)), keyEquivalent: ""))
    appMenu.addItem(.separator())
    appMenu.addItem(NSMenuItem(title: "退出 AgentTaskPanel", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
    let appItem = NSMenuItem()
    appItem.submenu = appMenu
    main.addItem(appItem)

    // 窗口菜单
    let windowMenu = NSMenu(title: "窗口")
    let showPanel = NSMenuItem(title: "显示任务面板", action: #selector(MenuBarManager.showPanel), keyEquivalent: "m")
    showPanel.target = MenuBarManager.shared
    windowMenu.addItem(showPanel)
    let close = NSMenuItem(title: "关闭面板", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
    windowMenu.addItem(close)
    let winItem = NSMenuItem()
    winItem.submenu = windowMenu
    main.addItem(winItem)

    // 帮助菜单
    let helpMenu = NSMenu(title: "帮助")
    let help = NSMenuItem(title: "GitHub 仓库", action: #selector(MenuBarManager.openGitHub), keyEquivalent: "")
    help.target = MenuBarManager.shared
    helpMenu.addItem(help)
    let helpItem = NSMenuItem()
    helpItem.submenu = helpMenu
    main.addItem(helpItem)

    return main
}
startServer()
UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { _, _ in }
let controller = PanelController()
controller.load()
controller.show()
app.mainMenu = buildAppMainMenu(panel: controller.panel, controller: controller)
// 必须强持有 watcher，否则实例被释放、定时器回调里 self 为 nil，置顶永远不生效
let pinWatcher = PinWatcher(panel: controller.panel)
let serverKeeper = ServerKeeper()
serverKeeper.start()
MenuBarManager.shared.start(panel: controller.panel)
app.run()
