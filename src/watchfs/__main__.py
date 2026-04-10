from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from colored import Back, Fore
from watchfiles import Change, awatch  # type: ignore

from watchfs import __version__
from watchfs.as_sync import as_sync
from watchfs.colorful import Badge
from watchfs.filters import ChangeCacheFilter, ExcludeFilter, combine_filters
from watchfs.mappings import SshTargetSpec, SyncMapping, parse_sync_mapping
from watchfs.rusty import Err, Ok
from watchfs.targets import SyncTarget, create_target

if TYPE_CHECKING:
    from watchfiles.filters import BaseFilter

BADGE_ADD = Badge("ADDED", Fore.black, Back.green)  # type: ignore
BADGE_DEL = Badge("DELETED", Fore.black, Back.red)  # type: ignore
BADGE_MOD = Badge("MODIFIED", Fore.black, Back.blue)  # type: ignore
CHANGE_TYPE_TO_BADGE = {
    Change.added: BADGE_ADD,
    Change.deleted: BADGE_DEL,
    Change.modified: BADGE_MOD,
}


async def handle_added(src_dir: Path, target: SyncTarget, changed: Path):
    await handle_modified(src_dir, target, changed)


async def handle_modified(src_dir: Path, target: SyncTarget, changed: Path):
    changed_rel_to_src = changed.relative_to(src_dir)
    if changed.is_dir():
        for child in changed.iterdir():
            await handle_modified(src_dir, target, child)
    elif changed.is_file():
        await target.write_file(changed_rel_to_src, changed)


async def handle_removed(src_dir: Path, target: SyncTarget, changed: Path):
    changed_rel_to_src = changed.relative_to(src_dir)
    await target.remove_path(changed_rel_to_src)


@dataclass(frozen=True, slots=True)
class SyncJob:
    mapping: SyncMapping
    target: SyncTarget
    queue_key: str


@dataclass(frozen=True, slots=True)
class SyncEvent:
    job: SyncJob
    change: Change
    path: Path


async def consume_target_queue(queue: asyncio.Queue[SyncEvent]) -> None:
    while True:
        event = await queue.get()
        try:
            try:
                await apply_event(event)
            except asyncio.CancelledError:
                raise
            except Exception as err:
                print(f"Failed to sync {event.path} to {event.job.target.description}: {err}", file=sys.stderr)
        finally:
            queue.task_done()


async def apply_event(event: SyncEvent) -> None:
    src_dir = event.job.mapping.source.resolve()
    match event.change:
        case Change.added:
            await handle_added(src_dir, event.job.target, event.path)
        case Change.modified:
            await handle_modified(src_dir, event.job.target, event.path)
        case Change.deleted:
            await handle_removed(src_dir, event.job.target, event.path)


async def watch_source(
    source: Path,
    jobs: list[SyncJob],
    queues: dict[str, asyncio.Queue[SyncEvent]],
    filter: BaseFilter,
    *,
    force_polling: bool = False,
) -> None:
    async for changes in awatch(source, watch_filter=filter, force_polling=force_polling):
        for change, path in changes:
            path = Path(path).absolute()
            print(f"{CHANGE_TYPE_TO_BADGE[change]} {path}")
            for job in jobs:
                await queues[job.queue_key].put(SyncEvent(job=job, change=change, path=path))


def build_queue_key(mapping: SyncMapping) -> str:
    if isinstance(mapping.target, SshTargetSpec):
        return f"ssh:{mapping.target.credential_key()}"
    return f"local:{mapping.target.display()}"


@as_sync
async def main():
    parser = argparse.ArgumentParser(prog="watchfs", description="Watch and sync files.")
    parser.add_argument("-v", "--version", action="version", version=__version__)
    parser.add_argument(
        "sync_mapping",
        metavar="SRC->DST",
        type=str,
        nargs="+",
        help="Sync mapping file. Use SRC->DST for SSH destinations such as user@host:/path.",
    )
    parser.add_argument("--exclude", type=str, help="Exclude directories or files, separated by comma.")
    parser.add_argument("-cc", "--enable-content-caching", action="store_true", help="Enable content caching.")
    parser.add_argument("--force-polling", action="store_true", help="Enable force polling.")
    args = parser.parse_args()
    parsed_sync_mapping: list[SyncMapping] = []
    for sync_src_with_dst in args.sync_mapping:
        match parse_sync_mapping(sync_src_with_dst):
            case Ok((mapping, bidirectional)):
                parsed_sync_mapping.append(mapping)
                if bidirectional:
                    match parse_sync_mapping(f"{mapping.target.display()}->{mapping.source}"):
                        case Ok((reverse_mapping, _)):
                            parsed_sync_mapping.append(reverse_mapping)
                        case Err(err):
                            raise err
            case Err(err):
                raise err

    jobs = [
        SyncJob(
            mapping=mapping,
            target=create_target(mapping.target),
            queue_key=build_queue_key(mapping),
        )
        for mapping in parsed_sync_mapping
    ]

    filters: list[BaseFilter] = []
    if args.exclude:
        filters.append(ExcludeFilter(args.exclude))
    if args.enable_content_caching:
        filters.append(ChangeCacheFilter())

    combined_filter = combine_filters(filters)
    print(f"Starting watch {', '.join(mapping.display() for mapping in parsed_sync_mapping)}")
    print("Press Ctrl+C to exit.")
    queues: dict[str, asyncio.Queue[SyncEvent]] = {job.queue_key: asyncio.Queue() for job in jobs}
    source_jobs: dict[Path, list[SyncJob]] = {}
    for job in jobs:
        source_jobs.setdefault(job.mapping.source.resolve(), []).append(job)
    worker_tasks: list[asyncio.Task[None]] = []
    watcher_tasks: list[asyncio.Task[None]] = []
    try:
        await asyncio.gather(*(job.target.start() for job in jobs))
        worker_tasks = [asyncio.create_task(consume_target_queue(queue)) for queue in queues.values()]
        watcher_tasks = [
            asyncio.create_task(
                watch_source(
                    source,
                    grouped_jobs,
                    queues,
                    combined_filter,
                    force_polling=args.force_polling,
                )
            )
            for source, grouped_jobs in source_jobs.items()
        ]
        await asyncio.gather(*worker_tasks, *watcher_tasks)
    except asyncio.exceptions.CancelledError:
        print("Bye!")
    finally:
        for task in watcher_tasks:
            task.cancel()
        for task in worker_tasks:
            task.cancel()
        await asyncio.gather(*watcher_tasks, *worker_tasks, return_exceptions=True)
        await asyncio.gather(*(job.target.close() for job in jobs))


if __name__ == "__main__":
    main()
