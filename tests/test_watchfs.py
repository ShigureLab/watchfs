from __future__ import annotations

import tomllib
from pathlib import Path, PurePosixPath

from watchfs import __version__
from watchfs.__main__ import build_queue_key
from watchfs.mappings import LocalTargetSpec, SshTargetSpec, parse_sync_mapping
from watchfs.rusty import Err, Ok

with Path("pyproject.toml").open("rb") as f:
    project_info = tomllib.load(f)


def test_version():
    assert __version__ == project_info["project"]["version"]


def test_parse_local_mapping_with_arrow():
    match parse_sync_mapping("src->dst"):
        case Ok((mapping, bidirectional)):
            assert mapping.source == Path("src")
            assert mapping.target == LocalTargetSpec(Path("dst"))
            assert bidirectional is False
        case _:
            raise AssertionError("expected local mapping to parse")


def test_parse_local_mapping_with_legacy_colon():
    match parse_sync_mapping("src:dst"):
        case Ok((mapping, bidirectional)):
            assert mapping.source == Path("src")
            assert mapping.target == LocalTargetSpec(Path("dst"))
            assert bidirectional is False
        case _:
            raise AssertionError("expected local legacy mapping to parse")


def test_parse_ssh_target_mapping():
    match parse_sync_mapping("src->meow@192.168.66.1:/tmp/watchfs"):
        case Ok((mapping, bidirectional)):
            assert mapping.source == Path("src")
            assert mapping.target == SshTargetSpec(
                host="192.168.66.1",
                path=PurePosixPath("/tmp/watchfs"),
                username="meow",
            )
            assert bidirectional is False
        case _:
            raise AssertionError("expected ssh mapping to parse")


def test_parse_ssh_target_mapping_with_home_path():
    match parse_sync_mapping("~/Projects/watchfs->meow@192.168.66.1:~/Projects/watchfs"):
        case Ok((mapping, bidirectional)):
            assert mapping.source == Path("~/Projects/watchfs").expanduser()
            assert mapping.target == SshTargetSpec(
                host="192.168.66.1",
                path=PurePosixPath("~/Projects/watchfs"),
                username="meow",
            )
            assert bidirectional is False
        case _:
            raise AssertionError("expected ssh home mapping to parse")


def test_parse_ssh_url_target_mapping():
    match parse_sync_mapping("src->ssh://meow@example.com:2222/tmp/watchfs"):
        case Ok((mapping, _)):
            assert mapping.target == SshTargetSpec(
                host="example.com",
                path=PurePosixPath("/tmp/watchfs"),
                username="meow",
                port=2222,
            )
        case _:
            raise AssertionError("expected ssh url mapping to parse")


def test_reject_remote_source():
    match parse_sync_mapping("meow@192.168.66.1:/tmp/src->dst"):
        case Err(err):
            assert "Remote source is not supported" in err.message
        case _:
            raise AssertionError("expected remote source to be rejected")


def test_reject_bidirectional_remote_mapping():
    match parse_sync_mapping("src<->meow@192.168.66.1:/tmp/watchfs"):
        case Err(err):
            assert "Bidirectional sync is not supported" in err.message
        case _:
            raise AssertionError("expected bidirectional ssh mapping to be rejected")


def test_reject_ambiguous_remote_mapping_without_arrow():
    match parse_sync_mapping("src:meow@192.168.66.1:/tmp/watchfs"):
        case Err(err):
            assert "Use SRC->DST" in err.message
        case _:
            raise AssertionError("expected ambiguous remote mapping to be rejected")


def test_same_ssh_machine_shares_serial_queue_key():
    match parse_sync_mapping("src->meow@192.168.66.1:/tmp/watchfs-a"):
        case Ok((first_mapping, _)):
            pass
        case _:
            raise AssertionError("expected first ssh mapping to parse")

    match parse_sync_mapping("src->meow@192.168.66.1:/tmp/watchfs-b"):
        case Ok((second_mapping, _)):
            pass
        case _:
            raise AssertionError("expected second ssh mapping to parse")

    assert build_queue_key(first_mapping) == build_queue_key(second_mapping)


def test_different_ssh_machine_uses_different_queue_key():
    match parse_sync_mapping("src->meow@192.168.66.1:/tmp/watchfs-a"):
        case Ok((first_mapping, _)):
            pass
        case _:
            raise AssertionError("expected first ssh mapping to parse")

    match parse_sync_mapping("src->meow@192.168.88.2:/tmp/watchfs-b"):
        case Ok((second_mapping, _)):
            pass
        case _:
            raise AssertionError("expected second ssh mapping to parse")

    assert build_queue_key(first_mapping) != build_queue_key(second_mapping)
