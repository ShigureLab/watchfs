from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from aiofiles.os import wrap
from watchfiles import Change, awatch  # type: ignore

from watchfs import __version__
from watchfs.as_sync import as_sync
from watchfs.exceptions import ParseError
from watchfs.rusty import Err, Ok, Option, Result, Some

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
            await handle_removed(src_dir, dst_dir, child)
        dst.rmdir()
    elif dst.is_file():
        dst.unlink()


@as_sync
async def sync(src_dir: str, dst_dir: str):
    src = Path(src_dir).absolute()
    dst = Path(dst_dir).absolute()
    async for changes in awatch(src):
        for change, path in changes:
            path = Path(path).absolute()
            print(f"{change.name}: {path}")
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
    return Ok((src_dir, dst_dir))


def main():
    parser = argparse.ArgumentParser(prog="watchfs", description="Watch and sync files.")
    parser.add_argument("-v", "--version", action="version", version=__version__)
    parser.add_argument("sync_mapping", metavar="SRC_DIR:DST_DIR", type=str, nargs="+", help="Sync mapping file.")
    args = parser.parse_args()
    for sync_src_with_dst in args.sync_mapping:
        match parse_sync_mapping(sync_src_with_dst):
            case Ok((src_dir, dst_dir)):
                sync(src_dir, dst_dir)  # TODO: support sync multiple dir
            case Err(err):
                raise err


if __name__ == "__main__":
    main()
