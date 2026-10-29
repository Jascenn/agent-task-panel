const { app, BrowserWindow, ipcMain, Notification, Menu, Tray, nativeImage, shell } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

const PORT = process.env.AGENT_PANEL_PORT || "8765";
const APP_ORIGIN = `http://127.0.0.1:${PORT}`;
const HEALTH_INTERVAL_MS = 5000;
let mainWindow = null;
let tray = null;
let backend = null;
let quitting = false;
let healthTimer = null;

function resourcePath(name) {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "app.asar.unpacked", "resources", name);
  }
  return path.join(__dirname, "resources", name);
}

function bundledBackend() {
  const name = process.platform === "win32" ? "agent-task-backend.exe" : "agent-task-backend";
  const candidate = resourcePath(path.join("backend", name));
  return fs.existsSync(candidate) ? candidate : null;
}

function pythonCommand() {
  if (process.env.AGENT_PANEL_PYTHON) return process.env.AGENT_PANEL_PYTHON;
  return process.platform === "win32" ? "python.exe" : "python3";
}

function startBackend() {
  if (backend && !backend.killed) return;
  const bundled = bundledBackend();
  const server = bundled ? null : resourcePath("server.py");
  if (!bundled && !fs.existsSync(server)) {
    throw new Error(`Backend not found: ${server}`);
  }

  const command = bundled || pythonCommand();
  const args = bundled ? [] : [server];
  const child = spawn(command, args, {
    cwd: path.dirname(bundled || server),
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
    env: { ...process.env, AGENT_PANEL_PORT: PORT },
  });
  backend = child;
  child.stdout.on("data", (chunk) => console.log(`[backend] ${chunk}`));
  child.stderr.on("data", (chunk) => console.error(`[backend] ${chunk}`));
  child.on("error", (error) => {
    console.error(`Backend failed to start: ${error.message}`);
    if (backend === child) backend = null;
  });
  child.on("exit", (code, signal) => {
    if (backend === child) backend = null;
    // A clean SIGTERM is the expected shutdown path during app.quit().
    if (!quitting && signal !== "SIGTERM") {
      console.error(`Backend exited (${code ?? signal}); restarting.`);
      setTimeout(startBackend, 1000);
    }
  });
}

function requestJson(pathname, method = "GET", body = null) {
  return new Promise((resolve, reject) => {
    const payload = body === null ? null : Buffer.from(JSON.stringify(body));
    const req = http.request(
      `${APP_ORIGIN}${pathname}`,
      {
        method,
        headers: payload
          ? {
              "Content-Type": "application/json",
              "Content-Length": payload.length,
            }
          : {},
        timeout: 3000,
      },
      (res) => {
        let data = "";
        res.setEncoding("utf8");
        res.on("data", (chunk) => {
          data += chunk;
        });
        res.on("end", () => {
          if (res.statusCode !== 200) {
            reject(new Error(`HTTP ${res.statusCode}`));
            return;
          }
          try {
            resolve(JSON.parse(data));
          } catch (error) {
            reject(error);
          }
        });
      },
    );
    req.on("timeout", () => req.destroy(new Error("timeout")));
    req.on("error", reject);
    if (payload) req.write(payload);
    req.end();
  });
}

async function backendReady() {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    try {
      const health = await requestJson("/api/health");
      if (health.api_version === 1) return true;
    } catch {
      // Backend takes a moment to bind the local port.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  return false;
}

function applyWindowOptions() {
  if (!mainWindow) return;
  mainWindow.setAlwaysOnTop(Boolean(mainWindow.isAlwaysOnTop()), "floating");
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 420,
    height: 680,
    minWidth: 340,
    minHeight: 480,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.js"),
    },
  });
  mainWindow.loadURL(`${APP_ORIGIN}/`);
  mainWindow.once("ready-to-show", () => mainWindow.show());
  mainWindow.webContents.on("will-navigate", (event, url) => {
    if (!url.startsWith(APP_ORIGIN)) {
      event.preventDefault();
      if (/^[a-z][a-z0-9+.-]*:/i.test(url)) shell.openExternal(url);
    }
  });
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^[a-z][a-z0-9+.-]*:/i.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
  applyWindowOptions();
}

function createTray() {
  const iconPath = app.isPackaged
    ? path.join(process.resourcesPath, "icon.png")
    : path.join(__dirname, "..", "docs", "appicon-256.png");
  const icon = nativeImage.createFromPath(iconPath).resize({ width: 18, height: 18 });
  tray = new Tray(icon);
  tray.setToolTip("AgentTaskPanel");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "显示面板", click: () => mainWindow?.show() },
      {
        label: "置顶窗口",
        type: "checkbox",
        checked: false,
        click: (item) => mainWindow?.setAlwaysOnTop(item.checked, "floating"),
      },
      { label: "刷新", click: () => mainWindow?.webContents.reload() },
      { label: "退出", click: () => app.quit() },
    ]),
  );
  tray.on("double-click", () => mainWindow?.show());
}

function registerIpc() {
  ipcMain.handle("panel:pin", async () => requestJson("/api/pin", "POST"));
  ipcMain.handle("panel:notify", (_event, payload) => {
    if (Notification.isSupported()) {
      new Notification({
        title: String(payload?.title || "任务完成"),
        body: String(payload?.body || ""),
      }).show();
    }
  });
  ipcMain.handle("panel:open-external", async (_event, url) => {
    if (typeof url !== "string" || !/^[a-z][a-z0-9+.-]*:/i.test(url)) return false;
    await shell.openExternal(url);
    return true;
  });
  ipcMain.handle("panel:window", (_event, action) => {
    if (!mainWindow) return false;
    if (action === "minimize") mainWindow.minimize();
    else if (action === "close") mainWindow.close();
    else if (action === "toggle-top") {
      mainWindow.setAlwaysOnTop(!mainWindow.isAlwaysOnTop(), "floating");
    }
    return mainWindow.isAlwaysOnTop();
  });
  ipcMain.handle("panel:platform", () => process.platform);
}

function startHealthWatch() {
  healthTimer = setInterval(async () => {
    try {
      await requestJson("/api/health");
    } catch {
      if (!backend) startBackend();
    }
  }, HEALTH_INTERVAL_MS);
}

app.whenReady().then(async () => {
  Menu.setApplicationMenu(null);
  registerIpc();
  startBackend();
  if (!(await backendReady())) {
    throw new Error("Backend did not become ready");
  }
  createWindow();
  createTray();
  startHealthWatch();
});

app.on("before-quit", () => {
  quitting = true;
  if (healthTimer) clearInterval(healthTimer);
  if (backend && !backend.killed) backend.kill();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
