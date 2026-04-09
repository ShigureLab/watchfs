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

```python
uv tool install watchfs
```

## Usage

```python
watchfs src1:dst1 src2:dst2
```

### SSH target

Use `SRC->DST` when the destination is a remote SSH directory:

```python
watchfs ./src->meow@192.168.66.1:/tmp/watchfs-demo
```

Notes:

- Only local source to remote SSH destination is supported right now.
- SSH currently relies on your existing OpenSSH login setup, such as key-based auth or an already configured SSH environment.
- Bidirectional sync with an SSH target is not supported.
- Events are serialized per destination machine and can upload to different destination machines in parallel.
- Jump host / bastion support is planned and currently tracked as a TODO in the SSH backend.
