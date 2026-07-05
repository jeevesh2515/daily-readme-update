#!/usr/bin/env python3
"""
readme-sync — Auto-sync README.md with your actual codebase.

Detects project type, runs tests, scans routes/modules, checks frontend build,
and rewrites README.md with verified data using **marker-based injection**.
Designed for pre-push hooks, CI, and AI-agent workflows.

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


MARKER_START = "<!-- readme-sync: {section} -->"
MARKER_END = "<!-- /readme-sync -->"


def debug(msg: str) -> None:
    if "--pre-push" in sys.argv:
        return
    print(f"  \U0001f4a1 {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    if "--pre-push" in sys.argv:
        return
    print(f"  \u26a0\ufe0f {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    if "--pre-push" in sys.argv:
        return
    print(f"  \u2713 {msg}", file=sys.stderr)


def fail(msg: str) -> None:
    if "--pre-push" in sys.argv:
        return
    print(f"  \u2717 {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Project detection
# ---------------------------------------------------------------------------

Project = dict[str, Any]


def detect_project(root: Path) -> Project:
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
        "test_output": "",
        "lint_passes": None,
    }

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
        info["test_command"] = find_command(
            root, ["pytest", "unittest", "nose"]
        )
        info["lint_command"] = find_command(
            root, ["ruff", "flake8", "pylint", "black --check"]
        )
        info["build_command"] = None
        if (root / "frontend").is_dir():
            info["has_frontend"] = True

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

    if (root / "Dockerfile").exists():
        info["has_docker"] = True

    return info


def find_command(root: Path, candidates: list[str]) -> str | None:
    for cmd in candidates:
        if cmd == "pytest":
            venv_pytest = root / ".venv" / "bin" / "pytest"
            if venv_pytest.exists():
                return f"{venv_pytest} -q"
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
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=root,
            timeout=timeout,
        )
        return result.returncode, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return -1, "(timeout)"
    except FileNotFoundError:
        return -1, "(not found)"


def collect_test_count(info: Project) -> int:
    cmd = info.get("test_command")
    if not cmd:
        return 0
    debug(f"Running: {cmd}")
    rc, output = run_command(cmd, info["root"])
    info["test_output"] = output
    if rc != 0:
        warn(f"Tests failed (rc={rc}) — counting partial results")

    patterns = [
        r"(\d+)\s+passed",
        r"ok\s+(\d+)\s+test",
        r"test result:\s+ok\.\s+(\d+)\s+passed",
    ]
    for pattern in patterns:
        m = re.search(pattern, output)
        if m:
            count = int(m.group(1))
            ok(f"Tests: {count} passed")
            return count
    return 0


def collect_routes(info: Project) -> list[str]:
    routes = []
    root = info["root"]

    for pattern in [
        "app/api/*.py",
        "app/routers/*.py",
        "app/*.py",
        "routes/*.py",
    ]:
        for path in root.glob(pattern):
            content = path.read_text()
            for m in re.finditer(
                r'@(router|app)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)',
                content,
            ):
                routes.append(f"{m.group(2).upper()} {m.group(3)}")

    for pattern in [
        "routes/**/*.ts",
        "routes/**/*.js",
        "pages/api/**/*.ts",
        "pages/api/**/*.js",
    ]:
        for path in root.glob(pattern):
            content = path.read_text()
            for m in re.finditer(
                r'\.(get|post|put|delete|all)\s*\([\s"\']([^"\']+)', content
            ):
                routes.append(f"{m.group(1).upper()} {m.group(2)}")

    for path in root.glob("app/api/**/route.ts"):
        parts = path.relative_to(root).parts
        route_path = (
            "/"
            + "/".join(p for p in parts if p not in ("app", "route.ts"))
        )
        routes.append(f"GET {route_path}")

    for pattern in ["**/*.go"]:
        for path in root.glob(pattern):
            content = path.read_text()
            for m in re.finditer(
                r'\.(Get|Post|Put|Delete|Handle)\s*\(\s*["\']([^"\']+)', content
            ):
                routes.append(f"{m.group(1).upper()} {m.group(2)}")

    if routes:
        ok(f"Routes: {len(routes)} found")
    return sorted(set(routes))


def collect_modules(info: Project) -> list[str]:
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
    components = []
    if not info["has_frontend"]:
        return components

    frontend_root = info["root"] / "frontend"
    if not frontend_root.is_dir():
        frontend_root = info["root"]

    for pattern in [
        "src/components/**/*.tsx",
        "src/components/**/*.jsx",
        "src/components/**/*.vue",
        "src/components/**/*.svelte",
    ]:
        for path in frontend_root.glob(pattern):
            name = path.stem
            if name not in ("index",) and not name.startswith("_"):
                components.append(name)

    ts_config = frontend_root / "tsconfig.json"
    if ts_config.exists():
        rc, _ = run_command(
            "npx tsc --noEmit 2>&1", frontend_root, timeout=60
        )
        if rc == 0:
            ok("Frontend TypeScript: clean")
        else:
            warn("Frontend TypeScript: errors found")

    build_cmd = info.get("build_command")
    if build_cmd:
        rc, output = run_command(build_cmd, root, timeout=120)
        if rc == 0:
            ok("Frontend build: clean")
        else:
            warn("Frontend build: failed")

    if components:
        ok(f"Frontend components: {len(components)} found")
    return sorted(components)


def check_lint(info: Project) -> bool | None:
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
    rc, output = run_command("git log -1 --oneline", root)
    if rc == 0:
        return output
    return ""


# ---------------------------------------------------------------------------
# Marker-based README injection
# ---------------------------------------------------------------------------


def _stats_block(info: Project) -> str:
    """Generate the stats table for the <!-- readme-sync: stats --> marker."""
    test_str = (
        f"{info['test_count']} passing"
        if info["test_count"]
        else "pending configuration"
    )
    commit = git_last_commit(info["root"])
    commit_str = f"`{commit}`" if commit else "—"
    type_str = info["type"] or "unknown"
    name_str = info["name"] or "—"
    version_str = info["version"] or "—"
    docker_str = "yes" if info.get("has_docker") else "no"
    lint_str = "clean" if info.get("lint_passes") else "issues" if info.get("lint_passes") is False else "—"

    lines = [
        "| Metric | Value |",
        "|--------|-------|",
        f"| Language | {type_str} |",
        f"| Version | {version_str} |",
        f"| Tests | {test_str} |",
        f"| Lint | {lint_str} |",
        f"| Docker | {docker_str} |",
        f"| Latest commit | {commit_str} |",
    ]
    return "\n".join(lines)


def _routes_block(info: Project) -> str:
    routes = info.get("routes", [])
    if not routes:
        return "No API routes detected."

    lines = ["| Method | Path |", "|--------|------|"]
    for route in routes[:30]:
        parts = route.split(" ", 1)
        if len(parts) == 2:
            lines.append(f"| {parts[0]} | `{parts[1]}` |")
    if len(routes) > 30:
        lines.append(f"| ... | {len(routes) - 30} more routes |")
    return "\n".join(lines)


def _modules_block(info: Project) -> str:
    modules = info.get("modules", [])
    if not modules:
        return "No source modules detected."
    return "\n".join(f"- `{m}`" for m in modules)


def _components_block(info: Project) -> str:
    components = info.get("frontend_components", [])
    if not components:
        return "No frontend components detected."
    return "\n".join(f"- `{c}`" for c in components)


SECTION_RENDERERS = {
    "stats": _stats_block,
    "routes": _routes_block,
    "modules": _modules_block,
    "components": _components_block,
}


def inject_readme(info: Project) -> str | None:
    """
    Replace marker sections in the existing README.
    Returns the new content, or None if no markers found.
    """
    root = info["root"]
    readme_path = root / "README.md"
    if not readme_path.exists():
        return None

    content = readme_path.read_text()
    original = content
    any_replaced = False

    for section, renderer in SECTION_RENDERERS.items():
        start_marker = MARKER_START.format(section=section)
        end_marker = MARKER_END
        pattern = re.compile(
            re.escape(start_marker) + r".*?" + re.escape(end_marker),
            re.DOTALL,
        )
        replacement = start_marker + "\n" + renderer(info) + "\n" + end_marker
        if pattern.search(content):
            content = pattern.sub(replacement, content)
            any_replaced = True

    if not any_replaced:
        return None

    return content


def update_readme(info: Project) -> bool:
    """Update README.md via marker injection. Returns True if changed."""
    root = info["root"]
    readme_path = root / "README.md"

    new_content = inject_readme(info)

    if new_content is None:
        # No markers found — offer to append a stats section
        warn("No <!-- readme-sync --> markers found in README.md")
        warn("Run with --apply to append a stats section at the end")
        return False

    if new_content == readme_path.read_text():
        ok("README.md: already up to date")
        return False

    # Show diff
    if "--apply" not in sys.argv and "--pre-push" not in sys.argv:
        old_lines = readme_path.read_text().splitlines()
        new_lines = new_content.splitlines()
        print(f"\n  \U0001f4dd README.md changes:", file=sys.stderr)
        print(f"     {len(old_lines)} lines \u2192 {len(new_lines)} lines", file=sys.stderr)
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
# Append mode (when no markers exist)
# ---------------------------------------------------------------------------


def append_stats(info: Project) -> bool:
    """Append a stats section to README.md when no markers exist."""
    root = info["root"]
    readme_path = root / "README.md"

    section = _stats_block(info)
    routes = _routes_block(info)
    modules = _modules_block(info)
    components = _components_block(info)

    new_content = (
        "\n\n---\n\n"
        "<!-- readme-sync: stats -->\n"
        f"{section}\n"
        "<!-- /readme-sync -->\n"
    )
    if "No API routes" not in routes:
        new_content += (
            "\n### API Routes\n"
            "<!-- readme-sync: routes -->\n"
            f"{routes}\n"
            "<!-- /readme-sync -->\n"
        )
    if "No source modules" not in modules:
        new_content += (
            "\n### Modules\n"
            "<!-- readme-sync: modules -->\n"
            f"{modules}\n"
            "<!-- /readme-sync -->\n"
        )
    if "No frontend components" not in components:
        new_content += (
            "\n### Frontend Components\n"
            "<!-- readme-sync: components -->\n"
            f"{components}\n"
            "<!-- /readme-sync -->\n"
        )

    new_content += (
        "\n<!-- readme-sync auto-generated section. "
        "Edit markers above; content between markers is replaced on each run. -->\n"
    )

    if readme_path.exists():
        old = readme_path.read_text()
        if new_content in old:
            ok("README.md: already up to date")
            return False

        if "--apply" not in sys.argv and "--pre-push" not in sys.argv:
            print(f"\n  \U0001f4dd Append stats section to README.md?", file=sys.stderr)
            try:
                response = input("  Apply changes? [Y/n] ").strip().lower()
                if response not in ("", "y", "yes"):
                    warn("Skipped README update")
                    return False
            except (EOFError, KeyboardInterrupt):
                warn("Skipped README update")
                return False

        readme_path.write_text(old.rstrip() + "\n" + new_content.lstrip())
        ok("README.md: stats section appended")
        return True

    readme_path.write_text(
        f"# {info['name'] or 'My Project'}\n\n{new_content.lstrip()}"
    )
    ok("README.md: created")
    return True


# ---------------------------------------------------------------------------
# CI check mode
# ---------------------------------------------------------------------------


def ci_check(info: Project) -> bool:
    """Verify README markers contain current data. Returns False if stale."""
    readme_path = info["root"] / "README.md"
    if not readme_path.exists():
        fail("README.md: missing")
        return False

    content = readme_path.read_text()
    issues = []

    # Check each marker section
    for section, renderer in SECTION_RENDERERS.items():
        start_marker = MARKER_START.format(section=section)
        end_marker = MARKER_END
        pattern = re.compile(
            re.escape(start_marker) + r"(.*?)" + re.escape(end_marker),
            re.DOTALL,
        )
        m = pattern.search(content)
        if m:
            expected = renderer(info)
            actual = m.group(1).strip()
            if expected.strip() != actual.strip():
                issues.append(
                    f"Section `{section}` is stale"
                )

    # Check inline test count if present
    test_count = info["test_count"]
    if test_count:
        tc_pattern = r"<!--\s*readme-sync:\s*test-count\s*-->(\d+)<!--\s*/readme-sync\s*-->"
        m = re.search(tc_pattern, content)
        if m:
            stated = int(m.group(1))
            if stated != test_count:
                issues.append(
                    f"Test count: README says {stated}, actual is {test_count}"
                )

    if issues:
        fail("CI check: README is out of date")
        for issue in issues:
            warn(issue)
        return False

    ok("CI check: README is current")
    return True


# ---------------------------------------------------------------------------
# Git hook installer
# ---------------------------------------------------------------------------


def install_hook(root: Path) -> None:
    hooks_dir = root / ".git" / "hooks"
    if not hooks_dir.is_dir():
        fail(f"Not a git repository: {root}")
        return

    hook_path = hooks_dir / "pre-push"
    hook_content = textwrap.dedent("""\
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

    gitignore = root / ".gitignore"
    marker = "# readme-sync generated files"
    if gitignore.exists():
        content = gitignore.read_text()
        if marker not in content:
            gitignore.write_text(content + f"\n{marker}\nREADME.md.bak\n")
    ok("Git hook: ready (runs silently before every `git push`)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    root = Path.cwd()
    args = set(sys.argv[1:])

    if "--version" in args:
        print("readme-sync 1.1.0")
        return

    if "--install-hook" in args:
        install_hook(root)
        return

    info = detect_project(root)

    if not info["type"]:
        warn(f"Unknown project type at {root}")
        warn(
            "Supported: Python (pyproject.toml), Node (package.json), Go (go.mod), Rust (Cargo.toml)"
        )
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

    # Try marker injection first
    updated = update_readme(info)

    # If no markers, offer to append
    if not updated:
        if "--apply" in args or "--pre-push" in args:
            updated = append_stats(info)
        else:
            # Interactive: ask user
            print(
                "\n  No <!-- readme-sync --> markers found in README.md.",
                file=sys.stderr,
            )
            print(
                "  Would you like to append a stats section? [Y/n] ",
                file=sys.stderr,
            )
            try:
                response = input().strip().lower()
                if response in ("", "y", "yes"):
                    updated = append_stats(info)
                else:
                    warn("Skipped README update")
            except (EOFError, KeyboardInterrupt):
                warn("Skipped README update")

    if "--pre-push" in args and updated:
        subprocess.run(
            "git add README.md && git commit --amend --no-edit --no-verify",
            shell=True,
            capture_output=True,
            cwd=root,
        )


if __name__ == "__main__":
    main()
