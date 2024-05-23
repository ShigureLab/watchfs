from __future__ import annotations

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


class CombinedFilter(BaseFilter):
    def __init__(self, filters: list[BaseFilter]):
        self.filters = filters

    def __call__(self, change: Change, path: str) -> bool:
        return all(filter(change, path) for filter in self.filters)


def combine_filters(filters: list[BaseFilter]) -> BaseFilter:
    return CombinedFilter(filters)
