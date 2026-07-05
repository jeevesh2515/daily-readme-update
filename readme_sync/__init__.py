#!/usr/bin/env python3
"""
readme-sync — Auto-sync README.md with your actual codebase.

Detects project type, runs tests, scans routes/modules, checks frontend build,
and rewrites README.md with verified data. Designed for pre-push hooks, CI,
and AI-agent workflows.

Usage:
    readme-sync                  # Interactive: diff + confirm changes
    readme-sync --apply          # Apply changes without confirmation
    readme-sync --pre-push       # Silent mode for git hooks (no output on success)
    readme-sync --check          # CI mode: exit 1 if README is stale
    readme-sync --install-hook   # Install git pre-push hook

Install:
    pipx install readme-sync
    # or
    uvx readme-sync
"""

import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any


def debug(msg: str) -> None:
    """Print debug message to stderr (invisible to --pre-push mode)."""
    if "--pre-push" in sys.argv:
        return
    print(f"  ℹ {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    if "--pre-push" in sys.argv:
        return
    print(f"  ⚠ {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    if "--pre-push" in sys.argv:
        return
    print(f"  ✓ {msg}", file=sys.stderr)


def fail(msg: str) -> None:
    if "--pre-push" in sys.argv:
        return
    print(f"  ✗ {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Project detection
# ---------------------------------------------------------------------------

Project = dict[str, Any]


def detect_project(root: Path) -> Project:
    """Detect project type, name, and metadata."""
    info: Project = {
        "root": root,
        "type": None,
        "name": None,
        "version": None,
        "description": None,
        "has_frontend": False,
        "has_tests": False,
        "has_docker": False,
        "test_command": None,
        "build_command": None,
        "lint_command": None,
        "routes": [],
        "modules": [],
        "frontend_components": [],
        "test_count": 0,
        "lint_passes": None,
    }

    # Python project
    if (root / "pyproject.toml").exists():
        info["type"] = "python"
        try:
            with open(root / "pyproject.toml") as f:
                content = f.read()
            m = re.search(r'name\s*=\s*"([^"]+)"', content)
            if m:
                info["name"] = m.group(1)
            m = re.search(r'version\s*=\s*"([^"]+)"', content)
            if m:
                info["version"] = m.group(1)
            m = re.search(r'description\s*=\s*"([^"]+)"', content)
            if m:
                info["description"] = m.group(1)
        except Exception:
            pass
        info["test_command"] = find_command(root, ["pytest", "unittest", "nose"])
        info["lint_command"] = find_command(root, ["ruff", "flake8", "pylint", "black --check"])
        info["build_command"] = None
        if (root / "frontend").is_dir():
            info["has_frontend"] = True

    # Node.js project
    elif (root / "package.json").exists():
        info["type"] = "node"
        try:
            pkg = json.loads((root / "package.json").read_text())
            info["name"] = pkg.get("name")
            info["version"] = pkg.get("version")
            info["description"] = pkg.get("description")
            scripts = pkg.get("scripts", {})
            if "test" in scripts:
                info["test_command"] = "npm test"
            if "build" in scripts:
                info["build_command"] = "npm run build"
            if "lint" in scripts:
                info["lint_command"] = "npm run lint"
        except Exception:
            pass

    # Go project
    elif (root / "go.mod").exists():
        info["type"] = "go"
        try:
            with open(root / "go.mod") as f:
                first = f.readline()
                m = re.match(r"module\s+(\S+)", first)
                if m:
                    info["name"] = m.group(1)
        except Exception:
            pass
        info["test_command"] = "go test ./..."
        info["build_command"] = "go build ./..."

    # Rust project
    elif (root / "Cargo.toml").exists():
        info["type"] = "rust"
        try:
            with open(root / "Cargo.toml") as f:
                content = f.read()
            m = re.search(r'name\s*=\s*"([^"]+)"', content)
            if m:
                info["name"] = m.group(1)
            m = re.search(r'version\s*=\s*"([^"]+)"', content)
            if m:
                info["version"] = m.group(1)
        except Exception:
            pass
        info["test_command"] = "cargo test"
        info["build_command"] = "cargo build"

    # Docker
    if (root / "Dockerfile").exists():
        info["has_docker"] = True

    return info


def find_command(root: Path, candidates: list[str]) -> str | None:
    """Return the first available test/lint command."""
    # Check if the tool is configured in pyproject.toml or available in venv
    for cmd in candidates:
        if cmd == "pytest":
            venv_pytest = root / ".venv" / "bin" / "pytest"
            if venv_pytest.exists():
                return f"{venv_pytest} -q"
            # Check if pytest is configured
            if (root / "pyproject.toml").exists():
                with open(root / "pyproject.toml") as f:
                    if "pytest" in f.read():
                        return ".venv/bin/python -m pytest -q"
        if cmd == "ruff":
            venv_ruff = root / ".venv" / "bin" / "ruff"
            if venv_ruff.exists():
                return f"{venv_ruff} check ."
            if (root / "pyproject.toml").exists():
                with open(root / "pyproject.toml") as f:
                    if "ruff" in f.read():
                        return ".venv/bin/python -m ruff check ."
    return None


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------


def run_command(cmd: str, root: Path, timeout: int = 30) -> tuple[int, str]:
    """Run a shell command and return (returncode, stdout)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=root, timeout=timeout
        )
        return result.returncode, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return -1, "(timeout)"
    except FileNotFoundError:
        return -1, "(not found)"


def collect_test_count(info: Project) -> int:
    """Run tests and extract pass count."""
    cmd = info.get("test_command")
    if not cmd:
        return 0
    debug(f"Running: {cmd}")
    rc, output = run_command(cmd, info["root"])
    if rc != 0:
        warn(f"Tests failed (rc={rc}) — counting partial results")

    # Parse common test output formats
    patterns = [
        r"(\d+)\s+passed",           # pytest, jest
        r"ok\s+(\d+)\s+test",        # Go
        r"test result:\s+ok\.\s+(\d+)\s+passed",  # Cargo
    ]
    for pattern in patterns:
        m = re.search(pattern, output)
        if m:
            count = int(m.group(1))
            ok(f"Tests: {count} passed")
            return count
    return 0


def collect_routes(info: Project) -> list[str]:
    """Scan for API route definitions."""
    routes = []
    root = info["root"]

    # FastAPI/Flask routes
    for pattern in ["app/api/*.py", "app/routers/*.py", "app/*.py", "routes/*.py"]:
        for path in root.glob(pattern):
            content = path.read_text()
            for m in re.finditer(r'@(router|app)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)', content):
                routes.append(f"{m.group(2).upper()} {m.group(3)}")

    # Express/Fastify routes
    for pattern in ["routes/**/*.ts", "routes/**/*.js", "pages/api/**/*.ts", "pages/api/**/*.js"]:
        for path in root.glob(pattern):
            content = path.read_text()
            for m in re.finditer(r'\.(get|post|put|delete|all)\s*\([\s"\']([^"\']+)', content):
                routes.append(f"{m.group(1).upper()} {m.group(2)}")

    # Next.js App Router
    for path in root.glob("app/api/**/route.ts"):
        parts = path.relative_to(root).parts
        route_path = "/" + "/".join(p for p in parts if p not in ("app", "route.ts"))
        routes.append(f"GET {route_path}")

    # Go Chi/Gin routes
    for pattern in ["**/*.go"]:
        for path in root.glob(pattern):
            content = path.read_text()
            for m in re.finditer(r'\.(Get|Post|Put|Delete|Handle)\s*\(\s*["\']([^"\']+)', content):
                routes.append(f"{m.group(1).upper()} {m.group(2)}")

    if routes:
        ok(f"Routes: {len(routes)} found")
    return sorted(set(routes))


def collect_modules(info: Project) -> list[str]:
    """Scan for source modules/directories."""
    modules = []
    root = info["root"]
    for src_dir in ["app", "src", "lib", "cmd", "internal", "pkg"]:
        d = root / src_dir
        if d.is_dir():
            for item in sorted(d.iterdir()):
                if item.is_dir() and not item.name.startswith(("__", ".")):
                    modules.append(item.name)
    return modules


def check_frontend(info: Project) -> list[str]:
    """Check frontend build and list components."""
    components = []
    if not info["has_frontend"]:
        return components

    frontend_root = info["root"] / "frontend"
    if not frontend_root.is_dir():
        frontend_root = info["root"]

    # React/Vue/Svelte components
    for pattern in ["src/components/**/*.tsx", "src/components/**/*.jsx", "src/components/**/*.vue", "src/components/**/*.svelte"]:
        for path in frontend_root.glob(pattern):
            name = path.stem
            if name not in ("index",) and not name.startswith("_"):
                components.append(name)

    # TypeScript check
    ts_config = frontend_root / "tsconfig.json"
    if ts_config.exists():
        rc, _ = run_command("npx tsc --noEmit 2>&1", frontend_root, timeout=60)
        if rc == 0:
            ok("Frontend TypeScript: clean")
        else:
            warn("Frontend TypeScript: errors found")

    # Build check
    build_cmd = info.get("build_command")
    if build_cmd:
        rc, output = run_command(build_cmd, root, timeout=120)
        if rc == 0:
            ok(f"Frontend build: clean")
        else:
            warn(f"Frontend build: failed")

    if components:
        ok(f"Frontend components: {len(components)} found")
    return sorted(components)


def check_lint(info: Project) -> bool | None:
    """Run linter and return whether it passes."""
    cmd = info.get("lint_command")
    if not cmd:
        return None
    rc, _ = run_command(cmd, info["root"])
    if rc == 0:
        ok("Lint: clean")
        return True
    else:
        warn("Lint: issues found")
        return False


def git_last_commit(root: Path) -> str:
    """Get the last commit message."""
    rc, output = run_command("git log -1 --oneline", root)
    if rc == 0:
        return output
    return ""


# ---------------------------------------------------------------------------
# README generation/update
# --------------------------------------------------------------------------


def generate_readme(info: Project) -> str:
    """Generate a complete README.md from collected project data."""
    name = info["name"] or "My Project"
    description = info["description"] or ""
    test_count = info["test_count"]
    routes = info["routes"]
    modules = info["modules"]
    components = info["frontend_components"]
    last_commit = git_last_commit(info["root"])

    lines = []
    lines.append(f"# {name}\n")
    if description:
        lines.append(f"{description}\n")

    # Badges
    badges = []
    if test_count:
        badges.append(f"![Tests](https://img.shields.io/badge/tests-{test_count}%20passing-brightgreen)")
    if info["type"]:
        badges.append(f"![Language](https://img.shields.io/badge/language-{info['type']}-blue)")
    if info["has_docker"]:
        badges.append("![Docker](https://img.shields.io/badge/docker-ready-blue)")
    if info["version"]:
        badges.append(f"![Version](https://img.shields.io/badge/version-{info['version']}-orange)")
    if badges:
        lines.append(" ".join(badges) + "\n")

    # Quick start
    lines.append("## Quick Start\n")
    if info["type"] == "node":
        lines.append("```bash\nnpm install\nnpm run dev\n```\n")
    elif info["type"] == "python":
        lines.append("```bash\npython -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt\nuvicorn app.main:app --reload\n```\n")
    elif info["type"] == "go":
        lines.append("```bash\ngo build ./...\n./myapp\n```\n")
    elif info["type"] == "rust":
        lines.append("```bash\ncargo build --release\n./target/release/myapp\n```\n")

    # Routes / API
    if routes:
        lines.append("## API\n")
        lines.append("| Method | Path |\n|--------|------|\n")
        for route in routes[:30]:
            parts = route.split(" ", 1)
            if len(parts) == 2:
                lines.append(f"| {parts[0]} | `{parts[1]}` |\n")
        if len(routes) > 30:
            lines.append(f"| ... | {len(routes) - 30} more routes |\n")
        lines.append("")

    # Modules
    if modules:
        lines.append("## Modules\n\n")
        for m in modules:
            lines.append(f"- `{m}`\n")
        lines.append("")

    # Frontend
    if components:
        lines.append("## Frontend Components\n\n")
        for c in components:
            lines.append(f"- `{c}`\n")
        lines.append("")

    # Test suite
    lines.append("## Test Suite\n\n")
    if test_count:
        lines.append(f"**{test_count} tests passing**")
    else:
        lines.append("Test suite status: pending configuration.")
    if last_commit:
        lines.append(f"\n\n_Latest: {last_commit}_")
    lines.append("\n")

    return "".join(lines)


def update_readme(info: Project) -> bool:
    """Update README.md with generated content. Returns True if changed."""
    root = info["root"]
    readme_path = root / "README.md"

    new_content = generate_readme(info)

    if readme_path.exists():
        old_content = readme_path.read_text()
        if old_content == new_content:
            ok("README.md: already up to date")
            return False

    # Show diff
    if readme_path.exists() and "--apply" not in sys.argv and "--pre-push" not in sys.argv:
        old_lines = readme_path.read_text().splitlines()
        new_lines = new_content.splitlines()
        print(f"\n  📝 README.md changes:", file=sys.stderr)
        print(f"     {len(old_lines)} lines → {len(new_lines)} lines", file=sys.stderr)
        try:
            response = input("  Apply changes? [Y/n] ").strip().lower()
            if response not in ("", "y", "yes"):
                warn("Skipped README update")
                return False
        except (EOFError, KeyboardInterrupt):
            warn("Skipped README update")
            return False

    readme_path.write_text(new_content)
    ok("README.md: updated")
    return True


# ---------------------------------------------------------------------------
# Git hook installer
# ---------------------------------------------------------------------------


def install_hook(root: Path) -> None:
    """Install a pre-push git hook that runs readme-sync."""
    hooks_dir = root / ".git" / "hooks"
    if not hooks_dir.is_dir():
        fail(f"Not a git repository: {root}")
        return

    hook_path = hooks_dir / "pre-push"
    hook_content = textwrap.dedent(f"""\
    #!/bin/sh
    # readme-sync pre-push hook — auto-update README.md before push
    # Generated by readme-sync install-hook
    # Remove this file to disable.

    echo "  📝 readme-sync: checking README.md..."
    python3 -m readme_sync --pre-push 2>/dev/null || true
    """)

    hook_path.write_text(hook_content)
    hook_path.chmod(0o755)
    ok(f"Pre-push hook installed at {hook_path}")

    # Add to .gitignore
    gitignore = root / ".gitignore"
    marker = "# readme-sync generated files"
    if gitignore.exists():
        content = gitignore.read_text()
        if marker not in content:
            gitignore.write_text(content + f"\n{marker}\nREADME.md.bak\n")
    ok("Git hook: ready (runs silently before every `git push`)")


# ---------------------------------------------------------------------------
# CI check mode
# ---------------------------------------------------------------------------


def ci_check(info: Project) -> bool:
    """Verify README is up to date. Returns False if stale."""
    old_readme = (info["root"] / "README.md")
    if not old_readme.exists():
        fail("README.md: missing")
        return False

    old_content = old_readme.read_text()
    new_content = generate_readme(info)

    # Check key data points in the README
    issues = []

    test_count = info["test_count"]
    if test_count:
        pattern = rf"(\d+)\s+test"
        m = re.search(pattern, old_content)
        if m and int(m.group(1)) != test_count:
            issues.append(f"Test count: README says {m.group(1)}, actual is {test_count}")

    routes = info["routes"]
    if routes:
        for route in routes[:5]:
            path_part = route.split(" ", 1)[-1].strip("`")
            if path_part not in old_content:
                issues.append(f"Route missing from docs: {route}")
                break

    if issues:
        print("  README is stale:", file=sys.stderr)
        for issue in issues:
            print(f"    - {issue}", file=sys.stderr)
        fail("CI check: README is out of date")
        return False

    ok("CI check: README is current")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    root = Path.cwd()
    args = set(sys.argv[1:])

    if "--install-hook" in args:
        install_hook(root)
        return

    info = detect_project(root)

    if not info["type"]:
        warn(f"Unknown project type at {root}")
        warn("Supported: Python (pyproject.toml), Node (package.json), Go (go.mod), Rust (Cargo.toml)")
        sys.exit(1)

    debug(f"Project: {info['name'] or 'unknown'} ({info['type']})")

    # Collect data
    info["modules"] = collect_modules(info)
    info["routes"] = collect_routes(info)
    info["frontend_components"] = check_frontend(info)
    info["test_count"] = collect_test_count(info)
    info["lint_passes"] = check_lint(info)

    if "--check" in args:
        passed = ci_check(info)
        sys.exit(0 if passed else 1)

    updated = update_readme(info)

    if "--pre-push" in args:
        if updated:
            # Stage and amend the commit with README update
            subprocess.run(
                "git add README.md && git commit --amend --no-edit --no-verify",
                shell=True, capture_output=True, cwd=root
            )


if __name__ == "__main__":
    main()
