# readme-guardian

README freshness checks for fast-moving AI-assisted projects.

```bash
npx readme-guardian
npx readme-guardian --status
npx readme-guardian --apply
npx readme-guardian --check
```

The npm package is a thin Node.js wrapper around the Python CLI. It delegates with argument arrays, not shell interpolation, and installs/runs the Python package through `pipx` when the CLI is not already available.

## Install

```bash
npm install -g readme-guardian
readme-guardian --install-hook
```

For Python-first projects, install the CLI directly:

```bash
pipx install readme-guardian
```

## Safety

- No telemetry.
- No API keys.
- No hidden network calls from the Python CLI.
- The npm wrapper may use `pipx install readme-guardian` or `pipx run readme-guardian` only when the Python CLI is missing.
- The pre-push hook never rewrites git history. If it updates README files, it blocks the push and asks you to review and commit those changes.

Source: https://github.com/jeevesh2515/readme-guardian
