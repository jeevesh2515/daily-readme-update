<p align="center">
  <img src="https://img.shields.io/badge/version-1.1.2-1b75bb?style=flat-square" alt="Version 1.1.2" />
  <img src="https://img.shields.io/badge/license-MIT-2ea44f?style=flat-square" alt="MIT license" />
  <img src="https://img.shields.io/badge/AI--agent-ready-111827?style=flat-square" alt="AI agent ready" />
</p>

# readme-guardian

Keep a project's machine-verifiable README facts current while preserving its human-written story. Detect drift, preview the change, and generate a local green, yellow, or red README status badge.

## Quick Start

This npm package is a small Node.js launcher for the matching Python wheel bundled inside this tarball. It needs [pipx](https://pipx.pypa.io/stable/installation/) available on `PATH`.

```bash
npm install -g readme-guardian

# Check README freshness without writing files or running project commands.
readme-guardian --status

# Append managed sections once, then preview and apply updates.
readme-guardian --init
readme-guardian
readme-guardian --apply

# Enforce current generated facts in CI.
readme-guardian --check
```

Install the optional guarded pre-push hook with `readme-guardian --install-hook`. When it refreshes generated README content, it stops that push for review and a commit; it never amends commits or rewrites history.

## Safety

- The Python CLI has no telemetry and makes no network calls.
- It never replaces an unmarked README and writes only managed README sections plus `readme-badge.svg`.
- It refuses symlinked write targets and uses bounded, symlink-skipping source scans.
- Project test and lint commands run only after explicit `--run-checks` consent.
- The launcher uses argument arrays and the wheel already inside this npm tarball; it does not interpolate user input into a shell or install a global Python package.

For the full agent skill, status-badge semantics, security policy, source, and release checksums, visit [jeevesh2515/readme-guardian](https://github.com/jeevesh2515/readme-guardian).
