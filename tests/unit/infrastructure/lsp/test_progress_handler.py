"""Tests for ProgressHandler."""

import pytest
from llm_lsp_cli.domain.progress import WorkDoneProgressState
from llm_lsp_cli.infrastructure.lsp.progress_handler import ProgressHandler


class TestProgressHandler:
    """Test cases for ProgressHandler."""

    def test_handle_begin_creates_state(self) -> None:
        """Test that handling begin notification creates progress state."""
        handler = ProgressHandler()
        params = {
            "token": "test-token",
            "value": {
                "kind": "begin",
                "title": "Indexing workspace",
                "message": "Starting analysis",
                "percentage": 0,
                "cancellable": True,
            },
        }

        handler.handle_progress(params)
        state = handler.get_state("test-token")

        assert state is not None
        assert state.token == "test-token"
        assert state.title == "Indexing workspace"
        assert state.message == "Starting analysis"
        assert state.percentage == 0
        assert state.cancellable is True
        assert state.started is True
        assert state.completed is False

    def test_handle_begin_with_defaults(self) -> None:
        """Test that begin notification uses defaults for missing fields."""
        handler = ProgressHandler()
        params = {
            "token": "minimal-token",
            "value": {
                "kind": "begin",
            },
        }

        handler.handle_progress(params)
        state = handler.get_state("minimal-token")

        assert state is not None
        assert state.title == ""
        assert state.message == ""
        assert state.percentage == 0
        assert state.cancellable is False

    def test_handle_report_updates_state(self) -> None:
        """Test that handling report notification updates progress state."""
        handler = ProgressHandler()

        # First, start the progress
        handler.handle_progress(
            {
                "token": "report-token",
                "value": {
                    "kind": "begin",
                    "title": "Processing",
                    "message": "Starting",
                    "percentage": 0,
                },
            }
        )

        # Then send a report
        handler.handle_progress(
            {
                "token": "report-token",
                "value": {
                    "kind": "report",
                    "message": "Halfway done",
                    "percentage": 50,
                },
            }
        )

        state = handler.get_state("report-token")
        assert state is not None
        assert state.message == "Halfway done"
        assert state.percentage == 50
        assert state.title == "Processing"  # Unchanged
        assert state.started is True
        assert state.completed is False

    def test_handle_report_partial_update(self) -> None:
        """Test that report only updates provided fields."""
        handler = ProgressHandler()

        # Start progress
        handler.handle_progress(
            {
                "token": "partial-token",
                "value": {
                    "kind": "begin",
                    "title": "Task",
                    "message": "Initial message",
                    "percentage": 10,
                },
            }
        )

        # Report with only message (no percentage)
        handler.handle_progress(
            {
                "token": "partial-token",
                "value": {
                    "kind": "report",
                    "message": "Updated message",
                },
            }
        )

        state = handler.get_state("partial-token")
        assert state is not None
        assert state.message == "Updated message"
        assert state.percentage == 10  # Should retain previous value

    def test_handle_report_for_unknown_token(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that report for unknown token logs warning."""
        handler = ProgressHandler()

        handler.handle_progress(
            {
                "token": "unknown-token",
                "value": {
                    "kind": "report",
                    "message": "This should warn",
                },
            }
        )

        assert "unknown token" in caplog.text.lower()

    def test_handle_end_completes_progress(self) -> None:
        """Test that handling end notification completes progress."""
        handler = ProgressHandler()

        # Start progress
        handler.handle_progress(
            {
                "token": "end-token",
                "value": {
                    "kind": "begin",
                    "title": "Finishing Task",
                    "message": "Working",
                },
            }
        )

        # End progress
        handler.handle_progress(
            {
                "token": "end-token",
                "value": {
                    "kind": "end",
                },
            }
        )

        # State should be removed from active states
        state = handler.get_state("end-token")
        assert state is None

    def test_handle_end_logs_completion(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that end notification logs completion."""
        handler = ProgressHandler()

        # Set log level to INFO to capture info-level logs
        import logging

        logger = logging.getLogger("llm_lsp_cli.infrastructure.lsp.progress_handler")
        logger.setLevel(logging.INFO)

        handler.handle_progress(
            {
                "token": "log-token",
                "value": {
                    "kind": "begin",
                    "title": "Logged Task",
                    "message": "Running",
                },
            }
        )

        handler.handle_progress(
            {
                "token": "log-token",
                "value": {
                    "kind": "end",
                },
            }
        )

        assert "Work completed" in caplog.text
        assert "Logged Task" in caplog.text

    def test_handle_non_dict_value_returns_early(self) -> None:
        """Test that non-dict values are ignored."""
        handler = ProgressHandler()

        # Should not raise
        handler.handle_progress(
            {
                "token": "test",
                "value": "not a dict",
            }
        )

        assert handler.get_all_states() == {}

    def test_handle_progress_without_kind_returns_early(self) -> None:
        """Test that progress without 'kind' field is ignored (partial results)."""
        handler = ProgressHandler()

        # This is a partial result progress, not work done progress
        handler.handle_progress(
            {
                "token": "partial",
                "value": {
                    "items": [{"uri": "file://test.py", "diagnostics": []}],
                },
            }
        )

        # Should not create any state
        assert handler.get_all_states() == {}

    def test_register_callback_is_notified(self) -> None:
        """Test that registered callbacks are notified on state changes."""
        handler = ProgressHandler()
        callback_states: list[WorkDoneProgressState] = []

        def callback(state: WorkDoneProgressState) -> None:
            callback_states.append(state)

        handler.register_callback(callback)

        handler.handle_progress(
            {
                "token": "callback-token",
                "value": {
                    "kind": "begin",
                    "title": "Callback Test",
                    "message": "Starting",
                    "percentage": 0,
                },
            }
        )

        assert len(callback_states) == 1
        assert callback_states[0].title == "Callback Test"
        assert callback_states[0].started is True

    def test_callback_is_notified_on_report(self) -> None:
        """Test that callbacks are notified on report."""
        handler = ProgressHandler()
        callback_states: list[WorkDoneProgressState] = []

        handler.register_callback(lambda s: callback_states.append(s))

        # Begin
        handler.handle_progress(
            {
                "token": "report-callback-token",
                "value": {
                    "kind": "begin",
                    "title": "Report Test",
                    "message": "Start",
                    "percentage": 0,
                },
            }
        )

        # Report
        handler.handle_progress(
            {
                "token": "report-callback-token",
                "value": {
                    "kind": "report",
                    "message": "Progress",
                    "percentage": 50,
                },
            }
        )

        assert len(callback_states) == 2
        assert callback_states[1].message == "Progress"
        assert callback_states[1].percentage == 50

    def test_callback_is_notified_on_end(self) -> None:
        """Test that callbacks are notified on end."""
        handler = ProgressHandler()
        callback_states: list[WorkDoneProgressState] = []

        handler.register_callback(lambda s: callback_states.append(s))

        # Begin
        handler.handle_progress(
            {
                "token": "end-callback-token",
                "value": {
                    "kind": "begin",
                    "title": "End Test",
                },
            }
        )

        # End
        handler.handle_progress(
            {
                "token": "end-callback-token",
                "value": {
                    "kind": "end",
                },
            }
        )

        # Should have begin and end notifications
        assert len(callback_states) == 2
        assert callback_states[0].started is True
        # The end callback marks the state as completed before notification

    def test_callback_error_does_not_crash_handler(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that callback errors don't crash the handler."""
        handler = ProgressHandler()

        def bad_callback(state: WorkDoneProgressState) -> None:
            raise RuntimeError("Callback error")

        handler.register_callback(bad_callback)

        # Should not raise
        handler.handle_progress(
            {
                "token": "error-token",
                "value": {
                    "kind": "begin",
                    "title": "Error Test",
                },
            }
        )

        assert "Progress callback error" in caplog.text

    def test_get_all_states_returns_copy(self) -> None:
        """Test that get_all_states returns a copy."""
        handler = ProgressHandler()

        handler.handle_progress(
            {
                "token": "token-1",
                "value": {"kind": "begin", "title": "Task 1"},
            }
        )
        handler.handle_progress(
            {
                "token": "token-2",
                "value": {"kind": "begin", "title": "Task 2"},
            }
        )

        states = handler.get_all_states()
        assert len(states) == 2
        assert "token-1" in states
        assert "token-2" in states

        # Modifying returned dict should not affect internal state
        states["token-3"] = WorkDoneProgressState(token="token-3")
        assert handler.get_all_states() == {
            "token-1": handler.get_state("token-1"),
            "token-2": handler.get_state("token-2"),
        }

    def test_full_lifecycle(self) -> None:
        """Test complete begin -> report -> end lifecycle."""
        handler = ProgressHandler()
        events: list[str] = []

        handler.register_callback(lambda s: events.append(f"{s.percentage}%"))

        # Begin
        handler.handle_progress(
            {
                "token": "lifecycle-token",
                "value": {
                    "kind": "begin",
                    "title": "Lifecycle Test",
                    "message": "Starting",
                    "percentage": 0,
                },
            }
        )
        assert len(events) == 1
        assert events[0] == "0%"

        # Report 1
        handler.handle_progress(
            {
                "token": "lifecycle-token",
                "value": {
                    "kind": "report",
                    "message": "Working",
                    "percentage": 50,
                },
            }
        )
        assert len(events) == 2
        assert events[1] == "50%"

        # Report 2
        handler.handle_progress(
            {
                "token": "lifecycle-token",
                "value": {
                    "kind": "report",
                    "message": "Almost done",
                    "percentage": 90,
                },
            }
        )
        assert len(events) == 3
        assert events[2] == "90%"

        # End
        handler.handle_progress(
            {
                "token": "lifecycle-token",
                "value": {
                    "kind": "end",
                },
            }
        )
        # State should be removed
        assert handler.get_state("lifecycle-token") is None


class TestWorkDoneProgressState:
    """Test cases for WorkDoneProgressState dataclass."""

    def test_create_with_required_fields_only(self) -> None:
        """Test creating state with only token."""
        state = WorkDoneProgressState(token="test-token")

        assert state.token == "test-token"
        assert state.title == ""
        assert state.message == ""
        assert state.percentage == 0
        assert state.cancellable is False
        assert state.started is False
        assert state.completed is False

    def test_create_with_all_fields(self) -> None:
        """Test creating state with all fields."""
        state = WorkDoneProgressState(
            token="full-token",
            title="Full Title",
            message="Full Message",
            percentage=75,
            cancellable=True,
            started=True,
            completed=False,
        )

        assert state.token == "full-token"
        assert state.title == "Full Title"
        assert state.message == "Full Message"
        assert state.percentage == 75
        assert state.cancellable is True
        assert state.started is True
        assert state.completed is False

    def test_immutability_pattern(self) -> None:
        """Test that state updates create new instances."""
        # Dataclasses are mutable by default, but ProgressHandler
        # should create new instances on updates (immutability pattern)
        handler = ProgressHandler()

        handler.handle_progress(
            {
                "token": "immut-token",
                "value": {
                    "kind": "begin",
                    "title": "Immutability Test",
                    "message": "Start",
                    "percentage": 0,
                },
            }
        )

        state1 = handler.get_state("immut-token")
        assert state1 is not None

        handler.handle_progress(
            {
                "token": "immut-token",
                "value": {
                    "kind": "report",
                    "percentage": 50,
                },
            }
        )

        state2 = handler.get_state("immut-token")
        assert state2 is not None

        # Handler creates new instances, so state1 and state2 should be different objects
        # Note: Dataclasses are mutable, so we check that the handler replaced the reference
        assert state1 is not state2
        assert state1.percentage == 0
        assert state2.percentage == 50
