# Security Policy

## Supported Versions

Security fixes are released in the latest version of `readme-guardian`.

## Privacy and Data Handling

The Python CLI runs locally. It does not send telemetry, source code, README content, test output, or repository metadata to any server.

The CLI reads project metadata files such as `package.json`, `pyproject.toml`, `go.mod`, and `Cargo.toml`, and scans eligible source files for route/component/module patterns. Scanning skips symlinks, common generated directories, files above 1 MB, and stops after 2,500 files.

By default, readme-guardian does not run a project's test or lint commands. `--run-checks` explicitly opts into the project's own commands, such as `npm test`, `go test ./...`, `cargo test`, `.venv/bin/python -m pytest -q`, or `.venv/bin/python -m ruff check .`. Run that flag only in repositories you trust, just as you would run their tests directly.

The npm package contains the matching Python wheel and uses `pipx run` to execute it in an isolated environment. It does not silently install a global Python package or download a second package from PyPI. Installing the npm package itself uses npm's normal package-download path.

The CLI writes only `README.md` managed sections and `readme-badge.svg`. `--init` appends managed sections instead of replacing an existing README. It refuses to follow symlinks for either target or for a pre-push hook.

## Git Hook Safety

The pre-push hook does not rewrite history, amend commits, or overwrite another hook. It refuses to run when README files already have uncommitted changes. If it updates README files during a push, it blocks the push and asks the user to review and commit the changes.

## Reporting a Vulnerability

Please report security issues privately through GitHub Security Advisories:

https://github.com/jeevesh2515/readme-guardian/security/advisories/new

If advisories are unavailable, open a minimal issue asking for a private security contact without posting exploit details.
