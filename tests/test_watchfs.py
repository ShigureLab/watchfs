from __future__ import annotations

import tomllib
from pathlib import Path, PurePosixPath
from typing import cast

from watchfs import __version__
from watchfs.__main__ import build_queue_key
from watchfs.exceptions import ParseError
from watchfs.mappings import LocalTargetSpec, SshTargetSpec, parse_sync_mapping, parse_target_spec
from watchfs.rusty import Err, Ok, Result

with Path("pyproject.toml").open("rb") as f:
    project_info = tomllib.load(f)


def test_version():
    assert __version__ == project_info["project"]["version"]


def expect_ok[T](result: Result[T, Exception], message: str) -> T:
    assert isinstance(result, Ok), message
    return cast("Ok[T]", result).ok()


def expect_err[E: Exception](result: Result[object, E], message: str) -> E:
    assert isinstance(result, Err), message
    return cast("Err[E]", result).err()


def test_parse_local_mapping_with_arrow():
    mapping, bidirectional = expect_ok(parse_sync_mapping("src->dst"), "expected local mapping to parse")
    assert mapping.source == Path("src")
    assert mapping.target == LocalTargetSpec(Path("dst"))
    assert bidirectional is False


def test_parse_local_mapping_with_legacy_colon():
    mapping, bidirectional = expect_ok(parse_sync_mapping("src:dst"), "expected local legacy mapping to parse")
    assert mapping.source == Path("src")
    assert mapping.target == LocalTargetSpec(Path("dst"))
    assert bidirectional is False


def test_parse_windows_drive_paths_as_local_targets():
    target = expect_ok(parse_target_spec("C:/src"), "expected Windows drive path to parse as local")
    assert isinstance(target, LocalTargetSpec)
    assert target.path == Path("C:/src")


def test_parse_windows_local_mapping_with_arrow():
    mapping, bidirectional = expect_ok(parse_sync_mapping("C:/src->D:/dst"), "expected Windows arrow mapping to parse")
    assert mapping.source == Path("C:/src")
    assert mapping.target == LocalTargetSpec(Path("D:/dst"))
    assert bidirectional is False


def test_parse_windows_local_mapping_with_legacy_colon():
    mapping, bidirectional = expect_ok(
        parse_sync_mapping("C:/src:D:/dst"), "expected Windows legacy mapping to parse"
    )
    assert mapping.source == Path("C:/src")
    assert mapping.target == LocalTargetSpec(Path("D:/dst"))
    assert bidirectional is False


def test_parse_ssh_target_mapping():
    mapping, bidirectional = expect_ok(
        parse_sync_mapping("src->meow@192.168.66.1:/tmp/watchfs"), "expected ssh mapping to parse"
    )
    assert mapping.source == Path("src")
    assert mapping.target == SshTargetSpec(
        host="192.168.66.1",
        path=PurePosixPath("/tmp/watchfs"),
        username="meow",
    )
    assert bidirectional is False


def test_parse_ssh_target_mapping_with_home_path():
    mapping, bidirectional = expect_ok(
        parse_sync_mapping("~/Projects/watchfs->meow@192.168.66.1:~/Projects/watchfs"),
        "expected ssh home mapping to parse",
    )
    assert mapping.source == Path("~/Projects/watchfs").expanduser()
    assert mapping.target == SshTargetSpec(
        host="192.168.66.1",
        path=PurePosixPath("~/Projects/watchfs"),
        username="meow",
    )
    assert bidirectional is False


def test_parse_ssh_url_target_mapping():
    mapping, _ = expect_ok(parse_sync_mapping("src->ssh://meow@example.com:2222/tmp/watchfs"), "expected ssh url mapping to parse")
    assert mapping.target == SshTargetSpec(
        host="example.com",
        path=PurePosixPath("/tmp/watchfs"),
        username="meow",
        port=2222,
    )


def test_reject_remote_source():
    err = expect_err(parse_sync_mapping("meow@192.168.66.1:/tmp/src->dst"), "expected remote source to be rejected")
    assert isinstance(err, ParseError)
    assert "Remote source is not supported" in err.message


def test_reject_bidirectional_remote_mapping():
    err = expect_err(
        parse_sync_mapping("src<->meow@192.168.66.1:/tmp/watchfs"),
        "expected bidirectional ssh mapping to be rejected",
    )
    assert isinstance(err, ParseError)
    assert "Bidirectional sync is not supported" in err.message


def test_reject_local_destination_nested_under_source_message():
    err = expect_err(parse_sync_mapping("src:src/nested"), "expected nested local destination to be rejected")
    assert isinstance(err, ParseError)
    assert "dst_dir(" in err.message
    assert "is a subdirectory of src_dir(" in err.message


def test_reject_ambiguous_remote_mapping_without_arrow():
    err = expect_err(
        parse_sync_mapping("src:meow@192.168.66.1:/tmp/watchfs"),
        "expected ambiguous remote mapping to be rejected",
    )
    assert isinstance(err, ParseError)
    assert "Use SRC->DST" in err.message


def test_same_ssh_machine_shares_serial_queue_key():
    first_mapping, _ = expect_ok(
        parse_sync_mapping("src->meow@192.168.66.1:/tmp/watchfs-a"),
        "expected first ssh mapping to parse",
    )
    second_mapping, _ = expect_ok(
        parse_sync_mapping("src->meow@192.168.66.1:/tmp/watchfs-b"),
        "expected second ssh mapping to parse",
    )

    assert build_queue_key(first_mapping) == build_queue_key(second_mapping)


def test_different_ssh_machine_uses_different_queue_key():
    first_mapping, _ = expect_ok(
        parse_sync_mapping("src->meow@192.168.66.1:/tmp/watchfs-a"),
        "expected first ssh mapping to parse",
    )
    second_mapping, _ = expect_ok(
        parse_sync_mapping("src->meow@192.168.88.2:/tmp/watchfs-b"),
        "expected second ssh mapping to parse",
    )

    assert build_queue_key(first_mapping) != build_queue_key(second_mapping)
