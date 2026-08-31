"""Bounded, symlink-safe and atomic local file operations."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

from .errors import StorageError, ValidationError


def ensure_private_directory(path: Path) -> None:
    """Create an owned directory and keep it private."""

    if path.is_symlink():
        raise StorageError(f"refusing symlinked directory: {path.name}")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        info = path.stat()
    except OSError as exc:
        raise StorageError(f"cannot inspect directory: {path.name}") from exc
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise StorageError(f"directory is not privately owned: {path.name}")
    os.chmod(path, 0o700)


def refuse_symlink(path: Path) -> None:
    if path.is_symlink():
        raise StorageError(f"refusing symlinked target: {path.name}")


def read_bytes_bounded(path: Path, maximum: int) -> bytes:
    refuse_symlink(path)
    try:
        info = path.stat()
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise StorageError(f"cannot inspect file: {path.name}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise StorageError(f"not a regular file: {path.name}")
    if info.st_size > maximum:
        raise ValidationError(f"{path.name} exceeds {maximum} bytes")
    try:
        with path.open("rb") as handle:
            data = handle.read(maximum + 1)
    except OSError as exc:
        raise StorageError(f"cannot read file: {path.name}") from exc
    if len(data) > maximum:
        raise ValidationError(f"{path.name} exceeds {maximum} bytes")
    return data


def read_json_bounded(path: Path, maximum: int) -> Any:
    raw = read_bytes_bounded(path, maximum)
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{path.name} is not valid UTF-8 JSON") from exc


def canonical_json_bytes(value: Any, *, pretty: bool = True) -> bytes:
    if pretty:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    return text.encode("utf-8")


def atomic_write(path: Path, data: bytes, *, mode: int = 0o600) -> None:
    """Replace one regular file with flushed same-directory bytes."""

    ensure_private_directory(path.parent)
    refuse_symlink(path)
    if path.exists():
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise StorageError(f"target is not an owned regular file: {path.name}")

    descriptor = -1
    temporary = ""
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = ""
        os.chmod(path, mode)
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        raise StorageError(f"cannot atomically write: {path.name}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def atomic_write_json(path: Path, value: Any, *, mode: int = 0o600) -> None:
    atomic_write(path, canonical_json_bytes(value), mode=mode)
