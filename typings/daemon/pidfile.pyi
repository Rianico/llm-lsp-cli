"""
Type stub file for daemon.pidfile module.

This module provides PIDLockFile and TimeoutPIDLockFile for daemon process locking.
"""

from typing import TracebackType


class PIDLockFile:
    """Lockfile behavior implemented via Unix PID files."""

    def __init__(self, path: str, threaded: bool = True) -> None:
        """Initialize a PID-based lock file.

        Args:
            path: Path to the PID file.
            threaded: Whether to use thread-level locking.
        """
        ...

    def read_pid(self) -> int | None:
        """Read the PID from the lock file.

        Returns:
            The PID if the lock is held, None otherwise.
        """
        ...

    def get_pid(self) -> int | None:
        """Get the PID currently holding the lock.

        Returns:
            The PID if the lock is held, None otherwise.
        """
        ...

    def is_locked(self) -> bool:
        """Check if the lock is currently held.

        Returns:
            True if the lock is held, False otherwise.
        """
        ...

    def acquire(self, timeout: float | None = None) -> None:
        """Acquire the lock.

        Args:
            timeout: Maximum time to wait for the lock (None = wait forever).

        Raises:
            LockTimeout: If the lock cannot be acquired within the timeout.
        """
        ...

    def release(self) -> None:
        """Release the lock."""
        ...

    def break_lock(self) -> None:
        """Break an existing lock."""
        ...

    def locked(self) -> bool:
        """Return whether the lock is currently held."""
        ...

    def __enter__(self) -> "PIDLockFile": ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...


class TimeoutPIDLockFile(PIDLockFile):
    """Lockfile with default timeout, implemented as a Unix PID file."""

    def __init__(
        self,
        path: str,
        acquire_timeout: float = -1,
        threaded: bool = True,
    ) -> None:
        """Initialize a PID-based lock file with default timeout.

        Args:
            path: Path to the PID file.
            acquire_timeout: Default timeout for acquire operations.
            threaded: Whether to use thread-level locking.
        """
        ...

    def acquire(self, timeout: float | None = None) -> None:
        """Acquire the lock with optional timeout override.

        Args:
            timeout: Maximum time to wait (uses acquire_timeout if not specified).
        """
        ...


__all__ = ["PIDLockFile", "TimeoutPIDLockFile"]
