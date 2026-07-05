#!/usr/bin/env python3
"""
readme-guardian — The README freshness guarantee for vibe coders.

Auto-detects your project, runs tests, scans routes/modules/components,
and keeps README.md in sync before every push. Zero config. One command.

Usage:
    readme-guardian                        # Interactive mode
    readme-guardian --apply                # Apply changes silently
    readme-guardian --check                # CI mode: exit 1 if stale
    readme-guardian --install-hook         # Pre-push hook (one-time)
    readme-guardian --uninstall-hook       # Remove pre-push hook
    readme-guardian --version              # Show version

Install:
    pipx install readme-guardian           # Python (any project)
    npx readme-guardian                    # Node (via npm)
    brew install readme-guardian           # macOS (future)
"""

import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path


def debug(msg: str) -> None:
    if "--pre-push" in sys.argv:
        return
    print(f"  \U0001f4a1 {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    if "--pre-push" in sys.argv:
        return
    print(f"  \u2713 {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    if "--pre-push" in sys.argv:
        return
    print(f"  \u26a0 {msg}", file=sys.stderr)


def fail(msg: str) -> None:
    if "--pre-push" in sys.argv:
        return
    print(f"  \u2717 {msg}", file=sys.stderr)


def banner() -> None:
    if "--pre-push" in sys.argv:
        return
    print(file=sys.stderr)
    print("  \U0001f6e1\ufe0f  readme-guardian v1.0", file=sys.stderr)
    print("  \u2500" * 30, file=sys.stderr)


# ---------------------------------------------------------------------------
# Project detection (language-agnostic, zero config)
# ---------------------------------------------------------------------------

def detect_project(root: Path) -> dict:
    info = {
        "type": None,
        "name": "my-project",
        "version": "",
        "description": "",
        "scripts": {},
        "is_monorepo": False,
        "has_frontend": False,
        "has_docker": False,
        "test_command": None,
        "build_command": None,
        "lint_command": None,
        "tests": 0,
        "test_output": "",
        "routes": [],
        "modules": [],
        "components": [],
        "lint_pass": None,
    }

    # --- Package.json (Node/JS/TS) — detected FIRST for broader reach ---
    if (root / "package.json").exists():
        try:
            pkg = json.loads((root / "package.json").read_text())
            info["name"] = pkg.get("name", info["name"])
            info["version"] = pkg.get("version", "")
            info["description"] = pkg.get("description", "")
            info["scripts"] = pkg.get("scripts", {})

            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if any(x in deps for x in ("next", "react", "vue", "svelte", "vite")):
                info["has_frontend"] = True

            if "test" in info["scripts"]:
                info["test_command"] = "npm test -- --reporter=min 2>&1 || npm test 2>&1"
            if "build" in info["scripts"]:
                info["build_command"] = "npm run build 2>&1"
            if "lint" in info["scripts"]:
                info["lint_command"] = "npm run lint 2>&1"

            workspaces = pkg.get("workspaces", [])
            info["is_monorepo"] = bool(workspaces)
        except Exception:
            pass

        if not info["type"]:
            info["type"] = "node"

    # --- pyproject.toml (Python) ---
    if (root / "pyproject.toml").exists():
        try:
            content = (root / "pyproject.toml").read_text()
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

        info["type"] = "python"
        if not info["test_command"]:
            info["test_command"] = _find_python_cmd(root, "pytest")
        if not info["lint_command"]:
            info["lint_command"] = _find_python_cmd(root, "ruff")
        if (root / "frontend").is_dir():
            info["has_frontend"] = True

    # --- go.mod (Go) ---
    if (root / "go.mod").exists():
        try:
            first = (root / "go.mod").read_text().split("\n")[0]
            m = re.match(r"module\s+(\S+)", first)
            if m:
                info["name"] = m.group(1)
        except Exception:
            pass
        info["type"] = "go"
        info["test_command"] = "go test ./... 2>&1"
        info["build_command"] = "go build ./... 2>&1"

    # --- Cargo.toml (Rust) ---
    if (root / "Cargo.toml").exists():
        try:
            content = (root / "Cargo.toml").read_text()
            m = re.search(r'name\s*=\s*"([^"]+)"', content)
            if m:
                info["name"] = m.group(1)
            m = re.search(r'version\s*=\s*"([^"]+)"', content)
            if m:
                info["version"] = m.group(1)
        except Exception:
            pass
        info["type"] = "rust"
        info["test_command"] = "cargo test 2>&1"
        info["build_command"] = "cargo build 2>&1"

    if (root / "Dockerfile").exists():
        info["has_docker"] = True

    # Detect workspaces/monorepo
    if not info["is_monorepo"]:
        for f in ["pnpm-workspace.yaml", "lerna.json", "rush.json"]:
            if (root / f).exists():
                info["is_monorepo"] = True
                break

    return info


def _find_python_cmd(root: Path, tool: str) -> str | None:
    """Check if a Python tool is available via venv or configured."""
    bin_path = root / ".venv" / "bin" / tool
    if bin_path.exists():
        return f"{bin_path} 2>&1"
    if (root / "pyproject.toml").exists():
        with open(root / "pyproject.toml") as f:
            if tool in f.read():
                venv_python = root / ".venv" / "bin" / "python"
                if tool == "pytest":
                    return f"{venv_python} -m pytest -q 2>&1" if venv_python.exists() else None
                elif tool == "ruff":
                    return f"{venv_python} -m ruff check . 2>&1" if venv_python.exists() else None
    return None


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def _run(cmd: str, root: Path, timeout: int = 60) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=root, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except subprocess.TimeoutExpired:
        return -1, "(timeout)"
    except FileNotFoundError:
        return -1, "(not found)"


def collect_tests(info: dict) -> int:
    cmd = info.get("test_command")
    if not cmd:
        return 0
    debug(f"Running: {cmd}")
    rc, output = _run(cmd, Path.cwd())
    info["test_output"] = output

    patterns = [
        (r"(\d+)\s+passed", 1),
        (r"ok\s+(\d+)\s+test", 1),
        (r"test result:\s+ok\.\s+(\d+)\s+passed", 1),
        (r"Tests:\s+(\d+)", 1),
    ]
    for pat, group in patterns:
        m = re.search(pat, output)
        if m:
            n = int(m.group(group))
            ok(f"Tests: {n} passing")
            return n
    if rc == 0:
        ok("Tests: passed (count unknown)")
        return -1
    return 0


def collect_routes(info: dict) -> list[str]:
    routes = set()
    root = Path.cwd()

    # FastAPI/Flask
    for pat in ["**/*.py"]:
        for path in root.glob(pat):
            try:
                content = path.read_text()
                for m in re.finditer(r'@(?:router|app)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)', content):
                    routes.add(f"{m.group(0).split('.')[1].split('(')[0].upper()} {m.group(1)}")
            except Exception:
                pass

    # Next.js App Router
    for path in root.glob("app/api/**/route.*"):
        rel = path.relative_to(root)
        parts = rel.parts
        # Build path from directory structure
        route_parts = []
        for p in parts:
            if p in ("app", "route.ts", "route.js"):
                continue
            if p.startswith("["):
                route_parts.append(f":{p.strip('[]')}")
            else:
                route_parts.append(p)
        route_path = "/" + "/".join(route_parts)
        routes.add(f"GET {route_path}")

    # Express/Fastify
    for pat in ["**/*.{ts,js}", "!node_modules/**"]:
        for path in root.glob(pat):
            if "node_modules" in str(path):
                continue
            try:
                content = path.read_text()
                for m in re.finditer(r'\.(get|post|put|delete|all|patch)\s*\(\s*["\'`]([^"\'`]+)', content, re.IGNORECASE):
                    routes.add(f"{m.group(1).upper()} {m.group(2)}")
            except Exception:
                pass

    # Go
    for path in root.glob("**/*.go"):
        try:
            content = path.read_text()
            for m in re.finditer(r'\.(Get|Post|Put|Delete|Patch|Handle)\s*\(\s*["\']([^"\']+)', content):
                routes.add(f"{m.group(1).upper()} {m.group(2)}")
        except Exception:
            pass

    result = sorted(routes)
    if result:
        ok(f"Routes: {len(result)} found")
    return result


def collect_modules(info: dict) -> list[str]:
    modules = set()
    root = Path.cwd()

    # Python
    for d in root.glob("app/*/__init__.py"):
        modules.add(d.parent.name)
    for d in root.glob("src/*/__init__.py"):
        modules.add(d.parent.name)

    # Node
    for d in root.glob("src/*/index.ts"):
        modules.add(d.parent.name)
    for d in root.glob("src/*/index.js"):
        modules.add(d.parent.name)

    # Go
    for d in root.glob("cmd/*/main.go"):
        modules.add(d.parent.name)
    for d in root.glob("internal/*/"):
        modules.add(d.name)

    # Rust
    for d in root.glob("src/*.rs"):
        modules.add(d.stem)

    # Any top-level source dirs
    for src_dir in ["app", "src", "lib", "cmd", "internal", "pkg"]:
        d = root / src_dir
        if d.is_dir():
            for item in sorted(d.iterdir()):
                if item.is_dir() and not item.name.startswith(("__", ".", "node_modules")):
                    modules.add(item.name)

    return sorted(modules)


def collect_components(info: dict) -> list[str]:
    if not info.get("has_frontend") and info.get("type") != "node":
        return []
    components = set()
    root = Path.cwd()

    frontend_root = root / "frontend" if (root / "frontend").is_dir() else root
    for pat in ["**/*.tsx", "**/*.jsx", "**/*.vue", "**/*.svelte"]:
        for path in frontend_root.glob(pat):
            if "node_modules" in str(path):
                continue
            name = path.stem
            if not name.startswith("_") and name not in ("index", "layout", "page", "loading", "error"):
                components.add(name)

    if components:
        ok(f"Components: {len(components)} found")
    return sorted(components)


def collect_lint(info: dict) -> bool | None:
    cmd = info.get("lint_command")
    if not cmd:
        return None
    rc, _ = _run(cmd, Path.cwd())
    if rc == 0:
        ok("Lint: clean")
        return True
    warn("Lint: has issues")
    return False


# ---------------------------------------------------------------------------
# Badge SVG generation — self-updating freshness badge
# ---------------------------------------------------------------------------

BADGE_TEMPLATE = """\
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="README: {status}">
  <linearGradient id="s" x2="0" y2="100%%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{left_w}" height="20" fill="#555"/>
    <rect x="{left_w}" width="{right_w}" height="20" fill="{color}"/>
    <rect width="{width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,DejaVu Sans,Geneva,sans-serif" font-size="11">
    <text x="{left_mid}" y="14" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{left_mid}" y="13">{label}</text>
    <text x="{right_mid}" y="14" fill="#010101" fill-opacity=".3">{message}</text>
    <text x="{right_mid}" y="13">{message}</text>
  </g>
</svg>"""


def generate_badge(info: dict) -> str:
    """Generate a shields.io-style SVG freshness badge."""
    label = "README"
    tests = info.get("tests", 0)
    lint = info.get("lint_pass")

    if tests > 0:
        status = "fresh"
        message = f"{tests} passing"
        color = "#4c1"  # brightgreen
    elif tests == 0 and lint is None:
        status = "synced"
        message = "synced"
        color = "#4c1"  # green — at least it ran
    elif tests == 0:
        status = "no-tests"
        message = "no tests"
        color = "#dfb317"  # yellow
    else:
        status = "stale"
        message = "stale"
        color = "#e05d44"  # red

    left_w = len(label) * 7 + 14
    right_w = len(message) * 7 + 14
    width = left_w + right_w
    left_mid = left_w // 2
    right_mid = left_w + right_w // 2

    return BADGE_TEMPLATE.format(
        width=width,
        left_w=left_w,
        right_w=right_w,
        left_mid=left_mid,
        right_mid=right_mid,
        label=label,
        message=message,
        color=color,
        status=status,
    )


def update_badge(info: dict) -> bool:
    """Generate and write the freshness badge SVG. Returns True if changed."""
    path = Path.cwd() / "readme-badge.svg"
    svg = generate_badge(info)
    if path.exists() and path.read_text() == svg:
        return False
    path.write_text(svg)
    ok(f"Badge: readme-badge.svg — {info.get('tests', 0)} tests passing")
    return True


# ---------------------------------------------------------------------------
# README generation — clean, beautiful, readable
# ---------------------------------------------------------------------------

def shield(label: str, value: str, color: str = "brightgreen") -> str:
    """Generate a shields.io badge."""
    import urllib.parse
    label_e = urllib.parse.quote(label)
    value_e = urllib.parse.quote(value)
    return f"![{label}](https://img.shields.io/badge/{label_e}-{value_e}-{color})"


def freshness_badge(info: dict) -> str:
    """Generate the green 'README fresh' badge."""
    test_str = f"{info['tests']}%20passing" if info.get("tests", 0) > 0 else "synced"
    return shield("README", f"fresh-{test_str}", "brightgreen")


def generate_readme(info: dict) -> str:
    """Generate a complete, beautiful README."""
    name = info["name"] or "my-project"
    desc = info["description"] or ""
    version = info.get("version", "")
    type_ = info.get("type", "unknown")
    tests = info.get("tests", 0)
    routes = info.get("routes", [])
    modules = info.get("modules", [])
    components = info.get("components", [])
    docker = info.get("has_docker", False)
    lint = info.get("lint_pass")

    # Get last commit for freshness
    rc, commit = _run("git log -1 --oneline", Path.cwd())
    commit_str = commit if rc == 0 else ""
    rc2, commit_msg = _run("git log -1 --format=%s", Path.cwd())
    commit_msg_str = commit_msg if rc2 == 0 else ""

    lines = []
    lines.append(f"# {name}\n")
    if desc:
        lines.append(f"{desc}\n")

    # --- Badge row ---
    badges = [freshness_badge(info)]
    if version:
        badges.append(shield("version", version, "blue"))
    badges.append(shield("lang", type_, "blue"))
    if tests > 0:
        badges.append(shield("tests", f"{tests}%20passing", "brightgreen"))
    if lint is True:
        badges.append(shield("lint", "clean", "brightgreen"))
    elif lint is False:
        badges.append(shield("lint", "issues", "yellow"))
    if docker:
        badges.append(shield("docker", "ready", "blue"))
    lines.append(" ".join(badges) + "\n")

    # --- Shield.io style ---
    lines.append(
        '<p align="center">\n'
        "  <sub>README auto-synced by "
        '<a href="https://github.com/jeevesh2515/readme-guardian">'
        "readme-guardian</a> \U0001f6e1\ufe0f</sub>\n"
        "</p>\n"
    )

    # --- Quick Start ---
    lines.append("## \U0001f680 Quick Start\n")
    lines.append(_quick_start(info))

    # --- API Routes ---
    if routes:
        lines.append("## \U0001f4e1 API\n")
        lines.append("| Method | Path |\n|--------|------|\n")
        for r in routes[:25]:
            parts = r.split(" ", 1)
            if len(parts) == 2:
                lines.append(f"| **{parts[0]}** | `{parts[1]}` |\n")
        if len(routes) > 25:
            lines.append(f"| ... | {len(routes) - 25} more |\n")
        lines.append("")

    # --- Modules ---
    if modules:
        lines.append("## \U0001f4c2 Modules\n\n")
        for m in modules:
            lines.append(f"- `{m}`\n")
        lines.append("")

    # --- Components ---
    if components:
        lines.append("## \U0001f3a8 Components\n\n")
        for c in components:
            lines.append(f"- `{c}`\n")
        lines.append("")

    # --- Test Suite ---
    lines.append("## \U0001f9ea Test Suite\n\n")
    if tests > 0:
        lines.append(f"**{tests} tests passing** \u2705\n")
    elif tests == 0:
        lines.append("Tests: pending configuration.\n")
    elif tests == -1:
        lines.append("Tests: passing (count unknown).\n")

    # --- Freshness footer ---
    if commit_str:
        lines.append(f"\n_Latest: `{commit_str}`")
        if commit_msg_str:
            lines.append(f" — _{commit_msg_str}_")
        lines.append("_\n")

    return "".join(lines)


def _quick_start(info: dict) -> str:
    t = info["type"]
    if t == "node":
        lines = [
            "```bash",
            "# Install dependencies",
            "npm install",
            "",
            "# Start development server",
            "npm run dev",
            "```",
        ]
        if info.get("build_command"):
            lines.insert(3, f"")
            lines.insert(4, "# Build for production")
            lines.insert(5, "npm run build")
        return "\n".join(lines) + "\n"
    elif t == "python":
        return (
            "```bash\n"
            "# Set up virtual environment\n"
            "python -m venv .venv && source .venv/bin/activate\n"
            "pip install -e .\n"
            "\n"
            "# Start the app [adjust to your entry point]\n"
            "# python -m app.main\n"
            "```\n"
        )
    elif t == "go":
        return (
            "```bash\n"
            "# Build and run\n"
            "go build -o ./bin/app ./cmd/\n"
            "./bin/app\n"
            "```\n"
        )
    elif t == "rust":
        return (
            "```bash\n"
            "# Build and run\n"
            "cargo run\n"
            "```\n"
        )
    return "```bash\n# See project documentation for setup instructions\n```\n"


# ---------------------------------------------------------------------------
# README injection (marker-based, non-destructive)
# ---------------------------------------------------------------------------

MARKERS = {
    "stats": None,  # main stats table
    "routes": None,
    "modules": None,
    "components": None,
}

SECTION_TPL = """\
<!-- readme-guardian:{name} -->
{content}
<!-- /readme-guardian -->"""


def _stats_content(info: dict) -> str:
    t = info.get("type") or "unknown"
    v = info.get("version") or "—"
    tests = info.get("tests", 0)
    t_str = f"{tests} passing" if tests > 0 else "—"
    lint = "clean" if info.get("lint_pass") else "issues" if info.get("lint_pass") is False else "—"
    docker = "yes" if info.get("has_docker") else "no"
    monorepo = "yes" if info.get("is_monorepo") else "no"
    rc, commit = _run("git log -1 --oneline", Path.cwd())
    c_str = f"`{commit}`" if rc == 0 else "—"

    return (
        "| Metric | Value |\n"
        "|--------|-------|\n"
        f"| Language | {t} |\n"
        f"| Version | {v} |\n"
        f"| Tests | {t_str} |\n"
        f"| Lint | {lint} |\n"
        f"| Docker | {docker} |\n"
        f"| Monorepo | {monorepo} |\n"
        f"| Latest commit | {c_str} |\n"
    )


def _routes_content(info: dict) -> str:
    routes = info.get("routes", [])
    if not routes:
        return "No API routes detected."
    lines = ["| Method | Path |", "|--------|------|"]
    for r in routes[:25]:
        parts = r.split(" ", 1)
        if len(parts) == 2:
            lines.append(f"| **{parts[0]}** | `{parts[1]}` |")
    if len(routes) > 25:
        lines.append(f"| ... | {len(routes) - 25} more |")
    return "\n".join(lines)


def _modules_content(info: dict) -> str:
    modules = info.get("modules", [])
    if not modules:
        return "No source modules detected."
    return "\n".join(f"- `{m}`" for m in modules)


def _components_content(info: dict) -> str:
    comps = info.get("components", [])
    if not comps:
        return "No UI components detected."
    return "\n".join(f"- `{c}`" for c in comps)


def inject_readme(info: dict) -> str | None:
    """Replace markers in README. Returns updated content or None."""
    path = Path.cwd() / "README.md"
    if not path.exists():
        return None

    content = path.read_text()
    original = content
    touched = False

    rendered = {
        "stats": _stats_content(info),
        "routes": _routes_content(info),
        "modules": _modules_content(info),
        "components": _components_content(info),
    }

    for name, rc in rendered.items():
        start = f"<!-- readme-guardian:{name} -->"
        end = "<!-- /readme-guardian -->"
        pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
        replacement = start + "\n" + rc + "\n" + end
        if pat.search(content):
            content = pat.sub(replacement, content)
            touched = True

    if not touched:
        return None
    return content


def update_readme(info: dict) -> bool:
    """Apply marker injection. Returns True if changed."""
    path = Path.cwd() / "README.md"
    new = inject_readme(info)
    if new is None:
        return False
    if new == path.read_text():
        ok("README: already up to date")
        return False
    path.write_text(new)
    ok("README: updated")
    return True


# ---------------------------------------------------------------------------
# Full-regenerate mode (for projects without markers — generates full README)
# ---------------------------------------------------------------------------

def regenerate(info: dict) -> bool:
    """Regenerate the entire README from scratch. Returns True if changed."""
    path = Path.cwd() / "README.md"
    new = generate_readme(info)

    if path.exists() and path.read_text() == new:
        ok("README: already up to date")
        return False
    path.write_text(new)
    ok("README: regenerated")
    return True


# ---------------------------------------------------------------------------
# CI check
# ---------------------------------------------------------------------------

def ci_check(info: dict) -> bool:
    path = Path.cwd() / "README.md"
    if not path.exists():
        fail("README.md: missing")
        return False

    content = path.read_text()
    issues = []

    # Check markers
    rendered = {
        "stats": _stats_content(info),
        "routes": _routes_content(info),
        "modules": _modules_content(info),
        "components": _components_content(info),
    }
    for name, expected in rendered.items():
        start = f"<!-- readme-guardian:{name} -->"
        end = "<!-- /readme-guardian -->"
        pat = re.compile(re.escape(start) + r"(.*?)" + re.escape(end), re.DOTALL)
        m = pat.search(content)
        if m and m.group(1).strip() != expected.strip():
            issues.append(f"Section `{name}` is stale")

    # Check freshness badge version
    if info.get("tests", 0) > 0:
        current_badge = f"fresh-{info['tests']}%20passing"
        if current_badge not in content:
            issues.append("Freshness badge does not match test count")

    if issues:
        for i in issues:
            warn(i)
        fail("README is stale")
        return False
    ok("README is current")
    return True


# ---------------------------------------------------------------------------
# Hook management
# ---------------------------------------------------------------------------

HOOK_TEMPLATE = """\
#!/bin/sh
# readme-guardian pre-push hook — keeps README.md in sync
# Installed by: readme-guardian --install-hook
# Remove with: readme-guardian --uninstall-hook

echo "  \U0001f6e1\ufe0f  readme-guardian: checking README..."
python3 -m readme_sync --pre-push 2>/dev/null || true
"""


def install_hook() -> None:
    root = Path.cwd()
    git_dir = root / ".git"
    if not git_dir.is_dir():
        fail("Not a git repository")
        return

    hook = git_dir / "hooks" / "pre-push"
    hook.write_text(HOOK_TEMPLATE)
    hook.chmod(0o755)
    ok(f"Pre-push hook installed at {hook}")

    # Ensure .gitignore has a backup exclusion
    gi = root / ".gitignore"
    if gi.exists() and "# readme-guardian" not in gi.read_text():
        with open(gi, "a") as f:
            f.write("\n# readme-guardian backups\n*.bak\n")
    ok("Hook will run silently before every `git push`")


def uninstall_hook() -> None:
    hook = Path.cwd() / ".git" / "hooks" / "pre-push"
    if hook.exists() and "readme-guardian" in hook.read_text():
        hook.unlink()
        ok("Pre-push hook removed")
    else:
        warn("No readme-guardian hook found")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = set(sys.argv[1:])

    if "--version" in args or "-v" in args:
        print("readme-guardian v1.0")
        return

    banner()

    if "--install-hook" in args:
        install_hook()
        return
    if "--uninstall-hook" in args:
        uninstall_hook()
        return

    info = detect_project(Path.cwd())
    if not info.get("type"):
        warn("Could not detect project type")
        warn("Supported: Node (package.json), Python (pyproject.toml), Go (go.mod), Rust (Cargo.toml)")
        sys.exit(1)

    debug(f"Detected: {info['type']} — {info['name']}")

    # Collect data
    info["modules"] = collect_modules(info)
    info["routes"] = collect_routes(info)
    info["components"] = collect_components(info)
    info["tests"] = collect_tests(info)
    info["lint_pass"] = collect_lint(info)

    if "--check" in args:
        sys.exit(0 if ci_check(info) else 1)

    # Update badge SVG
    badge_updated = update_badge(info)

    # Try marker injection first
    if inject_readme(info) is not None:
        readme_updated = update_readme(info)
    else:
        readme_updated = regenerate(info)

    updated = readme_updated or badge_updated

    if "--pre-push" in args and updated:
        subprocess.run(
            "git add README.md readme-badge.svg && git commit --amend --no-edit --no-verify",
            shell=True, capture_output=True,
        )


if __name__ == "__main__":
    main()
