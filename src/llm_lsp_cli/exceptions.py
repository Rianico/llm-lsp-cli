"""Exception hierarchy for llm-lsp-cli."""

from __future__ import annotations


class CLIError(Exception):
    """Base exception for CLI errors."""

    pass


class DaemonError(Exception):
    """Base exception for daemon-related errors.

    All daemon exceptions include workspace and language context for actionable error messages.
    Exceptions also include log_file path for debugging daemon failures.
    """

    def __init__(
        self,
        message: str,
        workspace: str | None = None,
        language: str | None = None,
        log_file: str | None = None,
    ):
        self.message = message
        self.workspace = workspace
        self.language = language
        self.log_file = log_file
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message with context."""
        context_parts = []
        if self.workspace:
            context_parts.append(f"workspace='{self.workspace}'")
        if self.language:
            context_parts.append(f"language='{self.language}'")

        context = f" [{', '.join(context_parts)}]" if context_parts else ""
        log_suffix = f" (log: {self.log_file})" if self.log_file else ""
        return f"{self.message}{context}{log_suffix}"


class DaemonStartupError(DaemonError):
    """Raised when daemon fails to start."""

    pass


class DaemonStartupTimeoutError(DaemonError):
    """Raised when daemon startup times out waiting for socket.

    Includes the socket path and timeout duration for debugging.
    """

    def __init__(
        self,
        socket_path: str,
        timeout: float,
        workspace: str | None = None,
        language: str | None = None,
        log_file: str | None = None,
    ):
        self.socket_path = socket_path
        self.timeout = timeout
        message = f"Daemon startup timed out after {timeout}s waiting for socket"
        super().__init__(message, workspace, language, log_file)

    def _format_message(self) -> str:
        """Format the timeout error message with socket path."""
        base_message = super()._format_message()
        return f"{base_message} (socket: {self.socket_path})"


class DaemonCrashedError(DaemonError):
    """Raised when daemon socket exists but connection fails.

    Indicates the daemon process crashed after creating the socket.
    """

    def __init__(
        self,
        socket_path: str,
        workspace: str | None = None,
        language: str | None = None,
        log_file: str | None = None,
    ):
        self.socket_path = socket_path
        message = "Daemon crashed - socket exists but connection failed"
        super().__init__(message, workspace, language, log_file)

    def _format_message(self) -> str:
        """Format the crash error message with socket path."""
        base_message = super()._format_message()
        return f"{base_message} (socket: {self.socket_path})"
