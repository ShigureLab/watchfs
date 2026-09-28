from __future__ import annotations

import asyncio
import sys
import sysconfig
from contextlib import aclosing
from typing import TYPE_CHECKING

from watchfiles import Change, awatch

from watchfs.__main__ import SyncEvent, SyncJob, apply_event, build_queue_key
from watchfs.mappings import LocalTargetSpec, SyncMapping
from watchfs.targets import LocalTarget

if TYPE_CHECKING:
    from pathlib import Path


def test_free_threaded_imports_keep_gil_disabled():
    if sys.version_info >= (3, 13) and sysconfig.get_config_var("Py_GIL_DISABLED"):
        assert not sys._is_gil_enabled()


def test_native_watch_and_local_sync(tmp_path: Path):
    async def watch_and_sync():
        source = tmp_path / "source"
        destination = tmp_path / "destination"
        source.mkdir()
        destination.mkdir()
        spec = LocalTargetSpec(destination)
        mapping = SyncMapping(source=source, target=spec)
        target = LocalTarget(spec)
        job = SyncJob(mapping=mapping, target=target, queue_key=build_queue_key(mapping))
        changed = source / "example.txt"

        async with aclosing(
            awatch(source, yield_on_timeout=True, rust_timeout=100, debounce=10, step=10, force_polling=False)
        ) as changes:
            # Drain setup events (e.g. macOS can report the new source directory).
            # An empty batch confirms the watcher is ready before creating a file.
            async for batch in changes:
                if not batch:
                    break
            changed.write_text("Python runtime smoke test")
            async for batch in changes:
                if (Change.added, str(changed)) in batch:
                    break
            await apply_event(SyncEvent(job=job, change=Change.added, path=changed))
            assert (destination / changed.name).read_text() == changed.read_text()

        if sys.version_info >= (3, 13) and sysconfig.get_config_var("Py_GIL_DISABLED"):
            assert not sys._is_gil_enabled()

    async def run():
        async with asyncio.timeout(10):
            await watch_and_sync()

    asyncio.run(run())
