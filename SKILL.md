---
name: readme-guardian
description: |
  Keep README.md current after coding work by checking, previewing, and
  updating readme-guardian managed facts such as test status, API routes,
  modules, UI components, project version, Docker support, monorepo status,
  latest commit, and readme-badge.svg. Use when the user asks to update,
  sync, check, verify, refresh, or maintain a README after implementation,
  refactors, PR preparation, daily docs updates, post-ship documentation,
  freshness badges, stale README fixes, or AI/vibe-coding documentation drift.
---

# readme-guardian AI Agent Companion Skill

Use this skill to keep README.md honest while a project changes quickly. Let the CLI handle mechanical facts. Add only the contextual documentation that requires judgment: what changed, why it matters, how users should use it, and any migration notes.

For push-time automation, install the CLI and pre-push hook:

```bash
pipx install readme-guardian
readme-guardian --install-hook
```

## Workflow

1. Inspect the repository changes before touching docs:

```bash
git status --short
git diff --stat
```

Categorize each changed file:

| File type | Effect on README |
|-----------|-----------------|
| `routes/*.py`, `pages/api/*.ts` | New/removed API routes → update route table |
| `src/components/*.tsx` | New/removed UI components → update component list |
| `src/*/`, `app/*/` | New modules → update module list |
| `tests/*.py`, `*.test.ts` | Test count changed → update badge |
| `package.json`, `pyproject.toml` | Dependencies changed → update stack |

2. Check README freshness without writing files:

```bash
readme-guardian --status
```

Use plain `readme-guardian` when you want a unified diff preview of the exact README.md and readme-badge.svg changes.

3. Apply mechanical README and badge updates when the user wants docs updated:

```bash
readme-guardian --apply
```

This updates only README.md and readme-badge.svg. With markers such as `<!-- readme-guardian:stats -->`, it replaces only managed sections. Without markers, it previews by default and regenerates only when `--apply` is explicit.

4. Review the diff and add human context if needed:

The CLI handles facts. Add insight:

```
"What changed → why → how does it work → what should users know"
```

Good additions:
- Architecture decisions made this session
- Design rationale that isn't obvious from the code
- Usage examples for new features
- Migration notes for breaking changes
- ASCII architecture diagrams for complex flows

5. Verify before finishing:

```bash
readme-guardian --check
```

`--check` exits 0 when README.md and readme-badge.svg match the current project facts. It exits 1 when either file is stale.

6. Commit docs with the relevant code or as a focused docs commit:

```bash
git add README.md
git commit -m "docs: sync README"
```

## CLI Commands

| Command | Use |
|---------|-----|
| `readme-guardian` | Preview exact README.md and badge changes without writing. |
| `readme-guardian --status` | Show whether README.md and readme-badge.svg are current. |
| `readme-guardian --apply` | Write README.md and readme-badge.svg updates. |
| `readme-guardian --check` | CI-safe check; exit 1 when docs are stale. |
| `readme-guardian --install-hook` | Install a pre-push hook that applies updates automatically. |
| `readme-guardian --uninstall-hook` | Remove the pre-push hook. |

## Example Sessions

### After adding an API endpoint

```
You: "add /api/patients endpoint"

Agent: [implements route, writes tests, runs them]
You: "update the readme"

Agent:
  1. Runs readme-guardian to preview the route table change
  2. Runs readme-guardian --apply
  3. Adds usage example showing request/response
  4. Runs readme-guardian --check
  5. "Done. Route documented with curl example."
```

### After a refactor

```
You: "I split the monolithic utils.py into domain modules"

Agent: [already observed the change]
You: "sync docs"

Agent:
  1. Runs readme-guardian --status
  2. Runs readme-guardian --apply
  3. Adds architecture note about new module boundaries
  4. Runs readme-guardian --check
```

### Before opening a PR

```
You: "verify my PR has docs"

Agent:
  1. Runs readme-guardian --check
  2. Runs readme-guardian --apply
  3. Reviews diff
  4. Runs readme-guardian --check
```

## The Freshness Badge

Once installed, your README gets a **freshness badge** that updates with every push:

```
![readme-guardian](./readme-badge.svg)
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
| AI Agent (this skill) | Contextual docs during coding | Active development |
| Pre-push hook | Auto-update README | Every `git push` |
| CI check | Block stale READMEs | Every pull request |

Use all three. Your README will never be wrong again.
