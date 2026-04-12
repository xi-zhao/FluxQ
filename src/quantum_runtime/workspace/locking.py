"""Workspace-scoped mutation locks."""

from __future__ import annotations

import json
import os
import secrets
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, PrivateAttr, ValidationError


LOCK_FILENAME = ".workspace.lock"


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class WorkspaceLock(BaseModel):
    """Lease metadata for the active workspace writer."""

    pid: int
    hostname: str
    command: str
    started_at: str
    lock_path: str
    lease_id: str

    _released: bool = PrivateAttr(default=False)

    def __enter__(self) -> "WorkspaceLock":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: Any,
    ) -> None:
        self.release()

    def release(self) -> None:
        """Release the workspace lease if it is still ours."""
        if self._released:
            return

        lock_path = Path(self.lock_path)
        try:
            current = _read_lock(lock_path)
        except FileNotFoundError:
            current = None

        if current is None or current.lease_id == self.lease_id:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

        self._released = True


class WorkspaceLockConflict(RuntimeError):
    """Raised when another process already holds the workspace lease."""

    code = "workspace_lock_conflict"

    def __init__(self, holder: WorkspaceLock):
        self.holder = holder
        self.lock_path = holder.lock_path
        super().__init__(self.__str__())

    @property
    def details(self) -> dict[str, Any]:
        return {
            "pid": self.holder.pid,
            "hostname": self.holder.hostname,
            "command": self.holder.command,
            "started_at": self.holder.started_at,
            "lock_path": self.lock_path,
        }

    def __str__(self) -> str:
        return json.dumps(
            {
                "error_code": self.code,
                "details": self.details,
            },
            ensure_ascii=True,
        )


def acquire_workspace_lock(root: Path, *, command: str | None = None) -> WorkspaceLock:
    """Acquire the exclusive workspace writer lease."""
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / LOCK_FILENAME

    lock = WorkspaceLock(
        pid=os.getpid(),
        hostname=socket.gethostname(),
        command=command or " ".join(sys.argv),
        started_at=_timestamp(),
        lock_path=str(lock_path),
        lease_id=secrets.token_hex(8),
    )

    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as exc:
        raise WorkspaceLockConflict(_read_lock_or_placeholder(lock_path)) from exc

    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(lock.model_dump_json(indent=2))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
        raise

    return lock


def _read_lock(lock_path: Path) -> WorkspaceLock:
    payload = lock_path.read_text(encoding="utf-8")
    return WorkspaceLock.model_validate_json(payload)


def _read_lock_or_placeholder(lock_path: Path) -> WorkspaceLock:
    try:
        return _read_lock(lock_path)
    except (FileNotFoundError, OSError, ValidationError, json.JSONDecodeError):
        return WorkspaceLock(
            pid=-1,
            hostname="unknown",
            command="unknown",
            started_at="unknown",
            lock_path=str(lock_path),
            lease_id="unknown",
        )
