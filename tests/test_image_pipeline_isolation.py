"""Track 2 must be unable to publish an image by itself.

The scraping/matching path may only write to image_candidates. Setting
products.image_id is reserved for the staff approval flow, because a photo of the
wrong pack on a NAFDAC-regulated pharmacy is a patient-safety failure.

This is a static check over the real source files rather than a behavioural one:
a behavioural test only proves the paths it exercises, while this fails the moment
anyone adds the assignment anywhere in the pipeline.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Everything Track 2 consists of.
PIPELINE_FILES = [
    ROOT / "app" / "services" / "image_matching.py",
    ROOT / "scripts" / "scrape_manufacturer_images.py",
    *sorted((ROOT / "scripts" / "scrapers").glob("*.py")),
]


def _assigned_attributes(tree: ast.AST) -> list[str]:
    """Every `something.attr = ...` target in the module."""
    out = []
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = [node.target]
        for t in targets:
            if isinstance(t, ast.Attribute):
                out.append(t.attr)
    return out


def test_pipeline_files_all_exist():
    """If a file is renamed, this guard must be updated rather than silently pass."""
    assert len(PIPELINE_FILES) >= 8
    for path in PIPELINE_FILES:
        assert path.exists(), path


@pytest.mark.parametrize("path", PIPELINE_FILES, ids=lambda p: p.name)
def test_no_pipeline_module_assigns_product_image_id(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    assert "image_id" not in _assigned_attributes(tree), (
        f"{path.relative_to(ROOT)} assigns .image_id. Track 2 must only write to "
        "image_candidates; publishing an image is the staff approval flow's job."
    )


@pytest.mark.parametrize("path", PIPELINE_FILES, ids=lambda p: p.name)
def test_no_pipeline_module_calls_store_image(path: Path):
    """Bytes reach media_assets only on approval, not on scrape."""
    src = path.read_text(encoding="utf-8")
    assert "store_image" not in src, (
        f"{path.relative_to(ROOT)} calls store_image. Track 2 stages URLs only; the "
        "image enters media_assets when staff approve it."
    )


def test_pipeline_never_sets_is_listed():
    """Scraping must not make a product visible to customers."""
    for path in PIPELINE_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assert "is_listed" not in _assigned_attributes(tree), path


# Libraries that would make matching approximate. Checked as IMPORTS via AST, not as
# substrings, so the module's own prose explaining that it does not use them is not a
# false positive.
FUZZY_MODULES = {
    "difflib", "Levenshtein", "levenshtein", "fuzzywuzzy", "rapidfuzz", "thefuzz",
    "jellyfish", "textdistance", "metaphone", "sentence_transformers", "sklearn",
    "numpy", "scipy", "gensim",
}


@pytest.mark.parametrize("path", PIPELINE_FILES, ids=lambda p: p.name)
def test_no_pipeline_module_imports_a_fuzzy_matcher(path: Path):
    """No edit distance, no embeddings, no similarity library. Ever."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module.split(".")[0])

    found = sorted(set(imported) & FUZZY_MODULES)
    assert not found, (
        f"{path.relative_to(ROOT)} imports {found}. Matching is exact by design — "
        "approximate matching on medicine packs is a patient-safety risk."
    )


def test_matching_uses_plain_string_equality():
    """The comparison itself must be ==, not a similarity score above a threshold."""
    src = (ROOT / "app" / "services" / "image_matching.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    equal_fn = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_equal"
    )
    comparisons = [n for n in ast.walk(equal_fn) if isinstance(n, ast.Compare)]
    ops = {type(op).__name__ for c in comparisons for op in c.ops}
    assert ops <= {"Eq"}, f"_equal uses non-equality comparisons: {ops}"
