"""Progress handler for LSP work done progress."""

import logging
from collections.abc import Callable
from typing import Any

from llm_lsp_cli.domain.progress import WorkDoneProgressState

logger = logging.getLogger(__name__)


class ProgressHandler:
    """
    Handles LSP work done progress notifications.

    Responsible for:
    - Parsing begin/report/end progress kinds
    - Maintaining progress state per token
    - Notifying registered callbacks on state changes
    """

    def __init__(self) -> None:
        self._progress_states: dict[str, WorkDoneProgressState] = {}
        self._callbacks: list[Callable[[WorkDoneProgressState], None]] = []

    def handle_progress(self, params: dict[str, Any]) -> None:
        """Handle $/progress notification."""
        token = params.get("token", "")
        value = params.get("value", {})

        if not isinstance(value, dict):
            return

        # Check if this is work done progress (has 'kind' field)
        if "kind" not in value:
            # Partial result progress (e.g., workspace diagnostics)
            # Delegate to diagnostic manager or other handlers
            return

        kind = value.get("kind", "")

        if kind == "begin":
            self._handle_begin(token, value)
        elif kind == "report":
            self._handle_report(token, value)
        elif kind == "end":
            self._handle_end(token)

    def _handle_begin(self, token: str, value: dict[str, Any]) -> None:
        """Handle progress begin notification."""
        state = WorkDoneProgressState(
            token=token,
            title=value.get("title", ""),
            message=value.get("message", ""),
            percentage=value.get("percentage", 0),
            cancellable=value.get("cancellable", False),
            started=True,
        )
        self._progress_states[token] = state
        logger.info(f"Work started: {state.title} - {state.message} ({state.percentage}%)")
        self._notify_callbacks(state)

    def _handle_report(self, token: str, value: dict[str, Any]) -> None:
        """Handle progress report notification."""
        if token not in self._progress_states:
            logger.warning(f"Progress report for unknown token: {token}")
            return

        state = self._progress_states[token]
        # Create new state instance (immutability)
        updated_state = WorkDoneProgressState(
            token=state.token,
            title=state.title,
            message=value.get("message", state.message),
            percentage=value.get("percentage", state.percentage),
            cancellable=state.cancellable,
            started=state.started,
            completed=state.completed,
        )
        self._progress_states[token] = updated_state
        logger.debug(f"Progress: {updated_state.message} ({updated_state.percentage}%)")
        self._notify_callbacks(updated_state)

    def _handle_end(self, token: str) -> None:
        """Handle progress end notification."""
        if token in self._progress_states:
            state = self._progress_states[token]
            # Mark as completed before notifying
            state.completed = True
            logger.info(f"Work completed: {state.title}")
            self._notify_callbacks(state)
            del self._progress_states[token]

    def register_callback(self, callback: Callable[[WorkDoneProgressState], None]) -> None:
        """Register a callback for progress state changes."""
        self._callbacks.append(callback)

    def _notify_callbacks(self, state: WorkDoneProgressState) -> None:
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(state)
            except Exception as e:
                logger.exception(f"Progress callback error: {e}")

    def get_state(self, token: str) -> WorkDoneProgressState | None:
        """Get current state for a token."""
        return self._progress_states.get(token)

    def get_all_states(self) -> dict[str, WorkDoneProgressState]:
        """Get all active progress states."""
        return dict(self._progress_states)
