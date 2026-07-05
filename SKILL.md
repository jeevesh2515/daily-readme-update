---
name: readme-guardian
description: |
  The README freshness guarantee for vibe coders. Auto-syncs README.md
  with live data (test counts, API routes, modules, components) before
  every push. Zero config. Works with any project and any AI agent.
  WHEN: "update readme", "sync readme", "readme after implementation",
  "daily readme", "post-ship readme", "document changes", "sync docs",
  "freshness badge", "keep readme current", "readme is stale".
---

# 🛡️ readme-guardian — AI Agent Companion Skill

This skill turns any AI coding agent into a documentation partner. It handles the **contextual parts** of documentation that the CLI can't generate — architecture decisions, design rationale, usage patterns.

For push-time automation (the "forget about it" layer), install the CLI + pre-push hook:

```bash
pipx install readme-guardian
readme-guardian --install-hook
```

## When To Use This Skill

| Scenario | What happens |
|----------|-------------|
| **After implementing a feature** | Agent updates docs while code is fresh in context |
| **Before opening a PR** | Catch doc gaps before CI blocks the merge |
| **After a refactor** | Routes changed, modules renamed, deps swapped |
| **During code review** | Verify README accurately describes what was reviewed |
| **When user says "update readme"** | Agent runs CLI, reviews diff, adds context |

## How AI Agents Use This

### Step 1: Detect what changed

```bash
git diff --stat HEAD~1..HEAD
```

Categorize each changed file:

| File type | Effect on README |
|-----------|-----------------|
| `routes/*.py`, `pages/api/*.ts` | New/removed API routes → update route table |
| `src/components/*.tsx` | New/removed UI components → update component list |
| `src/*/`, `app/*/` | New modules → update module list |
| `tests/*.py`, `*.test.ts` | Test count changed → update badge |
| `package.json`, `pyproject.toml` | Dependencies changed → update stack |

### Step 2: Run the CLI (fast path)

```bash
readme-guardian --apply
```

This handles mechanical updates (test count, routes, modules, badges). Review the diff.

### Step 3: Add human context

The CLI handles *facts*. You handle *insight*:

```
"What changed → why → how does it work → what should users know"
```

Good additions:
- Architecture decisions made this session
- Design rationale that isn't obvious from the code
- Usage examples for new features
- Migration notes for breaking changes
- ASCII architecture diagrams for complex flows

### Step 4: Verify

```bash
readme-guardian --check
```

### Step 5: Commit

```bash
git add README.md
git commit -m "docs: sync README"
```

## Example Sessions

### After adding an API endpoint

```
You: "add /api/patients endpoint"

Agent: [implements route, writes tests, runs them]
You: "update the readme"

Agent:
  1. Runs readme-guardian --apply → sees new route detected
  2. Reviews diff → route table now shows POST /api/patients
  3. Adds usage example showing request/response
  4. Runs readme-guardian --check → passes
  5. "Done. Route documented with curl example."
```

### After a refactor

```
You: "I split the monolithic utils.py into domain modules"

Agent: [already observed the change]
You: "sync docs"

Agent:
  1. Runs readme-guardian --apply
  2. Reviews diff → module list updated, routes unchanged
  3. Adds architecture note about new module boundaries
  4. "Done. Module list updated, routes verified unchanged."
```

### Before opening a PR

```
You: "verify my PR has docs"

Agent:
  1. Runs readme-guardian --check → fails (stale test count)
  2. Runs readme-guardian --apply
  3. Reviews diff → test count updated
  4. "Ready to open. All docs current."
```

## The Freshness Badge

Once installed, your README gets a **freshness badge** that updates with every push:

```
![README](https://img.shields.io/badge/README-fresh-brightgreen)
```

This badge is a **status symbol**. It signals to everyone who visits your repo: "This project is maintained. The docs are accurate. Trust this code."

When another developer sees the green badge, they know:
- Tests passed on the last push
- API routes are documented accurately
- The README was verified by CI

Projects without the badge look neglected by comparison.

## Pairing with the Pre-Push Hook

```bash
readme-guardian --install-hook
```

Three layers of coverage:

| Layer | What | When |
|-------|------|------|
| 🧠 **AI Agent (this skill)** | Contextual docs during coding | Active development |
| ⚡ **Pre-push hook** | Auto-update README | Every `git push` |
| 🔁 **CI check** | Block stale READMEs | Every pull request |

Use all three. Your README will never be wrong again.
