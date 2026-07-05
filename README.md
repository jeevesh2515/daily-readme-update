<p align="center">
  <a href="./readme-badge.svg">
    <img src="./readme-badge.svg" alt="README status" />
  </a>
  <img src="https://img.shields.io/badge/version-1.0-blue" alt="Version" />
  <img src="https://img.shields.io/badge/npm-readme--guardian-blue?logo=npm" alt="npm" />
  <img src="https://img.shields.io/badge/homebrew-readme--guardian-orange?logo=homebrew" alt="Homebrew" />

  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT" />
  <img src="https://img.shields.io/badge/PRs-welcome-orange" alt="PRs welcome" />
</p>

<h1 align="center">🛡️ readme-guardian</h1>

<h3 align="center">
  <i>The README freshness guarantee for vibe coders.</i>
</h3>

<p align="center">
  <b>One command. Zero config. Every push.</b>
  <br />
  Auto-syncs your README with live test counts, API routes, and modules.
  <br />
  Works with every AI agent, every language, every project.
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-install">Install</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-the-freshness-badge">The Badge</a> •
  <a href="#-for-ai-agents">For AI Agents</a> •
  <a href="#-ci-enforcement">CI</a> •
  <a href="#-comparison">Comparison</a>
</p>

<br />

<p align="center">
  <sup>
    <a href="https://www.npmjs.com/package/readme-guardian"><code>npm install -g readme-guardian</code></a> •
    <a href="https://github.com/jeevesh2515/homebrew-tap"><code>brew install readme-guardian</code></a> •
    <a href="https://pypi.org/project/readme-guardian"><code>pipx install readme-guardian</code></a>
  </sup>
</p>

<!-- readme-guardian:stats -->
| Metric | Value |
|--------|-------|
| Language | python |
| Version | 1.0.0 |
| Tests | — |
| Lint | — |
| Docker | no |
| Monorepo | no |
| Latest commit | `5558fcd fix: remove invalid PyPI classifier` |

<!-- /readme-guardian -->

---

## 🏅 The Freshness Badge

**This is the status symbol of the vibe coding era.**

Once you install readme-guardian, your repo gets a `readme-badge.svg` that updates on every push:

```
![readme-guardian](./readme-badge.svg)
```

<p align="center">
  <img src="./readme-badge.svg" alt="README status badge" />
</p>

**What it tells the world:**

| Badge color | Meaning | Trust level |
|-------------|---------|-------------|
| ![#4c1](https://placehold.co/15x15/4c1/4c1.png) Green | README is fresh, tests pass | ✅ High |
| ![#dfb317](https://placehold.co/15x15/dfb317/dfb317.png) Yellow | README synced but no tests | ⚠️ Medium |
| ![#e05d44](https://placehold.co/15x15/e05d44/e05d44.png) Red | README is stale | ❌ Low |

**Why this matters:** When a developer visits your repo and sees a green badge, they know instantly:
- The docs are accurate
- Tests were run recently
- This project is actively maintained

When they see a red badge, they know to be cautious. The badge doesn't lie because it's generated from live data on every push.

**It's also self-promoting.** Every repo with the badge advertises readme-guardian. The more repos use it, the more it becomes the standard for README freshness.

---

## 🤔 The Problem

You're vibe coding with an AI agent. You ship fast. PRs land. Push to GitHub.

The code is perfect. **The README still says "hello world" from day one.**

Your project looks abandoned. Contributors bounce. Users leave. Nobody trusts a project with a stale README.

> *"The README is the first thing people see. If it's wrong, they assume the code is too."*

---

## 🛡️ The Solution

```
npx readme-guardian --install
```

**That's it.** One command. Now before every `git push`, readme-guardian:

1. 🔍 Detects your stack (Node, Python, Go, Rust — monorepos too)
2. 🧪 Runs your tests and live-counts passes
3. 🗺️ Scans for API routes
4. 📦 Lists source modules and frontend components
5. 📝 Updates the README with verified data
6. ✅ **Only if something actually changed**

Your README is always accurate. You never think about it.

---

## 🚀 Quick Start

```bash
# Try it right now — no install needed
npx readme-guardian

# Then install for every push
npx readme-guardian --install-hook
```

## 📦 Install

Pick your poison:

### npm / npx (recommended for JS/TS projects)

```bash
# Run without installing (auto-installs Python CLI)
npx readme-guardian

# Install globally
npm install -g readme-guardian
readme-guardian --install-hook
```

### pipx (recommended for Python projects)

```bash
pipx install readme-guardian
readme-guardian --install-hook
```

### Homebrew (macOS)

```bash
brew install jeevesh2515/homebrew-tap/readme-guardian
readme-guardian --install-hook
```

### Commands

| Command | What it does |
|---------|-------------|
| `readme-guardian` | Interactive preview — see what would change |
| `readme-guardian --apply` | Apply changes immediately |
| `readme-guardian --check` | CI mode — exit 1 if README is stale |
| `readme-guardian --install-hook` | Install pre-push hook (runs automatically) |
| `readme-guardian --uninstall-hook` | Remove the pre-push hook |
| `readme-guardian --version` | Show version |

---

## 🧠 How It Works

### Zero-config detection

readme-guardian auto-detects your project by looking at your config files:

| File | What we learn |
|------|--------------|
| `package.json` | Name, version, scripts, frontend deps, workspaces |
| `pyproject.toml` | Name, version, test/lint tooling |
| `go.mod` | Module name, test command |
| `Cargo.toml` | Name, version, test command |

**No configuration files. No API keys. No setup.**

### What we collect

```
📁 Project root
 ├── Stack type       → Node / Python / Go / Rust
 ├── Test count       → Live from pytest / npm test / go test / cargo test
 ├── API routes       → FastAPI, Express, Next.js App Router, Go Chi/Gin
 ├── Source modules   → Python packages, Node modules, Go packages
 ├── UI components    → React, Vue, Svelte files
 ├── Lint status      → ruff, ESLint
 └── Git state        → Last commit hash and message
```

### What we generate

A clean, beautiful README with:
- **Live badges** — test count, version, lint status, Docker support
- **The freshness badge** — `![README](https://img.shields.io/badge/README-fresh-brightgreen)` — a status symbol that tells the world your docs are accurate
- **Quick start** — framework-aware install instructions
- **API route table** — all detected endpoints with methods
- **Module list** — source code directory structure
- **Component inventory** — frontend UI components
- **Test suite status** — live count, not a hardcoded number

### Non-destructive by design

If your README has `<!-- readme-guardian:stats -->` markers, only content between markers is replaced. Everything else — your narrative, architecture docs, contribution guidelines — stays intact.

If no markers exist, readme-guardian generates a complete README and asks first.

---

## 🤖 For AI Agents

This repo ships a companion **skill file** (`SKILL.md`) that turns any AI coding agent into a documentation partner.

### Installation

```bash
# Claude Code, OpenCode
cp SKILL.md ~/.agents/skills/readme-guardian/SKILL.md

# Codex CLI
cp SKILL.md ~/.codex/skills/readme-guardian/SKILL.md

# Cursor
# Add SKILL.md to .cursor/skills/
```

### How agents use it

```
You: "Update the README"
Agent: [runs readme-guardian, reviews diff, adds context about
       the architecture decisions made during this session,
       verifies the freshness badge matches test count]
```

The CLI handles **facts** (test counts, routes, versions). The agent handles **context** (why decisions were made, architectural rationale). Together they produce documentation that's both accurate and insightful.

### Compatible with

<p align="center">
  <b>Claude Code</b> •
  <b>Codex CLI</b> •
  <b>OpenCode</b> •
  <b>Cursor</b> •
  <b>GitHub Copilot</b> •
  <b>Continue.dev</b> •
  <b>Antigravity</b> •
  <b>Windsurf</b>
</p>

---

## 🔁 CI Enforcement

Add to any GitHub Actions workflow:

```yaml
# .github/workflows/readme-check.yml
on: pull_request
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install readme-guardian
      - run: readme-guardian --check
```

Any PR with a stale README **fails automatically**. No more merging docs that don't match reality.

---

## 📊 Comparison

| Feature | Manual | CI-only | **readme-guardian** |
|---------|--------|---------|-------------------|
| Auto-detect project type | ❌ | ❌ | ✅ |
| Live test count on push | ❌ | ❌ | ✅ |
| Scan for API routes | ❌ | ❌ | ✅ |
| List UI components | ❌ | ❌ | ✅ |
| Pre-push hook (zero effort) | ❌ | ❌ | ✅ |
| CI enforcement | ❌ | ✅ | ✅ |
| AI agent companion | ❌ | ❌ | ✅ |
| Freshness badge | ❌ | ❌ | ✅ |
| Works offline | ✅ | ❌ | ✅ |
| Zero config | ❌ | ❌ | ✅ |

---

## 🔐 Security

- **Zero network calls.** No telemetry, no API keys, no phone home.
- **No credential access.** Does not read `.env`, secrets, or config files.
- **Reads only source structure.** Scans for patterns, not content.
- **Suppressed build output.** All commands redirect stdout to logs.
- **Git-local.** Only modifies `README.md`. Never touches source code.
- **Ask-first mode.** Interactive mode shows diff before applying.

---

## 🌟 Why You'll Love It

**If you use AI agents**, you know the pain: agents ship code at machine speed but documentation stays human-slow. readme-guardian closes the gap. Your README becomes a build artifact — verified at push time, not remembered at documentation time.

**If you maintain open source**, the freshness badge is a trust signal. Projects with `README: fresh` attract contributors. Projects with stale READMEs repel them.

**If you're a team lead**, enforce README freshness in CI. Block PRs with stale docs. Make documentation a first-class citizen.

---

## 🧰 For Maintainers

```
.
├── README.md                  # This file — hand-crafted with markers
├── SKILL.md                   # AI agent companion skill
├── pyproject.toml             # Python package (pipx installable)
├── readme_sync/
│   ├── __init__.py            # CLI implementation
│   └── __main__.py            # python -m entry point
├── .github/workflows/         # CI enforcement (copy to your repo)
│   └── readme-check.yml
├── LICENSE                    # MIT
└── .gitignore
```

---

## 📜 License

MIT — do whatever you want. Fork it, modify it, use it in proprietary projects, include it in your own AI agent toolchains. Attribution appreciated but not required.

---

<p align="center">
  <a href="https://github.com/jeevesh2515/readme-guardian">
    <img src="https://img.shields.io/badge/%F0%9F%9B%A1%EF%B8%8F%20Star%20on%20GitHub-%E2%AD%90-brightgreen?style=for-the-badge" alt="Star on GitHub" />
  </a>
</p>

<p align="center">
  <sub>
    Built for the vibe coding era.
    <br />
    Documentation shouldn't be an afterthought — it should be a build artifact.
    <br />
    <b>Star this repo.</b> Your future self will thank you.
  </sub>
</p>
