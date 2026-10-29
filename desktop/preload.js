const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("agentPanel", {
  platform: process.platform,
  notify: (payload) => ipcRenderer.invoke("panel:notify", payload),
  openExternal: (url) => ipcRenderer.invoke("panel:open-external", url),
  windowAction: (action) => ipcRenderer.invoke("panel:window", action),
});
