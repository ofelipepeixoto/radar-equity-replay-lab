"""POSIX filesystem access with directory handles and no-follow traversal."""
from __future__ import annotations

import os
import stat
from contextlib import contextmanager
from pathlib import Path

from .core import InvalidInput, MAX_BYTES


def _reject():
    raise InvalidInput("Invalid synthetic replay input or file")


@contextmanager
def _parent(path):
    # The handles pin each traversed directory; no symlink component is followed.
    if os.name != "posix" or any(not isinstance(getattr(os, flag, None), int) or getattr(os, flag, 0) <= 0 for flag in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")) or os.open not in os.supports_dir_fd:
        _reject()
    path = os.fspath(path)
    if not isinstance(path, str) or not path or "\x00" in path:
        _reject()
    absolute = path.startswith("/")
    parts = path.split("/")
    if absolute:
        parts = parts[1:]
    if not parts or any(part in {"", ".", ".."} for part in parts):
        _reject()
    descriptor = os.open("/" if absolute else ".", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            next_descriptor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        yield descriptor, parts[-1]
    finally:
        os.close(descriptor)


def read_input(path: str | Path) -> bytes:
    try:
        with _parent(path) as (parent, name):
            descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            try:
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_size <= MAX_BYTES:
                    _reject()
                chunks, total = [], 0
                while True:
                    chunk = os.read(descriptor, min(65536, MAX_BYTES + 1 - total))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_BYTES:
                        _reject()
                    chunks.append(chunk)
                return b"".join(chunks)
            finally:
                os.close(descriptor)
    except (OSError, TypeError, ValueError):
        _reject()


def write_report(path: str | Path, raw: bytes) -> None:
    try:
        with _parent(path) as (parent, name):
            descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            try:
                position = 0
                while position < len(raw):
                    written = os.write(descriptor, raw[position:])
                    if written == 0:
                        _reject()
                    position += written
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    except (OSError, TypeError, ValueError):
        _reject()
