from __future__ import annotations

import hashlib
import time
from pathlib import Path

from watchfiles import Change
from watchfiles.filters import BaseFilter, DefaultFilter


class ExcludeFilter(DefaultFilter):
    def __init__(self, cli_arg: str):
        ignore_dirs, ignore_entity_patterns, ignore_paths = self.parse_cli_arg(cli_arg)
        super().__init__(
            ignore_dirs=ignore_dirs,
            ignore_entity_patterns=ignore_entity_patterns,
            ignore_paths=ignore_paths,
        )

    @staticmethod
    def parse_cli_arg(cli_arg: str) -> tuple[list[str], list[str], list[str]]:
        ignore_dirs: list[str] = []
        ignore_entity_patterns: list[str] = []
        ignore_paths: list[str] = []
        for arg in cli_arg.split(","):
            arg = str(Path(arg).absolute())
            if "*" in arg:
                ignore_entity_patterns.append(arg)
            elif Path(arg).is_dir():
                ignore_dirs.append(arg)
            else:
                ignore_paths.append(arg)
        return ignore_dirs, ignore_entity_patterns, ignore_paths


class ChangeCacheFilter(BaseFilter):
    CACHE_MAX_ALIVE_TIME = 1

    def __init__(self):
        self.cache: dict[str, tuple[float, str]] = {}

    def __call__(self, change: Change, path: str) -> bool:
        match change:
            case Change.added | Change.modified:
                return not self.lookup_cache(path)
            case Change.deleted:
                return True

    def clean_dead_cache(self) -> None:
        to_delete: list[str] = []
        for path, (timestamp, _) in self.cache.items():
            if time.time() - timestamp > self.CACHE_MAX_ALIVE_TIME:
                to_delete.append(path)
        for path in to_delete:
            del self.cache[path]

    def lookup_cache(self, path: str) -> bool:
        self.clean_dead_cache()
        if path not in self.cache:
            self.cache[path] = (time.time(), self.calc_file_md5(path))
            return False
        _, md5 = self.cache[path]
        if md5 != self.calc_file_md5(path):
            self.cache[path] = (time.time(), self.calc_file_md5(path))
            return False
        return True

    def calc_file_md5(self, path: str) -> str:
        with Path(path).open("rb") as f:
            return hashlib.md5(f.read()).hexdigest()


class CombinedFilter(BaseFilter):
    def __init__(self, filters: list[BaseFilter]):
        self.filters = filters

    def __call__(self, change: Change, path: str) -> bool:
        return all(filter(change, path) for filter in self.filters)


def combine_filters(filters: list[BaseFilter]) -> BaseFilter:
    return CombinedFilter(filters)
