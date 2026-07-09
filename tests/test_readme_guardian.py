import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

import readme_sync


@contextmanager
def cwd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


class ReadmeGuardianTests(unittest.TestCase):
    def test_detects_routes_without_scanning_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "pyproject.toml", '[project]\nname = "api-demo"\nversion = "0.1.0"\n')
            write(
                root / "app.py",
                '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/users")
def create_user():
    return {}
''',
            )
            write(
                root / "server.js",
                '''
app.patch("/users/:id", updateUser)
''',
            )
            write(root / "node_modules/pkg/index.js", 'app.get("/vendor", handler)\n')

            with cwd(root):
                self.assertEqual(
                    readme_sync.collect_routes({}),
                    ["GET /health", "PATCH /users/:id", "POST /users"],
                )

    def test_detects_next_routes_and_components(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root / "package.json",
                '{"name":"web-demo","version":"1.2.3","dependencies":{"react":"latest","next":"latest"}}',
            )
            write(
                root / "app/api/users/[id]/route.ts",
                '''
export async function GET() {}
export function POST() {}
''',
            )
            write(root / "src/components/Button.tsx", "export function Button() { return null }\n")
            write(root / "src/components/page.tsx", "export default function Page() { return null }\n")

            with cwd(root):
                info = readme_sync.detect_project(root)
                self.assertEqual(info["type"], "node")
                self.assertEqual(
                    readme_sync.collect_routes(info),
                    ["GET /api/users/:id", "POST /api/users/:id"],
                )
                self.assertEqual(readme_sync.collect_components(info), ["Button"])

    def test_planned_changes_reports_stale_files_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stale = """# Demo

<!-- readme-guardian:stats -->
old stats
<!-- /readme-guardian -->
"""
            write(root / "README.md", stale)
            write(root / "readme-badge.svg", "old badge")

            info = {
                "type": "python",
                "version": "1.0.0",
                "tests": 3,
                "lint_pass": True,
                "has_docker": False,
                "is_monorepo": False,
                "routes": [],
                "modules": [],
                "components": [],
            }

            with cwd(root):
                changes = readme_sync.planned_changes(info)
                self.assertEqual(set(changes), {"README.md", "readme-badge.svg"})
                self.assertEqual((root / "README.md").read_text(), stale)
                self.assertEqual((root / "readme-badge.svg").read_text(), "old badge")

    def test_apply_changes_makes_check_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root / "README.md",
                """# Demo

<!-- readme-guardian:stats -->
old stats
<!-- /readme-guardian -->

<!-- readme-guardian:routes -->
old routes
<!-- /readme-guardian -->
""",
            )

            info = {
                "type": "python",
                "version": "1.0.0",
                "tests": -1,
                "lint_pass": None,
                "has_docker": False,
                "is_monorepo": False,
                "routes": ["GET /health"],
                "modules": [],
                "components": [],
            }

            with cwd(root):
                changes = readme_sync.planned_changes(info)
                self.assertTrue(readme_sync.apply_changes(changes))
                self.assertTrue(readme_sync.ci_check(info))
                self.assertEqual(readme_sync.planned_changes(info), {})
                self.assertIn("tests pass", (root / "readme-badge.svg").read_text())


if __name__ == "__main__":
    unittest.main()
