import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const desktop = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const root = path.resolve(desktop, "..");
const resources = path.join(desktop, "resources");
fs.mkdirSync(resources, { recursive: true });

for (const [source, target] of [
  ["resources/panel.html", "agent-task-dashboard.html"],
  ["src/server.py", "server.py"],
  ["src/platforms.py", "platforms.py"],
]) {
  fs.copyFileSync(path.join(root, source), path.join(resources, target));
}

// electron-builder 打包时需要 PNG 图标，构建目录不提交，统一在同步阶段生成。
fs.mkdirSync(path.join(desktop, "build"), { recursive: true });
fs.copyFileSync(
  path.join(root, "docs", "appicon.png"),
  path.join(desktop, "build", "icon.png"),
);

console.log(`Synced desktop resources from ${root}`);
