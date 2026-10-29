const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const ROOT = path.resolve(__dirname, "..");
const mainSource = fs.readFileSync(path.join(ROOT, "main.js"), "utf8");

test("backend resources exist", () => {
  for (const name of ["agent-task-dashboard.html", "server.py", "platforms.py"]) {
    assert.ok(fs.existsSync(path.join(ROOT, "resources", name)), `${name} missing`);
  }
});

test("packaging icon exists", () => {
  const icon = path.join(ROOT, "build", "icon.png");
  assert.ok(fs.existsSync(icon), "build/icon.png missing; run sync-resources.mjs");
  assert.ok(fs.statSync(icon).size > 0, "build/icon.png is empty");
});

test("desktop shell uses a versioned health probe", () => {
  assert.match(mainSource, /health\.api_version === 1/);
});

test("desktop shell exposes only narrow preload capabilities", () => {
  assert.match(mainSource, /contextIsolation: true/);
  assert.match(mainSource, /nodeIntegration: false/);
  assert.doesNotMatch(mainSource, /nodeIntegration: true/);
});

test("external links accept only explicit URL schemes", () => {
  assert.match(mainSource, /\^\[a-z\]\[a-z0-9\+\.\-\]\*:/i);
});
