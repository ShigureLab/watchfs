from __future__ import annotations

import argparse
import asyncio
import shutil
from pathlib import Path

from aiofiles.os import wrap
from colored import Back, Fore  # type: ignore
from watchfiles import Change, awatch  # type: ignore

from watchfs import __version__
from watchfs.as_sync import as_sync
from watchfs.colorful import Badge
from watchfs.exceptions import ParseError
from watchfs.rusty import Err, Ok, Result

BADGE_ADD = Badge("ADDED", Fore.black, Back.green)
BADGE_DEL = Badge("DELETED", Fore.black, Back.red)
BADGE_MOD = Badge("MODIFIED", Fore.black, Back.blue)
CHANGE_TYPE_TO_BADGE = {
    Change.added: BADGE_ADD,
    Change.deleted: BADGE_DEL,
    Change.modified: BADGE_MOD,
}

copyfile = wrap(shutil.copyfile)


async def handle_added(src_dir: Path, dst_dir: Path, changed: Path):
    await handle_modified(src_dir, dst_dir, changed)


async def handle_modified(src_dir: Path, dst_dir: Path, changed: Path):
    changed_rel_to_src = changed.relative_to(src_dir)
    dst = dst_dir / changed_rel_to_src
    if changed.is_dir():
        for child in changed.iterdir():
            await handle_modified(src_dir, dst_dir, child)
    elif changed.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        await copyfile(changed, dst)


async def handle_removed(src_dir: Path, dst_dir: Path, changed: Path):
    changed_rel_to_src = changed.relative_to(src_dir)
    dst = dst_dir / changed_rel_to_src
    if dst.is_dir():
        for child in dst.iterdir():
            child_rel_to_dst = child.relative_to(dst_dir)
            await handle_removed(src_dir, dst_dir, src_dir / child_rel_to_dst)
        dst.rmdir()
    elif dst.is_file():
        dst.unlink()


async def sync(src_dir: str, dst_dir: str):
    src = Path(src_dir).absolute()
    dst = Path(dst_dir).absolute()
    async for changes in awatch(src):
        for change, path in changes:
            path = Path(path).absolute()
            print(f"{CHANGE_TYPE_TO_BADGE[change]} {path}")
            match change:
                case Change.added:
                    await handle_added(src, dst, path)
                case Change.modified:
                    await handle_modified(src, dst, path)
                case Change.deleted:
                    await handle_removed(src, dst, path)


def parse_sync_mapping(sync_mapping: str) -> Result[tuple[str, str], ParseError]:
    splited_sync_mapping = sync_mapping.split(":")
    if len(splited_sync_mapping) != 2:
        return Err(ParseError("Invalid sync mapping."))
    src_dir, dst_dir = sync_mapping.split(":")

    # check if src_dir is a subdirectory of dst_dir
    abs_src_dir = Path(src_dir).resolve()
    abs_dst_dir = Path(dst_dir).resolve()
    if abs_src_dir in abs_dst_dir.parents:
        return Err(ParseError(f"src_dir({abs_src_dir}) is a subdirectory of dst_dir({abs_dst_dir})."))

    return Ok((src_dir, dst_dir))


@as_sync
async def main():
    parser = argparse.ArgumentParser(prog="watchfs", description="Watch and sync files.")
    parser.add_argument("-v", "--version", action="version", version=__version__)
    parser.add_argument("sync_mapping", metavar="SRC_DIR:DST_DIR", type=str, nargs="+", help="Sync mapping file.")
    args = parser.parse_args()
    parsed_sync_mapping: list[tuple[str, str]] = []
    for sync_src_with_dst in args.sync_mapping:
        match parse_sync_mapping(sync_src_with_dst):
            case Ok((src_dir, dst_dir)):
                parsed_sync_mapping.append((src_dir, dst_dir))
            case Err(err):
                raise err
    print(f"Starting watch {', '.join(map(lambda src_dst: f"{src_dst[0]} -> {src_dst[1]}", parsed_sync_mapping))}")
    print("Press Ctrl+C to exit.")
    try:
        await asyncio.gather(*[sync(src_dir, dst_dir) for src_dir, dst_dir in parsed_sync_mapping])
    except asyncio.exceptions.CancelledError:
        print("Bye!")


if __name__ == "__main__":
    main()
