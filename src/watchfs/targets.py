from __future__ import annotations

import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PurePath, PurePosixPath
from typing import IO, Protocol

from aiofiles.os import wrap

from watchfs.mappings import LocalTargetSpec, SshTargetSpec, TargetSpec

copyfile = wrap(shutil.copyfile)


class SyncTarget(Protocol):
    description: str

    async def start(self) -> None: ...

    async def close(self) -> None: ...

    async def write_file(self, relative_path: PurePath, source: Path) -> None: ...

    async def remove_path(self, relative_path: PurePath) -> None: ...


@dataclass(slots=True)
class LocalTarget:
    spec: LocalTargetSpec
    description: str = field(init=False)

    def __post_init__(self) -> None:
        self.description = self.spec.display()

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def write_file(self, relative_path: PurePath, source: Path) -> None:
        dst = self.spec.path / Path(*relative_path.parts)
        dst.parent.mkdir(parents=True, exist_ok=True)
        await copyfile(source, dst)

    async def remove_path(self, relative_path: PurePath) -> None:
        dst = self.spec.path / Path(*relative_path.parts)
        if dst.is_dir():
            await _remove_directory(dst)
        elif dst.exists():
            dst.unlink()


@dataclass(slots=True)
class SshTarget:
    spec: SshTargetSpec
    description: str = field(init=False)

    def __post_init__(self) -> None:
        self.description = self.spec.display()

    async def start(self) -> None:
        await self._run_ssh_command("true")

    async def close(self) -> None:
        return None

    async def write_file(self, relative_path: PurePath, source: Path) -> None:
        remote_path = self._remote_path(relative_path)
        remote_dir = _quote_remote_path(remote_path.parent.as_posix())
        remote_file = _quote_remote_path(remote_path.as_posix())
        command = f"mkdir -p -- {remote_dir} && cat > {remote_file}"

        with source.open("rb") as stdin:
            await self._run_ssh_command(command, stdin=stdin)

    async def remove_path(self, relative_path: PurePath) -> None:
        remote_path = _quote_remote_path(self._remote_path(relative_path).as_posix())
        command = (
            f"if [ -d {remote_path} ]; then "
            f"rm -rf -- {remote_path}; "
            f"elif [ -e {remote_path} ]; then "
            f"rm -f -- {remote_path}; "
            "fi"
        )
        await self._run_ssh_command(command)

    async def _run_ssh_command(self, remote_command: str, *, stdin: IO[bytes] | int | None = None) -> None:
        command = self._ssh_base_command()
        command.append(remote_command)
        result = await _run_command(command, stdin=stdin)
        if result.returncode != 0:
            stderr_text = result.stderr.decode().strip() if result.stderr else "unknown ssh error"
            raise RuntimeError(f"SSH command failed for {self.description}: {stderr_text}")

    def _ssh_base_command(self) -> list[str]:
        command = ["ssh"]
        if self.spec.port != 22:
            command.extend(["-p", str(self.spec.port)])
        command.extend(["-o", "BatchMode=yes"])
        command.append(self.spec.authority())
        if self.spec.jump_host is not None:
            # TODO: add jump host / ProxyJump support.
            pass
        return command

    def _remote_path(self, relative_path: PurePath) -> PurePosixPath:
        relative_posix = PurePosixPath(*relative_path.parts)
        return self.spec.path / relative_posix


def create_target(spec: TargetSpec) -> SyncTarget:
    if isinstance(spec, LocalTargetSpec):
        return LocalTarget(spec)
    return SshTarget(spec)


async def _remove_directory(path: Path) -> None:
    import asyncio

    await asyncio.to_thread(shutil.rmtree, path)


async def _run_command(
    command: list[str],
    *,
    stdin: IO[bytes] | int | None = None,
) -> subprocess.CompletedProcess[bytes]:
    import asyncio

    return await asyncio.to_thread(
        subprocess.run,
        command,
        stdin=stdin if stdin is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _quote_remote_path(path: str) -> str:
    if path == "~":
        return "~"
    if path.startswith("~/"):
        return f"~/{shlex.quote(path.removeprefix('~/'))}"
    return shlex.quote(path)
