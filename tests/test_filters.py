from __future__ import annotations

from pathlib import Path

from watchfiles import Change

from watchfs.filters import ExcludeFilter, iter_path_suffixes, match_pattern


def test_iter_path_suffixes_for_absolute_path():
    path = Path("/Users/meow/Projects/watchfs/.git/objects/8f/file")
    assert iter_path_suffixes(path) == [
        "Users/meow/Projects/watchfs/.git/objects/8f/file",
        "meow/Projects/watchfs/.git/objects/8f/file",
        "Projects/watchfs/.git/objects/8f/file",
        "watchfs/.git/objects/8f/file",
        ".git/objects/8f/file",
        "objects/8f/file",
        "8f/file",
        "file",
    ]


def test_match_relative_glob_excludes_git_tree():
    assert match_pattern(
        Path("/Users/meow/Projects/watchfs/.git/objects/8f/tmp_obj_oigEsw"),
        ".git/**",
    )


def test_match_relative_glob_excludes_git_directory_root():
    assert match_pattern(
        Path("/Users/meow/Projects/watchfs/.git"),
        ".git/**",
    )


def test_match_absolute_glob_pattern():
    assert match_pattern(
        Path("/Users/meow/Projects/watchfs/.git/config"),
        "/Users/meow/Projects/watchfs/.git/**",
    )


def test_exclude_filter_blocks_git_events():
    filter_ = ExcludeFilter(".git/**")
    assert filter_(Change.added, "/Users/meow/Projects/watchfs/.git/objects/8f") is False
    assert filter_(Change.added, "/Users/meow/Projects/watchfs/.git/objects/8f/tmp_obj_oigEsw") is False
    assert filter_(Change.modified, "/Users/meow/Projects/watchfs/.git/config") is False
    assert filter_(Change.modified, "/Users/meow/Projects/watchfs/src/watchfs/__main__.py") is True
