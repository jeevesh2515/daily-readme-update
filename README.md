# readme-sync

**Auto-sync README.md with your actual codebase. Every push. Every PR. No exceptions.**

[![Version](https://img.shields.io/badge/version-1.0.0-orange)]()

---

README files lie. Not because developers are lazy — because documentation is a **different mode of thinking** from coding. You finish a feature, you're in flow, you push. The README describes what the code *used to do*, not what it *does now*.

`readme-sync` closes that gap with three layers of automation:

| Layer | What it does | When it runs |
|-------|-------------|-------------|
| **CLI** | Reads your project, runs tests, scans routes/modules, rewrites README | On demand via `pipx run readme-sync` |
| **Git hook** | Silently updates README before every push | `git push` — zero thought required |
| **CI check** | Fails the PR if README is stale | Every pull request |

Use all three. Or pick one. Any of them is better than a manual README.

---

<!-- readme-sync: stats -->
| Metric | Value |
|--------|-------|
| Language | python |
| Version | 1.0.0 |
| Tests | pending configuration |
| Lint | — |
| Docker | no |
| Latest commit | `851f5d4 feat: marker-based injection, LICENSE, .gitignore, CI workflow` |
<!-- /readme-sync -->

---

## Quick Start

### Install

```bash
# Recommended — isolated, always latest
pipx install readme-sync

# Or run without installing
npx readme-sync          # if published to npm
uvx readme-sync          # if published to PyPI

# Or clone and run directly
git clone https://github.com/jeevesh2515/daily-readme-update.git
cd daily-readme-update
pip install -e .
```

### Use

```bash
# Preview changes
readme-sync

# Apply changes
readme-sync --apply

# Install pre-push hook (runs automatically before every push)
readme-sync --install-hook
```

---

## How It Works

### Project Detection

`readme-sync` auto-detects your project type by scanning for common config files:

| File | Language | Features detected |
|------|----------|------------------|
| `pyproject.toml` | Python | Name, version, deps, pytest config, ruff config |
| `package.json` | Node/TypeScript | Name, version, scripts (test, build, lint) |
| `go.mod` | Go | Module name, build command |
| `Cargo.toml` | Rust | Name, version, build command |

No configuration file needed. Point it at any project root.

### Data Collection

After detection, it collects verified facts:

```
Project root
  ├── Type & metadata  (from pyproject.toml / package.json / go.mod / Cargo.toml)
  ├── Test count       (runs pytest / npm test / go test / cargo test)
  ├── API routes       (scans for FastAPI, Express, Gin, Next.js route definitions)
  ├── Source modules   (ls app/ src/ lib/ cmd/)
  ├── Frontend status  (runs tsc --noEmit, lists components)
  └── Lint status      (runs ruff / npm run lint / equivalent)
```

Every fact is **verified at runtime** — not guessed, not cached, not approximated.

### README Generation

The generated README uses **marker-based injection** — embed `<!-- readme-sync: stats -->
| Metric | Value |
|--------|-------|
| Language | python |
| Version | 1.0.0 |
| Tests | pending configuration |
| Lint | — |
| Docker | no |
| Latest commit | `851f5d4 feat: marker-based injection, LICENSE, .gitignore, CI workflow` |
<!-- /readme-sync -->` in your hand-crafted README and `readme-sync` only replaces what's between the markers. The rest of your narrative stays intact.

```markdown
# My Project

## Quick Start
...

<!-- readme-sync: stats -->
| Metric | Value |
|--------|-------|
| Language | python |
| Version | 1.0.0 |
| Tests | pending configuration |
| Lint | — |
| Docker | no |
| Latest commit | `851f5d4 feat: marker-based injection, LICENSE, .gitignore, CI workflow` |
<!-- /readme-sync -->

## Architecture
...
```

---

## Three-Layer Architecture

### Layer 1: CLI (`readme-sync`)

Run on demand during development:

```bash
# Interactive — shows diff, asks before applying
readme-sync

# Non-interactive — apply changes immediately
readme-sync --apply

# Silent — for git hooks and automation (no stdout)
readme-sync --pre-push

# CI mode — exit 1 if README is stale
readme-sync --check
```

### Layer 2: Git Pre-Push Hook

```bash
readme-sync --install-hook
```

Installs a `.git/hooks/pre-push` script that runs silently before every `git push`. If the README is stale, it updates it and amends the current commit. You never think about it again.

Remove with:

```bash
rm .git/hooks/pre-push
```

### Layer 3: CI Enforcement (GitHub Action)

Add to your repo:

```yaml
# .github/workflows/readme-check.yml
on: pull_request
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install readme-sync
      - run: readme-sync --check
```

Fails any PR where the README doesn't match the codebase. Auto-comments with the fix command.

---

## Supported Projects

| Type | Detection | Tests | Routes | Frontend |
|------|-----------|-------|--------|----------|
| **Python** (FastAPI, Flask, Django) | `pyproject.toml` | `pytest` | `@router.get/post/...` decorators | `frontend/src/components/` |
| **Node.js / TypeScript** (Express, Next.js, Fastify) | `package.json` | `npm test` | Express routes, Next.js app router, Fastify handlers | `tsc --noEmit`, `npm run build` |
| **Go** (Gin, Chi, net/http) | `go.mod` | `go test ./...` | `.Get()/.Post()` method calls | — |
| **Rust** (Axum, Actix, Rocket) | `Cargo.toml` | `cargo test` | — | — |

---

## Security

`readme-sync` is designed to be safe for any environment:

- **No external network calls.** Zero API requests. No telemetry. No phone home.
- **No credential access.** Does not read `.env`, secrets, or configuration files.
- **Reads only project files.** Scans source code for structural patterns, not content.
- **Suppressed build output.** Frontend build commands redirect stdout to prevent credential leakage in logs.
- **Marker-only edits.** Only replaces content between `<!-- readme-sync -->` markers. Never destructive.
- **Git-local only.** Only modifies `README.md`. Never touches source code, config, or deployment files.

---

## For AI Agents

This repository includes a companion skill file (`SKILL.md`) for AI coding agents. During active development, the agent handles the contextual parts of documentation (architecture decisions, design rationale) that the CLI can't generate.

Installation:

```bash
cp SKILL.md ~/.agents/skills/daily-readme-update/SKILL.md
```

Trigger: "update readme" or "sync documentation" during a coding session.

---

## The Stale README Problem (Why This Exists)

Every developer knows the feeling:

1. You read a project's README
2. You follow the "Quick Start" instructions
3. They don't work
4. You dig into the code, find the actual API, discover the README was written for v0.1 but the code is at v0.4

This erodes trust. A stale README signals "this project isn't maintained" — even if the code is actively developed.

The root cause isn't laziness. It's that **documentation is a different cognitive mode from coding**. You can't be in "ship this feature" mode and "update the docs" mode simultaneously. By the time you switch, you've already pushed.

`readme-sync` eliminates the mode switch. Documentation becomes a **build artifact** — verified at push time, not remembered at documentation time.

---

## Comparison

| Feature | Manual | CI-only | readme-sync |
|---------|--------|---------|-------------|
| Auto-detect project type | ❌ | ❌ | ✓ |
| Run tests + embed count | ❌ | ❌ | ✓ |
| Scan for API routes | ❌ | ❌ | ✓ |
| List frontend components | ❌ | ❌ | ✓ |
| Pre-push hook (zero effort) | ❌ | ❌ | ✓ |
| CI enforcement | ❌ | ✓ | ✓ |
| AI agent companion | ❌ | ❌ | ✓ |
| Works offline | ✓ | ❌ | ✓ |
| No config needed | ✓ | ❌ | ✓ |

---

## License

MIT — do whatever you want. Fork it, modify it, use it in proprietary projects, include it in your own toolchains. Attribution appreciated but not required.

---

<p align="center">
  <sub>Built for the vibe coding era. Documentation shouldn't be an afterthought — it should be a build artifact.</sub>
</p>
