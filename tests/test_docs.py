"""Tests for repository documentation."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RELATIVE_LINK = re.compile(r"\]\((?![a-zA-Z][a-zA-Z0-9+.-]*:)([^)#\s]+)")
SKIPPED_DIRS = {".git", ".beads", "archive"}


def markdown_files():
    return [
        path for path in REPO_ROOT.rglob("*.md")
        if not SKIPPED_DIRS & set(path.relative_to(REPO_ROOT).parts)
    ]


def test_markdown_relative_links_point_to_existing_files():
    broken = [
        f"{doc.relative_to(REPO_ROOT)} -> {target}"
        for doc in markdown_files()
        for target in RELATIVE_LINK.findall(doc.read_text(encoding="utf-8"))
        if not (doc.parent / target).exists()
    ]
    assert not broken, broken
