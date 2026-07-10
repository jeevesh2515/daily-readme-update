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

import argparse
import difflib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path


VERSION = "1.0.1"


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
    print(f"  \U0001f6e1\ufe0f  readme-guardian v{VERSION}", file=sys.stderr)
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
                info["test_command"] = "npm test -- --reporter=min || npm test"
            if "build" in info["scripts"]:
                info["build_command"] = "npm run build"
            if "lint" in info["scripts"]:
                info["lint_command"] = "npm run lint"

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
        info["test_command"] = "go test ./..."
        info["build_command"] = "go build ./..."

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
        info["test_command"] = "cargo test"
        info["build_command"] = "cargo build"

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
        return shlex.quote(str(bin_path))
    if (root / "pyproject.toml").exists():
        with open(root / "pyproject.toml") as f:
            if tool in f.read():
                venv_python = root / ".venv" / "bin" / "python"
                if tool == "pytest":
                    return f"{shlex.quote(str(venv_python))} -m pytest -q" if venv_python.exists() else None
                elif tool == "ruff":
                    return f"{shlex.quote(str(venv_python))} -m ruff check ." if venv_python.exists() else None
    return None


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def _run(cmd: str, root: Path, timeout: int = 60) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=root, timeout=timeout)
        return r.returncode, (r.stdout + "\n" + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "(timeout)"
    except FileNotFoundError:
        return -1, "(not found)"


SKIP_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__tests__",
    "build",
    "dist",
    "node_modules",
    "spec",
    "test",
    "tests",
    "__pycache__",
}


def iter_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix.lower() in suffixes:
            paths.append(path)
    return sorted(paths)


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
    for path in iter_files(root, (".py",)):
        try:
            content = path.read_text(errors="ignore")
            for m in re.finditer(
                r'@(?:router|app)\.(get|post|put|delete|patch|options|head)\s*\(\s*["\']([^"\']+)',
                content,
                re.IGNORECASE,
            ):
                routes.add(f"{m.group(1).upper()} {m.group(2)}")
            for m in re.finditer(
                r'@(?:app)\.route\s*\(\s*["\']([^"\']+)["\']\s*,\s*methods\s*=\s*\[([^\]]+)\]',
                content,
                re.IGNORECASE,
            ):
                route_path = m.group(1)
                methods = re.findall(r'["\']([A-Z]+)["\']', m.group(2), re.IGNORECASE)
                for method in methods or ["GET"]:
                    routes.add(f"{method.upper()} {route_path}")
        except Exception:
            pass

    # Next.js App Router
    for path in root.glob("app/api/**/route.*"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        rel = path.relative_to(root)
        parts = rel.parts
        route_parts = []
        for p in parts:
            if p == "app" or p.startswith("route."):
                continue
            if p.startswith("["):
                route_parts.append(f":{p.strip('[]')}")
            else:
                route_parts.append(p)
        route_path = "/" + "/".join(route_parts)
        try:
            content = path.read_text(errors="ignore")
            methods = re.findall(r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)\b", content)
        except Exception:
            methods = []
        for method in methods or ["GET"]:
            routes.add(f"{method.upper()} {route_path}")

    # Express/Fastify
    for path in iter_files(root, (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
        try:
            content = path.read_text(errors="ignore")
            for m in re.finditer(r'\.(get|post|put|delete|all|patch|options|head)\s*\(\s*["\'`]([^"\'`]+)', content, re.IGNORECASE):
                routes.add(f"{m.group(1).upper()} {m.group(2)}")
        except Exception:
            pass

    # Go
    for path in iter_files(root, (".go",)):
        try:
            content = path.read_text(errors="ignore")
            for m in re.finditer(r'\.(Get|Post|Put|Delete|Patch|Handle|Options|Head)\s*\(\s*["\']([^"\']+)', content):
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
    for path in iter_files(frontend_root, (".tsx", ".jsx", ".vue", ".svelte")):
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
    elif tests == -1:
        status = "fresh"
        message = "tests pass"
        color = "#4c1"
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
    test_str = f"{info['tests']}%20passing" if info.get("tests", 0) > 0 else "tests%20pass" if info.get("tests") == -1 else "synced"
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

    # Avoid embedding the commit hash: a README cannot contain the hash of the
    # commit that contains it without becoming stale after every amend.
    rc, commit_msg = _run("git log -1 --format=%s", Path.cwd())
    commit_msg_str = commit_msg if rc == 0 else ""

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
    if commit_msg_str:
        lines.append(f"\n_Latest commit: `{commit_msg_str}`_\n")

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
    t_str = f"{tests} passing" if tests > 0 else "passing (count unknown)" if tests == -1 else "—"
    lint = "clean" if info.get("lint_pass") else "issues" if info.get("lint_pass") is False else "—"
    docker = "yes" if info.get("has_docker") else "no"
    monorepo = "yes" if info.get("is_monorepo") else "no"
    rc, commit = _run("git log -1 --format=%s", Path.cwd())
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


def desired_readme(info: dict) -> str | None:
    """Return the README content readme-guardian expects for this project."""
    injected = inject_readme(info)
    if injected is not None:
        return injected
    return generate_readme(info)


def planned_changes(info: dict) -> dict[str, tuple[str, str]]:
    """Return changed files as {path: (current, desired)} without writing."""
    changes: dict[str, tuple[str, str]] = {}

    readme_path = Path.cwd() / "README.md"
    current_readme = readme_path.read_text() if readme_path.exists() else ""
    next_readme = desired_readme(info)
    if next_readme is not None and current_readme != next_readme:
        changes["README.md"] = (current_readme, next_readme)

    badge_path = Path.cwd() / "readme-badge.svg"
    current_badge = badge_path.read_text() if badge_path.exists() else ""
    next_badge = generate_badge(info)
    if current_badge != next_badge:
        changes["readme-badge.svg"] = (current_badge, next_badge)

    return changes


def apply_changes(changes: dict[str, tuple[str, str]]) -> bool:
    for rel, (_, desired) in changes.items():
        (Path.cwd() / rel).write_text(desired)
        ok(f"{rel}: updated")
    if not changes:
        ok("README: already up to date")
        return False
    return True


def print_preview(changes: dict[str, tuple[str, str]]) -> None:
    if not changes:
        ok("README is current")
        return

    warn("README is stale")
    for rel, (current, desired) in changes.items():
        print(file=sys.stderr)
        print(f"--- {rel}", file=sys.stderr)
        diff = difflib.unified_diff(
            current.splitlines(),
            desired.splitlines(),
            fromfile=f"{rel} (current)",
            tofile=f"{rel} (expected)",
            lineterm="",
        )
        for line in diff:
            print(line, file=sys.stderr)


# ---------------------------------------------------------------------------
# CI check
# ---------------------------------------------------------------------------

def ci_check(info: dict) -> bool:
    changes = planned_changes(info)
    if changes:
        for rel in changes:
            warn(f"{rel} is stale")
        fail("README is stale")
        return False
    ok("README is current")
    return True


# ---------------------------------------------------------------------------
# Hook management
# ---------------------------------------------------------------------------

HOOK_TEMPLATE = """\
#!/bin/sh
# readme-guardian pre-push hook - keeps README.md in sync
# Installed by: readme-guardian --install-hook
# Remove with: readme-guardian --uninstall-hook

echo "  \U0001f6e1\ufe0f  readme-guardian: checking README..."
if command -v readme-guardian >/dev/null 2>&1; then
  readme-guardian --apply --pre-push
else
  python3 -m readme_sync --apply --pre-push
fi

if ! git diff --quiet -- README.md readme-badge.svg 2>/dev/null; then
  echo "  readme-guardian updated README.md/readme-badge.svg."
  echo "  Review and commit those changes, then push again."
  exit 1
fi
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

    ok("Hook will run silently before every `git push`")


def uninstall_hook() -> None:
    hook = Path.cwd() / ".git" / "hooks" / "pre-push"
    if hook.exists() and "readme-guardian" in hook.read_text():
        hook.unlink()
        ok("Pre-push hook removed")
    else:
        warn("No readme-guardian hook found")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="readme-guardian",
        description="Keep README.md and readme-badge.svg in sync with live project facts.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="write README.md and readme-badge.svg updates")
    mode.add_argument("--check", action="store_true", help="exit 1 when README.md or badge is stale")
    mode.add_argument("--status", action="store_true", help="show whether README.md and badge are current")
    parser.add_argument("--install-hook", action="store_true", help="install the git pre-push hook")
    parser.add_argument("--uninstall-hook", action="store_true", help="remove the git pre-push hook")
    parser.add_argument("--pre-push", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--version", "-v", action="store_true", help="show version")
    return parser


def collect_info(root: Path) -> dict:
    info = detect_project(root)
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

    return info


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        print(f"readme-guardian v{VERSION}")
        return

    banner()

    if args.install_hook:
        install_hook()
        return
    if args.uninstall_hook:
        uninstall_hook()
        return

    info = collect_info(Path.cwd())
    changes = planned_changes(info)

    if args.check:
        sys.exit(0 if ci_check(info) else 1)

    if args.status:
        if changes:
            for rel in changes:
                warn(f"{rel} is stale")
            sys.exit(1)
        ok("README is current")
        return

    if args.apply or args.pre_push:
        apply_changes(changes)
        return

    print_preview(changes)


if __name__ == "__main__":
    main()
