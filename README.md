# readme-guardian

![Version](https://img.shields.io/badge/version-1.1.1-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Keep the facts in a fast-moving project's README current without letting an AI agent rewrite its story. `readme-guardian` detects a supported project's routes, modules, components, version, and optional test/lint result; it updates only explicitly managed README sections and a local status badge.

It is built for AI-assisted development, where code changes quickly and README drift is easy to miss.

<!-- readme-guardian:stats -->
| Metric | Value |
|--------|-------|
| Language | python |
| Version | 1.1.1 |
| Tests | not configured |
| Lint | — |
| Docker | no |
| Monorepo | no |

<!-- /readme-guardian -->

## Start here

Run from the root of a Node, Python, Go, or Rust repository:

```bash
# Inspect only: no README changes and no project commands are run.
readme-guardian --status

# One-time setup: append managed sections without replacing your existing README.
readme-guardian --init

# Preview the exact README.md and badge changes.
readme-guardian

# Update managed sections after reviewing the preview.
readme-guardian --apply

# Verify in CI or before a PR.
readme-guardian --check
```

Use `--run-checks` only when you trust the project and want the README to record a fresh test and lint result:

```bash
readme-guardian --apply --run-checks
readme-guardian --check --run-checks
```

`--run-checks` may execute the repository's own `npm test`, `pytest`, `go test`, `cargo test`, or lint command. A normal status, preview, apply, or check never runs those commands.

## Install

### GitHub release wheel

The published release assets are the canonical way to install `1.1.0` until the package registries carry the same version:

```bash
pipx install "https://github.com/jeevesh2515/readme-guardian/releases/download/v1.1.1/readme_guardian-1.1.1-py3-none-any.whl"
readme-guardian --version
```

Install [pipx](https://pipx.pypa.io/stable/installation/) first if it is not available. Each GitHub release publishes SHA-256 digests alongside its assets.

### npm / npx

The npm tarball includes the matching Python wheel, so it does not silently download a second package from PyPI. It runs that wheel with `pipx` in an isolated environment.

```bash
npm install -g "https://github.com/jeevesh2515/readme-guardian/releases/download/v1.1.1/readme-guardian-1.1.1.tgz"
readme-guardian --status
```

The public npm registry has a 24-hour cooldown after its previous unpublish. PyPI currently serves `1.1.0`; `1.1.1` will be published to both registries by the Trusted Publishing workflow after the npm cooldown.

Maintainers can publish without storing registry credentials by configuring the included [Trusted Publishing workflow](PUBLISHING.md).

## What it manages

`readme-guardian --init` adds a `## Project facts` area with marker-delimited sections such as:

```markdown
<!-- readme-guardian:stats -->
| Metric | Value |
|--------|-------|
| Language | python |
| Version | 1.1.1 |
| Tests | not configured |
| Lint | — |
| Docker | no |
| Monorepo | no |

<!-- /readme-guardian -->
```

Later runs replace only content between those markers. Your introduction, architecture notes, screenshots, examples, contribution guide, and all other prose stay yours.

| Fact | Detection |
|---|---|
| Project name and version | `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod` |
| API routes | FastAPI/Flask, Express/Fastify, Next.js App Router, common Go patterns |
| Modules and components | Conventional Python, Node, Go, Rust, React, Vue, and Svelte layouts |
| Test and lint result | Optional, only with `--run-checks` |
| Docker and monorepo hints | Conventional project files |

The detector is intentionally conservative. A current status means the managed facts match what this tool can detect; it is not a claim that every sentence in a README is correct.

## Status badge

`--init` creates `readme-badge.svg`, which can be displayed from the repository itself:

```markdown
![README status](./readme-badge.svg)
```

| Color | Meaning |
|---|---|
| Green | Managed facts were generated with passing tests. |
| Yellow | Managed facts are synced, but checks were skipped or no test command was configured. |
| Red | The last explicitly requested test run failed or timed out. |

Run `readme-guardian --check` in CI to catch source changes that make the managed facts stale.

## Git and CI

Install a pre-push hook after initialization:

```bash
readme-guardian --install-hook
```

The hook runs checks only because you explicitly installed it. It never rewrites history or amends commits. It refuses to replace an existing hook, refuses to run over uncommitted README or badge changes, and blocks a push when it produces updates so those updates can be reviewed and committed.

For CI, use the same two-stage pattern in a trusted repository:

```yaml
- run: pipx install readme-guardian==1.1.0
- run: readme-guardian --check --run-checks
```

Use the GitHub release wheel URL above until `1.1.0` is published to PyPI.

## AI agent skill

The repository includes a concise [`SKILL.md`](SKILL.md) with a safe workflow for agents: inspect, initialize once, preview, apply managed facts, add human context, and verify.

OpenCode discovers project skills at `.opencode/skills/<name>/SKILL.md` and global skills at `~/.config/opencode/skills/<name>/SKILL.md`. For a project-local setup:

```bash
mkdir -p .opencode/skills/readme-guardian
cp /path/to/readme-guardian/SKILL.md .opencode/skills/readme-guardian/SKILL.md
```

Codex users can use the same file in `~/.codex/skills/readme-guardian/SKILL.md`.

## Security model

- The Python CLI has no telemetry and makes no network requests.
- It never replaces an unmarked README. `--init` appends managed sections.
- It writes only managed content in `README.md` and `readme-badge.svg`.
- It refuses to follow symlinks for README, badge, or hook writes.
- Source scanning skips symlinks, common generated directories, files over 1 MB, and stops after 2,500 files.
- It does not execute project commands unless `--run-checks` is explicitly passed.
- The npm wrapper uses argument arrays and the wheel bundled inside its verified npm tarball; it does not globally install Python packages.
- The tool cannot make an untrusted repository safe to execute. Run `--run-checks` only in codebases you trust.

See [SECURITY.md](SECURITY.md) for the complete policy and private disclosure path.

## Contributing

Contributions that improve detection accuracy, guardrails, tests, or agent interoperability are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md), follow the [Code of Conduct](CODE_OF_CONDUCT.md), and open an issue with a small reproducible project shape.

## License

[MIT](LICENSE)
