---
name: daily-readme-update
description: |
  Three-layer README sync system. CLI tool (`readme-sync`) that auto-detects
  project type and rewrites README.md with verified test counts, routes, and
  dependencies. Git pre-push hook for zero-effort automation. Companion skill
  for AI agents that want smart documentation during coding sessions.
  WHEN: "update readme", "sync readme", "readme after implementation",
  "daily readme", "post-ship readme", "document changes", "sync documentation".
---

# Daily README Update — AI Agent Skill

This is the AI companion skill for the [readme-sync](https://github.com/jeevesh2515/daily-readme-update) ecosystem. It handles documentation during active coding sessions. For push-time automation, install the pre-push hook or the GitHub Action instead.

## Ecosystem

```
┌──────────────────────────────────────────────────────────────┐
│                   readme-sync ecosystem                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. CLI tool (readme-sync)                                   │
│     pipx run readme-sync                                     │
│     → Detects project, runs tests, scans routes, updates     │
│                                                              │
│  2. Git pre-push hook (install once)                         │
│     readme-sync --install-hook                               │
│     → Runs silently before every git push                    │
│                                                              │
│  3. GitHub Action (CI enforcement)                           │
│     → PRs fail if README is stale                            │
│                                                              │
│  4. AI Agent skill (this file)                               │
│     → Smart docs during coding sessions                      │
│                                                              │
│  Use all three for maximum coverage.                         │
│  Any one of them is better than a manual README.             │
└──────────────────────────────────────────────────────────────┘
```

## When To Use This Skill

Use this during **active development** when the CLI tool isn't enough:

1. **After implementing a new feature** — tell the agent to update docs while the code is fresh
2. **When refactoring** — routes changed, modules renamed, dependencies swapped
3. **Before opening a PR** — catch documentation gaps the CI check will flag
4. **During code review** — verify the README accurately describes what was reviewed

## Instructions For AI Agents

### Step 1: Detect what changed

```bash
git diff --stat HEAD~1..HEAD
```

For each changed file, determine if it affects:
- **API surface** (new/removed routes, changed schema) → update API docs
- **Modules** (new/removed packages/directories) → update architecture
- **Dependencies** (new/removed packages) → update stack table
- **Frontend** (new/removed components) → update feature list
- **Tests** (new test files) → update test count + coverage table

### Step 2: Run the CLI tool (fast path)

If `readme-sync` is installed, run it first — it handles the mechanical updates:

```bash
pipx run readme-sync --apply
```

Then review the diff and add any context the CLI couldn't generate (architecture decisions, design rationale, usage examples).

### Step 3: Add human context

The CLI tool handles *facts* (test counts, routes, deps). You handle *context*:

- **Why** was this feature added? (problem it solves)
- **How** does it work at a high level? (architecture, data flow)
- **What** makes this implementation notable? (design decisions, trade-offs)
- **Who** is this for? (target users, use cases)

### Step 4: Verify

```bash
# The README must be truthful — verify every claim
pipx run readme-sync --check
```

### Step 5: Commit

```bash
git add README.md
git commit -m "docs: sync README with $(git log -1 --oneline --format=%s)"
```

## Example Sessions

### After adding a new API endpoint

```
You: "add /api/patients endpoint to the FastAPI app"
Agent: [implements route, adds tests, runs them]
You: "update readme"
Agent: [runs readme-sync, sees new route detected,
       adds POST /api/patients to API table, verifies check passes]
```

### After a refactor

```
You: "I split the monolithic utils.py into domain modules"
Agent: [already seen the change, runs readme-sync]
Agent: "Updated module list, verified routes unchanged, tests still pass"
```

### Before opening a PR

```
You: "verify my PR is documented"
Agent: [runs readme-sync --check, finds stale test count,
       runs readme-sync --apply, reviews diff, adds usage example]
```

## Pairing With The Pre-Push Hook

For maximum coverage, install the pre-push hook too:

```bash
pipx run readme-sync --install-hook
```

This way:
- During coding: the AI agent updates docs as you work (this skill)
- Before push: the git hook auto-syncs anything missed
- In CI: the GitHub Action blocks stale READMEs from merging

Three layers. One goal: documentation that matches reality.
