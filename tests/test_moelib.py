from __future__ import annotations

import tomllib
from pathlib import Path

from watchfs import __version__

with Path("pyproject.toml").open("rb") as f:
    project_info = tomllib.load(f)


def test_version():
    assert __version__ == project_info["tool"]["poetry"]["version"]
