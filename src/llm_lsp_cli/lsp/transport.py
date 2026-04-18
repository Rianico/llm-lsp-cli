"""LSP stdio transport layer."""

import asyncio
import contextlib
import inspect
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .constants import LSPConstants

# Default timeouts and delays
_STABILIZATION_DELAY = 0.05

logger = logging.getLogger(__name__)


class StdioTransport:
    """Transport layer for LSP communication over stdio."""

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        trace: bool = False,
        log_file: Path | None = None,
    ):
        self.command = command
        self.args = args or []
        self.cwd = cwd
        self.env = env
        self.trace = trace
        self.log_file = log_file

        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._notification_handlers: dict[str, Callable[..., Any]] = {}
        self._request_handlers: dict[str, Callable[..., Any]] = {}
        self._read_task: asyncio.Task[Any] | None = None
        self._stderr_task: asyncio.Task[Any] | None = None
        self._running = False
        self._log_fh: Any = None

    async def start(self) -> None:
        """Start the LSP server process.

        Verifies that the process starts successfully and doesn't exit immediately.

        Raises:
            RuntimeError: If the LSP server command is not found, permission is denied,
                or the process exits immediately with an error.
        """
        cmd = [self.command] + self.args

        logger.info(f"Starting LSP server: {' '.join(cmd)}")

        # Open log file if specified
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            self._log_fh = open(self.log_file, "a")  # noqa: SIM115

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

                # Log to file if available, otherwise to logger
                if self._log_fh:
                    self._log_fh.write(line.decode("utf-8", errors="replace"))
                    self._log_fh.flush()
                else:
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

                    logger.debug(f"Reading body of {content_length} bytes")

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
            logger.debug(f"<-- {data}")

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
            logger.debug(f"--> {payload}")

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

        # Close log file handle
        if self._log_fh:
            self._log_fh.close()
            self._log_fh = None

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
