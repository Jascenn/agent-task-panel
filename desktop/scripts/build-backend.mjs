import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const desktop = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const root = path.resolve(desktop, "..");
const resources = path.join(desktop, "resources");
const output = path.join(resources, "backend");
const work = path.join(desktop, ".pyinstaller");
const separator = process.platform === "win32" ? ";" : ":";
const python = process.env.AGENT_PANEL_PYTHON || (process.platform === "win32" ? "python.exe" : "python3");
const data = `${path.join(resources, "agent-task-dashboard.html")}${separator}.`;

fs.rmSync(output, { recursive: true, force: true });
fs.mkdirSync(output, { recursive: true });
fs.mkdirSync(work, { recursive: true });

const args = [
  "-m",
  "PyInstaller",
  "--noconfirm",
  "--clean",
  "--onefile",
  "--name",
  "agent-task-backend",
  "--distpath",
  output,
  "--workpath",
  work,
  "--specpath",
  work,
  "--add-data",
  data,
];
if (process.platform === "win32") args.push("--noconsole");
args.push(path.join(resources, "server.py"));

const result = spawnSync(python, args, {
  cwd: root,
  stdio: "inherit",
  env: { ...process.env, PYTHONPATH: path.join(root, "src") },
});

if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);

const binary = path.join(
  output,
  process.platform === "win32" ? "agent-task-backend.exe" : "agent-task-backend",
);
if (!fs.existsSync(binary)) throw new Error(`Backend executable not produced: ${binary}`);
if (process.platform !== "win32") fs.chmodSync(binary, 0o755);
console.log(`Built backend: ${binary}`);
