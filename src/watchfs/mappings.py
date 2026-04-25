from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from watchfs.exceptions import ParseError
from watchfs.rusty import Err, Ok, Result

_SSH_TARGET_RE = re.compile(r"^(?:(?P<username>[^@/:]+)@)?(?P<host>[^:]+):(?P<path>(?:/.*|~(?:/.*)?))$")
_WINDOWS_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/].*$")
_WINDOWS_LEGACY_MAPPING_RE = re.compile(r"^(?P<src>[A-Za-z]:[\\/].*):(?P<dst>[A-Za-z]:[\\/].*)$")


@dataclass(frozen=True, slots=True)
class LocalTargetSpec:
    path: Path

    def display(self) -> str:
        return str(self.path)


@dataclass(frozen=True, slots=True)
class SshTargetSpec:
    host: str
    path: PurePosixPath
    username: str | None = None
    port: int = 22
    jump_host: str | None = None

    def authority(self) -> str:
        if self.username:
            return f"{self.username}@{self.host}"
        return self.host

    def display(self) -> str:
        if self.port == 22:
            return f"{self.authority()}:{self.path.as_posix()}"
        return f"ssh://{self.authority()}:{self.port}{self.path.as_posix()}"

    def credential_key(self) -> str:
        return f"{self.authority()}:{self.port}"


type TargetSpec = LocalTargetSpec | SshTargetSpec


@dataclass(frozen=True, slots=True)
class SyncMapping:
    source: Path
    target: TargetSpec

    def display(self) -> str:
        target = self.target.display()
        return f"{self.source} -> {target}"


def parse_target_spec(spec: str) -> Result[TargetSpec, ParseError]:
    if spec.startswith("ssh://"):
        return _parse_ssh_url(spec)

    if _WINDOWS_DRIVE_PATH_RE.fullmatch(spec):
        return Ok(LocalTargetSpec(Path(spec).expanduser()))

    if matched := _SSH_TARGET_RE.fullmatch(spec):
        path = matched.group("path")
        return Ok(
            SshTargetSpec(
                host=matched.group("host"),
                path=PurePosixPath(path),
                username=matched.group("username"),
            )
        )

    return Ok(LocalTargetSpec(Path(spec).expanduser()))


def parse_sync_mapping(sync_mapping: str) -> Result[tuple[SyncMapping, bool], ParseError]:
    match _split_sync_mapping(sync_mapping):
        case Err(err):
            return Err(err)
        case Ok((src_dir, dst_dir, bidirectional)):
            match parse_target_spec(src_dir):
                case Err(err):
                    return Err(err)
                case Ok(src_spec):
                    if isinstance(src_spec, SshTargetSpec):
                        return Err(ParseError("Remote source is not supported yet. Source must be a local path."))

            match parse_target_spec(dst_dir):
                case Err(err):
                    return Err(err)
                case Ok(dst_spec):
                    if isinstance(dst_spec, SshTargetSpec) and bidirectional:
                        return Err(
                            ParseError("Bidirectional sync is not supported when the destination is an SSH target.")
                        )

                    if isinstance(dst_spec, LocalTargetSpec):
                        abs_src_dir = src_spec.path.resolve()
                        abs_dst_dir = dst_spec.path.resolve()
                        if abs_src_dir in abs_dst_dir.parents:
                            return Err(
                                ParseError(f"dst_dir({abs_dst_dir}) is a subdirectory of src_dir({abs_src_dir}).")
                            )

                    return Ok((SyncMapping(source=src_spec.path, target=dst_spec), bidirectional))

    raise AssertionError("unreachable")


def _parse_ssh_url(spec: str) -> Result[SshTargetSpec, ParseError]:
    parsed = urlparse(spec)
    if parsed.scheme != "ssh" or not parsed.hostname:
        return Err(ParseError(f"Invalid SSH target: {spec}"))
    if not parsed.path.startswith("/"):
        return Err(ParseError("SSH target path must be absolute."))

    return Ok(
        SshTargetSpec(
            host=parsed.hostname,
            path=PurePosixPath(parsed.path),
            username=parsed.username,
            port=parsed.port or 22,
        )
    )


def _split_sync_mapping(sync_mapping: str) -> Result[tuple[str, str, bool], ParseError]:
    if "<->" in sync_mapping:
        src_dir, dst_dir = sync_mapping.split("<->", maxsplit=1)
        return _validate_split(sync_mapping, src_dir, dst_dir, bidirectional=True)

    if "->" in sync_mapping:
        src_dir, dst_dir = sync_mapping.split("->", maxsplit=1)
        return _validate_split(sync_mapping, src_dir, dst_dir, bidirectional=False)

    if matched := _WINDOWS_LEGACY_MAPPING_RE.fullmatch(sync_mapping):
        return _validate_split(
            sync_mapping,
            matched.group("src"),
            matched.group("dst"),
            bidirectional=False,
        )

    if sync_mapping.count(":") == 1:
        src_dir, dst_dir = sync_mapping.split(":", maxsplit=1)
        return _validate_split(sync_mapping, src_dir, dst_dir, bidirectional=False)

    return Err(ParseError("Invalid sync mapping. Use SRC->DST when the destination contains ':'."))


def _validate_split(
    sync_mapping: str,
    src_dir: str,
    dst_dir: str,
    *,
    bidirectional: bool,
) -> Result[tuple[str, str, bool], ParseError]:
    if not src_dir or not dst_dir:
        return Err(ParseError(f"Invalid sync mapping: {sync_mapping}"))

    return Ok((src_dir, dst_dir, bidirectional))
