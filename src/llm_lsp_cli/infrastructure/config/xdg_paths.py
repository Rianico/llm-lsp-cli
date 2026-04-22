"""XDG directory paths with lazy initialization."""

from __future__ import annotations

import contextlib
import os
import threading
from pathlib import Path


class XdgPaths:
    """Thread-safe lazy initialization of XDG directories.

    Replaces module-level eager initialization with on-demand creation.
    Uses double-checked locking for singleton pattern.

    Attributes:
        config_dir: XDG_CONFIG_HOME/llm-lsp-cli
        state_dir: XDG_STATE_HOME/llm-lsp-cli
        runtime_dir: XDG_RUNTIME_DIR/llm-lsp-cli
    """

    _instance: XdgPaths | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        """Initialize XDG paths (called once by get())."""
        # Store full paths including llm-lsp-cli subdirectory
        self._config_dir = self._resolve_config_home() / "llm-lsp-cli"
        self._state_dir = self._resolve_state_home() / "llm-lsp-cli"
        self._runtime_dir = self._resolve_runtime_dir() / "llm-lsp-cli"

        # Create directories
        self._ensure_directory(self._config_dir)
        self._ensure_directory(self._state_dir)
        self._ensure_directory(self._runtime_dir)

    @classmethod
    def get(cls) -> XdgPaths:
        """Get singleton instance with lazy initialization.

        Thread-safe using double-checked locking.

        Returns:
            XdgPaths: Singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_for_testing(cls) -> None:
        """Reset singleton instance for testing.

        This allows tests to override environment variables and get fresh initialization.
        """
        with cls._lock:
            cls._instance = None

    @staticmethod
    def _resolve_config_home() -> Path:
        """Resolve XDG_CONFIG_HOME with fallback."""
        env_val = os.environ.get("XDG_CONFIG_HOME")
        if env_val:
            return Path(env_val)
        return Path.home() / ".config"

    @staticmethod
    def _resolve_state_home() -> Path:
        """Resolve XDG_STATE_HOME with fallback."""
        env_val = os.environ.get("XDG_STATE_HOME")
        if env_val:
            return Path(env_val)
        return Path.home() / ".local" / "state"

    @staticmethod
    def _resolve_runtime_dir() -> Path:
        """Resolve XDG_RUNTIME_DIR with fallback chain.

        Fallback chain:
        1. $XDG_RUNTIME_DIR
        2. $TMPDIR
        3. /tmp
        """
        env_val = os.environ.get("XDG_RUNTIME_DIR")
        if env_val:
            return Path(env_val)

        env_val = os.environ.get("TMPDIR")
        if env_val:
            return Path(env_val)

        return Path("/tmp")

    @staticmethod
    def _ensure_directory(path: Path, mode: int = 0o700) -> None:
        """Ensure directory exists with specified permissions.

        Args:
            path: Directory path to create/validate
            mode: Permission mode (default 0o700)
        """
        path.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            path.chmod(mode)

    @property
    def config_dir(self) -> Path:
        """Get config directory (XDG_CONFIG_HOME/llm-lsp-cli)."""
        return self._config_dir

    @property
    def state_dir(self) -> Path:
        """Get state directory (XDG_STATE_HOME/llm-lsp-cli)."""
        return self._state_dir

    @property
    def runtime_dir(self) -> Path:
        """Get runtime directory (XDG_RUNTIME_DIR/llm-lsp-cli)."""
        return self._runtime_dir
