# WatchFS

Watch Files and Sync them to another directory

<p align="center">
   <a href="https://python.org/" target="_blank"><img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/watchfs?logo=python&style=flat-square"></a>
   <a href="https://pypi.org/project/watchfs/" target="_blank"><img src="https://img.shields.io/pypi/v/watchfs?style=flat-square" alt="pypi"></a>
   <a href="https://pypi.org/project/watchfs/" target="_blank"><img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/watchfs?style=flat-square"></a>
   <a href="LICENSE"><img alt="LICENSE" src="https://img.shields.io/github/license/ShigureLab/watchfs?style=flat-square"></a>
   <br/>
   <a href="https://github.com/astral-sh/uv"><img alt="uv" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json&style=flat-square"></a>
   <a href="https://github.com/astral-sh/ruff"><img alt="ruff" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=flat-square"></a>
   <a href="https://gitmoji.dev"><img alt="Gitmoji" src="https://img.shields.io/badge/gitmoji-%20😜%20😍-FFDD67?style=flat-square"></a>
</p>

## Installation

```bash
uv tool install watchfs
```

Python 3.12+ is required. CI tests Python 3.15 (including release candidates) and
free-threaded Python 3.15t on Linux x64 and macOS 26 arm64. Standard CPython 3.15 can
use watchfiles' ABI3 wheels; 3.15t currently builds watchfiles from source and
requires a Rust toolchain.

Known source-build limitation: on macOS 27 with Xcode 27, locally built watchfiles
can fail to import with `mis-aligned LINKEDIT string pool`. This also reproduces
on Python 3.14 and 3.14t; published wheels work. macOS 3.15t runtime validation
currently covers the macOS 26 CI runner, not this macOS 27 toolchain. See
[the compatibility investigation](https://github.com/ShigureLab/watchfs/pull/104)
for details.

## Usage

```bash
watchfs src1:dst1 src2:dst2
```

### SSH target

Use `SRC->DST` when the destination is a remote SSH directory:

```bash
watchfs ./src->meow@192.168.66.1:/tmp/watchfs-demo
```

Notes:

- Only local source to remote SSH destination is supported right now.
- SSH currently relies on your existing OpenSSH login setup, such as key-based auth or an already configured SSH environment.
- Bidirectional sync with an SSH target is not supported.
- Events are serialized per destination machine and can upload to different destination machines in parallel.
- Jump host / bastion support is planned and currently tracked as a TODO in the SSH backend.
