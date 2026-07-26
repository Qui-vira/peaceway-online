"""Guard the app against importing things the deployed container does not have.

Railway builds from .railwayignore, which deliberately excludes dev-only trees —
`scripts/`, `tests/`, `docs/`. Anything under `app/` that imports from those is fine
locally and dies at container startup.

This is not hypothetical: on 2026-07-26 a deploy failed its healthcheck with
`ModuleNotFoundError: No module named 'scripts'`, because app/bot/staff/products_csv.py
imported `normalize_name` from scripts/import_pharmaos.py. The import graph must point
app <- scripts, never the reverse.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parent.parent / "app"
RAILWAYIGNORE = Path(__file__).resolve().parent.parent / ".railwayignore"


def _excluded_top_level_dirs() -> set[str]:
    """Top-level directories .railwayignore keeps out of the deployed image."""
    out = set()
    for line in RAILWAYIGNORE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if line.endswith("/") and "/" not in line[:-1] and not line.startswith("."):
            out.add(line[:-1])
    return out


def _app_modules():
    return sorted(APP.rglob("*.py"))


def test_railwayignore_still_excludes_dev_trees():
    """If this fails the guard below is testing nothing — update both together."""
    excluded = _excluded_top_level_dirs()
    assert "scripts" in excluded
    assert "tests" in excluded


@pytest.mark.parametrize("path", _app_modules(), ids=lambda p: str(p.name))
def test_app_never_imports_deploy_excluded_packages(path: Path):
    excluded = _excluded_top_level_dirs()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            root = node.module.split(".")[0]
            if root in excluded:
                offenders.append(f"line {node.lineno}: from {node.module} import ...")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in excluded:
                    offenders.append(f"line {node.lineno}: import {alias.name}")

    assert not offenders, (
        f"{path.relative_to(APP.parent)} imports a package excluded from the Railway "
        f"upload — it will crash at container startup:\n  " + "\n  ".join(offenders)
    )


# The runtime counterpart — actually calling build_dispatcher(), which is the startup
# path that failed — is covered by tests/test_bot_errors.py. It is deliberately not
# repeated here: aiogram routers are module-level singletons, so a second
# build_dispatcher() in the same session raises "Router is already attached".
