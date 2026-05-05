"""Type stubs for lockfile package."""

from typing import contextmanager
from types import TracebackType


class LockBase:
    """Base class for platform-specific lock files."""

    def __init__(self, path: str, threaded: bool = True) -> None: ...

    def acquire(self, timeout: float | None = None) -> None:
        """Acquire the lock."""
        ...

    def release(self) -> None:
        """Release the lock."""
        ...

    def locked(self) -> bool:
        """Return whether the lock is currently held."""
        ...

    def is_locked(self) -> bool:
        """Return whether the lock is currently held."""
        ...

    def break_lock(self) -> None:
        """Break an existing lock."""
        ...

    def __enter__(self) -> "LockBase": ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...


class LockTimeout(OSError):
    """Raised when a lock cannot be acquired within the timeout."""
    ...


class AlreadyLocked(LockTimeout):
    """Raised when a lock is already held by another process."""
    ...


class LockFailed(OSError):
    """Raised when a lock cannot be acquired."""
    ...


class UnlockFailed(OSError):
    """Raised when a lock cannot be released."""
    ...
