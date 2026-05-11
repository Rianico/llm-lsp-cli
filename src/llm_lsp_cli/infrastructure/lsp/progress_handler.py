"""Progress handler for LSP work done progress.

This module handles LSP response data (dict[str, object]).
LSP responses are inherently dynamic, so object is used for dict value types.
"""

import logging
from collections.abc import Callable
from typing import cast

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

    def handle_progress(self, params: dict[str, object]) -> None:
        """Handle $/progress notification."""
        token_val = params.get("token", "")
        token = str(token_val) if token_val is not None else ""
        value_raw = params.get("value", {})

        if not isinstance(value_raw, dict):
            return

        value = cast(dict[str, object], value_raw)

        # Check if this is work done progress (has 'kind' field)
        if "kind" not in value:
            # Partial result progress (e.g., workspace diagnostics)
            # Delegate to diagnostic manager or other handlers
            return

        kind_val = value.get("kind", "")
        kind = str(kind_val) if kind_val is not None else ""

        if kind == "begin":
            self._handle_begin(token, value)
        elif kind == "report":
            self._handle_report(token, value)
        elif kind == "end":
            self._handle_end(token)

    def _handle_begin(self, token: str, value: dict[str, object]) -> None:
        """Handle progress begin notification."""
        title_raw = value.get("title", "")
        message_raw = value.get("message", "")
        percentage_raw = value.get("percentage", 0)
        cancellable_raw = value.get("cancellable", False)

        state = WorkDoneProgressState(
            token=token,
            title=str(title_raw) if title_raw is not None else "",
            message=str(message_raw) if message_raw is not None else "",
            percentage=int(percentage_raw) if isinstance(percentage_raw, (int, float)) else 0,
            cancellable=bool(cancellable_raw),
            started=True,
        )
        self._progress_states[token] = state
        logger.info(f"Work started: {state.title} - {state.message} ({state.percentage}%)")
        self._notify_callbacks(state)

    def _handle_report(self, token: str, value: dict[str, object]) -> None:
        """Handle progress report notification."""
        if token not in self._progress_states:
            logger.warning(f"Progress report for unknown token: {token}")
            return

        state = self._progress_states[token]
        # Create new state instance (immutability)
        message_raw = value.get("message", state.message)
        percentage_raw = value.get("percentage", state.percentage)

        updated_state = WorkDoneProgressState(
            token=state.token,
            title=state.title,
            message=str(message_raw) if message_raw is not None else state.message,
            percentage=int(percentage_raw) if isinstance(percentage_raw, (int, float)) else state.percentage,
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
