# Security Policy

## Supported Versions

Security fixes are released in the latest version of `readme-guardian`.

## Privacy and Data Handling

The Python CLI runs locally. It does not send telemetry, source code, README content, test output, or repository metadata to any server.

The CLI reads project metadata files such as `package.json`, `pyproject.toml`, `go.mod`, and `Cargo.toml`; scans source files for route/component/module patterns; may run local test or lint commands detected from the project; and writes only `README.md` and `readme-badge.svg`.

Test and lint commands are the project's own commands, such as `npm test`, `go test ./...`, `cargo test`, `.venv/bin/python -m pytest -q`, or `.venv/bin/python -m ruff check .`. Run readme-guardian only in repositories you trust, the same way you would only run that repository's tests if you trust the project.

The npm package is a wrapper. If the Python CLI is missing, it may call `pipx install readme-guardian` or `pipx run readme-guardian` so npm/npx users can run the tool. That network access is package installation, not telemetry.

## Git Hook Safety

The pre-push hook does not rewrite history or amend commits. If README files are updated during a push, the hook blocks the push and asks the user to review and commit the changes.

## Reporting a Vulnerability

Please report security issues privately through GitHub Security Advisories:

https://github.com/jeevesh2515/readme-guardian/security/advisories/new

If advisories are unavailable, open a minimal issue asking for a private security contact without posting exploit details.
