---
name: readme-guardian
description: Keep README.md current after coding work by checking, safely initializing, and updating readme-guardian managed facts such as test status, API routes, modules, components, project version, Docker support, monorepo status, and readme-badge.svg. Use when the user asks to update, sync, check, verify, refresh, or maintain a README after implementation, refactors, PR preparation, stale README fixes, or AI-assisted documentation drift.
---

# README Guardian

Keep the README's machine-verifiable facts current without replacing the project's hand-written documentation. Use the CLI for facts and add only context that requires engineering judgment.

## Workflow

1. Work from the repository root. Inspect the implementation and its docs impact before editing:

```bash
git status --short
git diff --stat
readme-guardian --status
```

2. When the status command reports that README management is not initialized, explain that the tool will append managed sections rather than rewrite prose. Initialize only after the user asks to enable the guard:

```bash
readme-guardian --init
```

3. Preview mechanical changes before writing:

```bash
readme-guardian
```

4. Apply the managed facts and then add human context where the implementation warrants it:

```bash
readme-guardian --apply
```

Add concise explanations of new behavior, user-facing examples, migration notes, or architecture decisions. Do not describe features the code does not provide.

5. Run project checks only in a repository the user trusts and only when live test or lint status is needed:

```bash
readme-guardian --apply --run-checks
```

`--run-checks` may invoke the repository's own test and lint commands. Treat that as executing project code, not as a passive README operation.

6. Verify before completing the task:

```bash
readme-guardian --check
```

Use `readme-guardian --check --run-checks` in trusted CI when the README should contain the latest test outcome.

## Safety Rules

- Default to preview and status modes; they do not run project test or lint commands.
- Never replace an unmarked README. Use `--init`, which appends managed sections, or edit prose deliberately.
- Review the README diff after `--apply`.
- Do not bypass a pre-push hook that blocks because README files already have uncommitted changes.
- The CLI refuses to write symlinked `README.md`, `readme-badge.svg`, or pre-push hooks.

## Commands

| Command | Use |
|---|---|
| `readme-guardian --status` | Report whether managed facts and the badge are current. |
| `readme-guardian` | Preview exact managed-file changes. |
| `readme-guardian --init` | Append managed sections without replacing existing prose. |
| `readme-guardian --apply` | Update only managed sections and `readme-badge.svg`. |
| `readme-guardian --run-checks` | Explicitly run detected test and lint commands. |
| `readme-guardian --check` | Exit nonzero when initialized managed files are stale. |
| `readme-guardian --install-hook` | Install a standalone pre-push hook when none exists. |
| `readme-guardian --uninstall-hook` | Remove only the exact hook installed by this tool. |
