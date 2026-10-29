# docs / 文档目录

| Path / 路径 | Content / 内容 |
|---|---|
| `index.html` | Project homepage for Cloudflare Pages / Cloudflare Pages 项目主页 |
| `robots.txt` `sitemap.xml` | Search-engine discovery / 搜索引擎发现配置 |
| `_headers` | Cloudflare Pages security and cache headers / 安全与缓存响应头 |
| `screenshots/` | Clear (light/dark), solid and frost panel screenshots / 透明（白底/深色底）、纯色与毛玻璃面板截图 |
| `screenshots/social-card.png` | 1200×630 Open Graph preview / 社交分享预览图 |
| `appicon.png` `appicon-256.png` | App icon renders / App 图标渲染图 |
| `dev/BUILD-RELEASE.zh-CN.md` | Build, signing & release workflow / 构建、签名与发布流程 |
| `dev/API-CONTRACT.zh-CN.md` | Versioned local API contract for desktop clients / 桌面客户端本地 API 契约 |
| `dev/STATUS-DETECTION.zh-CN.md` | How running/done/idle is decided per agent / 各渠道任务状态判定规则 |
| `install/install-notes-template.txt` | Bilingual install guide shipped inside the DMG / DMG 内附带的中英双语安装说明模板 |
| `api/tasks-v1.schema.json` | Machine-readable tasks response schema / 任务 API 的机器可读 Schema |

## Automation / 自动化

| Workflow / 工作流 | Trigger / 触发条件 | Purpose / 用途 |
|---|---|---|
| `.github/workflows/ci.yml` | Pull requests, `main` | Build and verify the app / 构建并校验 App |
| `.github/workflows/codeql.yml` | Pull requests, `main`, weekly | CodeQL for Python and Actions / 安全扫描 |
| `.github/workflows/codeql-swift.yml` | Swift changes, `main`, weekly | CodeQL for Swift / Swift 安全扫描 |
| `.github/workflows/release.yml` | `v*` tags | Build, verify and publish the DMG / 构建、校验并发布 DMG |
| `.github/workflows/deploy-pages.yml` | `docs/**` on `main` | Deploy the website to Cloudflare Pages / 发布官网 |

## Deployment / 部署

Changes to this directory are deployed to the existing `agentpanel` Cloudflare Pages project by
`.github/workflows/deploy-pages.yml` after they reach `main`. The workflow can also be started
manually from GitHub Actions.

本目录的改动合并到 `main` 后，由 `.github/workflows/deploy-pages.yml` 自动发布到现有的
`agentpanel` Cloudflare Pages 项目；也可以在 GitHub Actions 中手动触发。
