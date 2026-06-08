#!/usr/bin/env python3
"""
Story 0.12 enforcement.

Walk Python sources and collect every `os.environ[...]`,
`os.environ.get(...)`, `os.getenv(...)`, and `env(...)` call.
Diff against keys present in `.env.example`. Exit non-zero on drift.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIRS = [ROOT / "config", ROOT / "apps"]
ENV_EXAMPLE = ROOT / ".env.example"


def collect_env_keys() -> set[str]:
    keys: set[str] = set()
    for root in SOURCE_DIRS:
        for path in root.rglob("*.py"):
            try:
                tree = ast.parse(path.read_text())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                # os.environ['X']
                if isinstance(node, ast.Subscript):
                    val = node.value
                    if (
                        isinstance(val, ast.Attribute)
                        and val.attr == "environ"
                        and isinstance(val.value, ast.Name)
                        and val.value.id == "os"
                    ):
                        idx = node.slice
                        if isinstance(idx, ast.Constant) and isinstance(idx.value, str):
                            keys.add(idx.value)
                if isinstance(node, ast.Call):
                    func = node.func
                    matched = False
                    if isinstance(func, ast.Attribute):
                        # os.environ.get('X')
                        if (
                            func.attr == "get"
                            and isinstance(func.value, ast.Attribute)
                            and func.value.attr == "environ"
                            and isinstance(func.value.value, ast.Name)
                            and func.value.value.id == "os"
                        ):
                            matched = True
                        # os.getenv('X')
                        elif (
                            func.attr == "getenv"
                            and isinstance(func.value, ast.Name)
                            and func.value.id == "os"
                        ):
                            matched = True
                        # env.bool('X'), env.list('X'), env.db('X'), env.int('X'), env.str('X')
                        elif (
                            isinstance(func.value, ast.Name)
                            and func.value.id == "env"
                        ):
                            matched = True
                    # env('X')
                    elif isinstance(func, ast.Name) and func.id == "env":
                        matched = True
                    if matched and node.args:
                        first = node.args[0]
                        if isinstance(first, ast.Constant) and isinstance(first.value, str):
                            keys.add(first.value)
    return keys


def declared_keys() -> set[str]:
    keys: set[str] = set()
    for raw in ENV_EXAMPLE.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            keys.add(line.split("=", 1)[0].strip())
    return keys


def main() -> int:
    used = collect_env_keys()
    declared = declared_keys()
    missing = sorted(used - declared)
    if missing:
        print("ERROR: .env.example is missing keys read by the code:")
        for k in missing:
            print(f"  - {k}")
        print(
            "\nAdd them to .env.example with a `# comment` on the line above. "
            "See docs/product/sprints/sprint-01/stories/0.12-env-audit.md."
        )
        return 1
    print(f"OK: all {len(used)} env keys in code are documented in .env.example.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
