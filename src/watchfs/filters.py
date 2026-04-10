from __future__ import annotations

import fnmatch
import hashlib
import time
from pathlib import Path

from watchfiles import Change
from watchfiles.filters import BaseFilter


def match_pattern(path: Path, pattern: str) -> bool:
    normalized_path = path.as_posix()
    if Path(pattern).is_absolute():
        return _match_candidate(normalized_path, pattern)

    return any(_match_candidate(candidate, pattern) for candidate in iter_path_suffixes(path))


def iter_path_suffixes(path: Path) -> list[str]:
    parts = path.parts[1:] if path.is_absolute() else path.parts
    return ["/".join(parts[index:]) for index in range(len(parts))]


def _match_candidate(candidate: str, pattern: str) -> bool:
    normalized_pattern = pattern.rstrip("/")
    if _contains_glob(pattern):
        if fnmatch.fnmatchcase(candidate, pattern):
            return True
        if pattern.endswith("/**"):
            return _match_candidate(candidate, pattern.removesuffix("/**"))
        return False

    return candidate == normalized_pattern or candidate.startswith(f"{normalized_pattern}/")


def _contains_glob(pattern: str) -> bool:
    return any(token in pattern for token in "*?[]")


class ExcludeFilter(BaseFilter):
    def __init__(self, cli_arg: str):
        super().__init__()
        self.exclude_patterns = self.parse_cli_arg(cli_arg)

    def __call__(self, change: Change, path: str) -> bool:
        return all(not match_pattern(Path(path), pattern) for pattern in self.exclude_patterns)

    @staticmethod
    def parse_cli_arg(cli_arg: str) -> list[str]:
        exclude_patterns: list[str] = []
        for arg in cli_arg.split(","):
            stripped_arg = arg.strip()
            if not stripped_arg:
                continue
            exclude_patterns.append(Path(stripped_arg).expanduser().as_posix())
        return exclude_patterns


class ChangeCacheFilter(BaseFilter):
    CACHE_MAX_ALIVE_TIME = 1

    def __init__(self):
        super().__init__()
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
