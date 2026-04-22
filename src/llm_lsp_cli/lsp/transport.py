"""LSP stdio transport layer."""

import asyncio
import contextlib
import copy
import inspect
import json
import logging
from collections.abc import Callable
from enum import Enum, auto
from typing import Any

from .constants import LSPConstants

# =============================================================================
# TRACE Level Definition
# =============================================================================

# Custom logging level for transport-layer messages (more verbose than DEBUG)
#
# NOTE: TRACE_LEVEL = 5 follows the Python logging convention for custom levels.
# Python's built-in levels are: CRITICAL=50, ERROR=40, WARNING=30, INFO=20, DEBUG=10.
# Custom TRACE level is set to 5 (below DEBUG=10) to ensure it is filtered when
# DEBUG threshold is active, but visible when explicitly enabled.
#
# This is separate from LogLevel.TRACE = 4 in the domain layer, which uses a
# 0-4 scale for ordering purposes in business logic, not Python logging levels.
TRACE_LEVEL = 5

# Register TRACE level name with Python logging
logging.addLevelName(TRACE_LEVEL, "TRACE")

# Default timeouts and delays
_STABILIZATION_DELAY = 0.05

# Logger names
_DIAGNOSTIC_LOGGER_NAME = "llm_lsp_cli.lsp.diagnostic"

logger = logging.getLogger(__name__)
_diagnostic_logger = logging.getLogger(_DIAGNOSTIC_LOGGER_NAME)


# =============================================================================
# Three-way log classification
# =============================================================================


class LogCategory(Enum):
    """LSP method log routing category."""

    SKIP = auto()   # Skip daemon.log; log full to diagnostics.log only
    DAEMON = auto() # Log full to daemon.log only; skip diagnostics.log
    MASK = auto()   # Log masked to daemon.log; log full to diagnostics.log


_SKIP_METHODS = frozenset({
    LSPConstants.PROGRESS,
})

_DAEMON_ONLY_METHODS = frozenset({
    LSPConstants.WINDOW_LOG_MESSAGE,
    "workspace/configuration",  # LSP request, not in LSPConstants
    LSPConstants.CLIENT_REGISTER_CAPABILITY,
})


def _classify_method(method: str) -> LogCategory:
    """Classify an LSP method into its log routing category.

    Every string input returns exactly one LogCategory. Default is MASK.
    """
    if method in _SKIP_METHODS:
        return LogCategory.SKIP
    if method in _DAEMON_ONLY_METHODS:
        return LogCategory.DAEMON
    return LogCategory.MASK


def _mask_array(target: dict[str, Any], key: str, mask_description: str = "array") -> None:
    """Mask an array field in a dictionary with length metadata.

    Mutates the target dictionary in place.

    Args:
        target: Dictionary to modify
        key: Key of the array field to mask
        mask_description: Description for the mask (used in logging)
    """
    if key in target and isinstance(target[key], list):
        target[key] = f"... ({mask_description}_len: {len(target[key])})"


def _mask_progress_items(params: dict[str, Any]) -> None:
    """Mask items array in $/progress notification params.

    Mutates params in place.

    Args:
        params: Progress notification params dictionary
    """
    if not isinstance(params, dict) or "value" not in params:
        return

    value = params["value"]
    if not isinstance(value, dict) or "items" not in value:
        return

    _mask_array(value, "items", "array")


def _mask_diagnostics_params(params: dict[str, Any]) -> None:
    """Mask diagnostics array in textDocument/publishDiagnostics params.

    Mutates params in place.

    Args:
        params: Publish diagnostics params dictionary
    """
    if not isinstance(params, dict) or "diagnostics" not in params:
        return

    _mask_array(params, "diagnostics", "array")


def _mask_result_items(result_data: dict[str, Any]) -> None:
    """Mask items array in result dictionary.

    Mutates result_data in place.

    Args:
        result_data: Result dictionary from LSP response
    """
    if not isinstance(result_data, dict) or "items" not in result_data:
        return

    _mask_array(result_data, "items", "array")


def _mask_text_content(params: dict[str, Any]) -> None:
    """Mask text content fields in document synchronization params.

    Mutates the params dict in place (called on deep-copied data only).

    Handles:
    - textDocument/didOpen: params.textDocument.text
    - textDocument/didChange: params.contentChanges[].text
    """
    if not isinstance(params, dict):
        return

    # textDocument/didOpen: params.textDocument.text
    text_doc = params.get("textDocument")
    if isinstance(text_doc, dict) and "text" in text_doc:
        text = text_doc["text"]
        if isinstance(text, str):
            text_doc["text"] = f"... (text_len: {len(text)})"

    # textDocument/didChange: params.contentChanges[].text
    content_changes = params.get("contentChanges")
    if isinstance(content_changes, list):
        for change in content_changes:
            if isinstance(change, dict) and "text" in change:
                text = change["text"]
                if isinstance(text, str):
                    change["text"] = f"... (text_len: {len(text)})"


def _mask_diagnostics(data: dict[str, Any]) -> dict[str, Any]:
    """Mask diagnostic arrays in LSP messages to prevent log bloat.

    Creates a deep copy to avoid mutating the input data.
    Replaces diagnostic arrays with length metadata string.

    Patterns handled:
    - $/progress notifications with params.value.items[].diagnostics
    - textDocument/publishDiagnostics with params.diagnostics
    - Diagnostic responses with result.items

    Args:
        data: LSP message dictionary

    Returns:
        New dictionary with diagnostic arrays masked
    """
    # Deep copy to preserve immutability
    result = copy.deepcopy(data)

    method = result.get("method", "")

    # Handle $/progress notifications
    if method == "$/progress":
        _mask_progress_items(result.get("params", {}))

    # Handle textDocument/publishDiagnostics notifications
    elif method == "textDocument/publishDiagnostics":
        _mask_diagnostics_params(result.get("params", {}))

    # Handle textDocument/didOpen and didChange
    elif method in (
        LSPConstants.TEXT_DOCUMENT_DID_OPEN,
        LSPConstants.TEXT_DOCUMENT_DID_CHANGE,
    ):
        _mask_text_content(result.get("params", {}))

    # Handle diagnostic responses with result.items
    if "result" in result:
        _mask_result_items(result["result"])

    return result


class StdioTransport:
    """Transport layer for LSP communication over stdio."""

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        trace: bool = False,
    ):
        self.command = command
        self.args = args or []
        self.cwd = cwd
        self.env = env
        self.trace = trace

        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._notification_handlers: dict[str, Callable[..., Any]] = {}
        self._request_handlers: dict[str, Callable[..., Any]] = {}
        self._read_task: asyncio.Task[Any] | None = None
        self._stderr_task: asyncio.Task[Any] | None = None
        self._running = False

    async def start(self) -> None:
        """Start the LSP server process.

        Verifies that the process starts successfully and doesn't exit immediately.

        Raises:
            RuntimeError: If the LSP server command is not found, permission is denied,
                or the process exits immediately with an error.
        """
        cmd = [self.command] + self.args

        logger.info(f"Starting LSP server: {' '.join(cmd)}")

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
                env=self._merge_env(),
            )
        except FileNotFoundError as e:
            logger.error(f"LSP server command not found: {self.command}")
            raise RuntimeError(
                f"LSP server command not found: {self.command}. "
                f"Ensure the server is installed and in PATH."
            ) from e
        except PermissionError as e:
            logger.error(f"Permission denied executing LSP server: {self.command}")
            raise RuntimeError(
                f"Permission denied executing LSP server: {self.command}. Check file permissions."
            ) from e

        # Check if process exited immediately (crash on startup)
        if self._process.returncode is not None:
            # Process exited immediately - read stderr for error message
            stderr_output = b""
            if self._process.stderr:
                try:
                    stderr_output = await asyncio.wait_for(
                        self._process.stderr.read(),
                        timeout=2.0,
                    )
                except asyncio.TimeoutError:
                    stderr_output = b"(stderr read timeout)"

            stderr_text = stderr_output.decode("utf-8", errors="replace").strip()
            logger.error(
                f"LSP server exited immediately with code {self._process.returncode}. "
                f"Stderr: {stderr_text}"
            )
            raise RuntimeError(
                f"LSP server exited immediately with code {self._process.returncode}. "
                f"Error: {stderr_text}"
            )

        self._running = True

        # Small stabilization delay after process start
        await asyncio.sleep(_STABILIZATION_DELAY)

        self._read_task = asyncio.create_task(self._read_loop())
        self._stderr_task = asyncio.create_task(self._stderr_loop())

        logger.debug("LSP server started")

    def _merge_env(self) -> dict[str, str]:
        """Merge environment variables."""
        import os

        env = os.environ.copy()
        if self.env:
            env.update(self.env)
        return env

    async def _stderr_loop(self) -> None:
        """Read and log stderr output from the LSP server.

        Runs as a background task while the transport is active.
        """
        if self._process is None or self._process.stderr is None:
            return

        try:
            while self._running:
                line = await self._process.stderr.readline()
                if not line:
                    break

                # Log to logger at debug level
                logger.debug(f"LSP stderr: {line.decode('utf-8', errors='replace').strip()}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception(f"Error in stderr loop: {e}")

    async def _read_loop(self) -> None:
        """Read and process messages from the LSP server."""
        assert self._process is not None
        assert self._process.stdout is not None

        buffer = b""

        try:
            while self._running:
                # Read Content-Length header
                header_line = await self._process.stdout.readline()
                if not header_line:
                    logger.debug("Read loop: stdout closed (EOF)")
                    break

                buffer += header_line

                # Check for end of headers
                if header_line == b"\r\n":
                    # Parse content length from accumulated buffer
                    content_length = self._parse_content_length(buffer)
                    if content_length is None:
                        logger.error(f"Failed to parse Content-Length from: {buffer!r}")
                        buffer = b""
                        continue

                    logger.log(TRACE_LEVEL, f"Reading body of {content_length} bytes")

                    # Read body
                    try:
                        body = await self._process.stdout.readexactly(content_length)
                    except asyncio.IncompleteReadError as e:
                        logger.error(
                            f"Incomplete read: expected {content_length}, got {e.partial!r}"
                        )
                        buffer = b""
                        break

                    buffer = b""

                    # Process message
                    await self._handle_message(body)

        except asyncio.CancelledError:
            logger.debug("Read loop cancelled")
            pass
        except Exception as e:
            logger.exception(f"Error in read loop: {e}")

    def _parse_content_length(self, header_data: bytes) -> int | None:
        """Parse Content-Length from header data."""
        try:
            headers = header_data.decode("utf-8").split("\r\n")
            for header in headers:
                if header.startswith("Content-Length: "):
                    return int(header.split(": ")[1])
        except (ValueError, UnicodeDecodeError, IndexError):
            pass
        return None

    async def _handle_message(self, body: bytes) -> None:
        """Handle a received message."""
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse message: {e}")
            return

        if self.trace:
            method = data.get("method", "")
            category = _classify_method(method)

            if category == LogCategory.SKIP:
                # Only log to diagnostics.log (full)
                _diagnostic_logger.debug(f"<-- {data}")
            elif category == LogCategory.DAEMON:
                # Only log to daemon.log (full, not masked)
                logger.debug(f"<-- {data}")
            elif category == LogCategory.MASK:
                # Dual-path: masked to daemon.log, full to diagnostics.log
                masked_data = _mask_diagnostics(data)
                logger.debug(f"<-- {masked_data}")
                _diagnostic_logger.debug(f"<-- {data}")

        # Route message
        if "id" in data:
            if "method" in data:
                # Request from server
                await self._handle_request(data)
            else:
                # Response to our request
                await self._handle_response(data)
        elif "method" in data:
            # Notification from server
            await self._handle_notification(data)

    async def _handle_response(self, data: dict[str, Any]) -> None:
        """Handle a response to our request."""
        request_id = data.get("id")
        if request_id not in self._pending:
            logger.warning(f"Received response for unknown request: {request_id}")
            return

        future = self._pending.pop(request_id)
        if not future.done():
            if "error" in data:
                future.set_exception(LSPError(data["error"]))
            else:
                future.set_result(data.get("result"))

    async def _handle_request(self, data: dict[str, Any]) -> None:
        """Handle a request from the server."""
        request_id = data.get("id")
        if request_id is None:
            return

        method = data.get("method", "unknown")
        params = data.get("params", {})

        handler: Callable | None = self._request_handlers.get(method)  # type: ignore

        if handler is None:
            # No handler registered - send method not found error
            logger.debug(f"No handler for request: {method}")
            return

        # Call the registered handler
        try:
            if inspect.iscoroutinefunction(handler):
                result = await handler(params)
            else:
                result = handler(params)

            # Send successful response
            await self._send_payload(
                {
                    "jsonrpc": LSPConstants.JSONRPC_VERSION,
                    "id": request_id,
                    "result": result,
                }
            )
        except Exception as e:
            # Send error response
            await self._send_payload(
                {
                    "jsonrpc": LSPConstants.JSONRPC_VERSION,
                    "id": request_id,
                    "error": {
                        "code": LSPConstants.ERROR_INTERNAL_ERROR,
                        "message": str(e),
                    },
                }
            )

    async def _handle_notification(self, data: dict[str, Any]) -> None:
        """Handle a notification from the server."""
        method = data.get("method", "")
        params = data.get("params", {})

        handler: Callable | None = self._notification_handlers.get(method)  # type: ignore
        if handler:
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(params)
                else:
                    handler(params)
            except Exception as e:
                logger.exception(f"Error in notification handler: {e}")
        elif self.trace:
            logger.debug(f"No handler for notification: {method}")

    def on_notification(self, method: str, handler: Callable[..., Any]) -> None:
        """Register a notification handler."""
        self._notification_handlers[method] = handler

    def on_request(self, method: str, handler: Callable[..., Any]) -> None:
        """Register a server->client request handler."""
        self._request_handlers[method] = handler

    async def send_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> Any:
        """Send a request and wait for response."""
        assert self._process is not None, "Transport not started"
        assert self._process.stdin is not None, "Stdin not available"

        self._request_id += 1
        request_id = self._request_id

        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending[request_id] = future

        await self._send_payload(
            {
                "jsonrpc": LSPConstants.JSONRPC_VERSION,
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(request_id, None)
            raise TimeoutError(f"Request timed out: {method}") from None

    async def send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Send a notification (no response expected)."""
        assert self._process is not None, "Transport not started"

        await self._send_payload(
            {
                "jsonrpc": LSPConstants.JSONRPC_VERSION,
                "method": method,
                "params": params or {},
            }
        )

    async def send_request_fire_and_forget(
        self, method: str, params: dict[str, Any] | None = None
    ) -> None:
        """Send a request without waiting for response (fire-and-forget).

        Use this for requests like workspace/diagnostic that never resolve with data
        and instead send results via $/progress notifications.

        The request is sent with an ID (so it's a valid request), but no Future is
        created to wait for a response. The server will eventually cancel the request
        when a new one comes in or when the server shuts down.
        """
        assert self._process is not None, "Transport not started"

        self._request_id += 1
        request_id = self._request_id

        await self._send_payload(
            {
                "jsonrpc": LSPConstants.JSONRPC_VERSION,
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )
        # Note: We don't create a Future here since the server never resolves
        # this request - it stays pending until cancelled or server shutdown.

    async def _send_payload(self, payload: dict[str, Any]) -> None:
        """Send a JSON-RPC payload."""
        assert self._process is not None
        assert self._process.stdin is not None

        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode()

        if self.trace:
            masked_payload = _mask_diagnostics(payload)
            logger.debug(f"--> {masked_payload}")

        self._process.stdin.write(header + body)
        await self._process.stdin.drain()

    async def stop(self) -> None:
        """Stop the transport and kill the process."""
        self._running = False

        # Cancel read task
        if self._read_task:
            self._read_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._read_task

        # Cancel stderr task
        if self._stderr_task:
            self._stderr_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._stderr_task

        # Close stdin
        if self._process and self._process.stdin:
            self._process.stdin.close()

        # Wait for process to exit
        if self._process:
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                # Kill if not exiting
                self._process.kill()
                await self._process.wait()

        # Clear pending
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()


class LSPError(Exception):
    """LSP protocol error."""

    def __init__(self, error_data: dict[str, Any]):
        self.code = error_data.get("code", -1)
        self.message = error_data.get("message", "Unknown error")
        self.data = error_data.get("data")
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"LSP Error {self.code}: {self.message}"
