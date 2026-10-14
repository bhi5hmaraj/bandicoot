"""Tests for repository documentation."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RELATIVE_LINK = re.compile(r"\]\((?!https?://)([^)#\s]+)")


def test_readme_relative_links_point_to_existing_files():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    missing = [path for path in RELATIVE_LINK.findall(readme) if not (REPO_ROOT / path).exists()]
    assert not missing, missing
