"""Tests for FileState dataclass with mtime field.

These tests verify the refactored FileState structure:
- mtime field is present and is the first field
- diagnostics_version field is removed
"""

import pytest

from llm_lsp_cli.lsp.cache import FileState


class TestFileStateMtime:
    """Tests for FileState mtime field."""

    def test_default_mtime_is_zero(self) -> None:
        """Default mtime should be 0.0 (sentinel for untracked file)."""
        state = FileState()
        assert state.mtime == 0.0

    def test_mtime_can_be_set(self) -> None:
        """mtime can be set via constructor."""
        mtime_value = 1713765123.456789
        state = FileState(mtime=mtime_value)
        assert state.mtime == mtime_value

    def test_no_diagnostics_version_field(self) -> None:
        """diagnostics_version field should NOT exist after refactor."""
        state = FileState()
        assert not hasattr(state, "diagnostics_version")

    def test_mtime_is_first_field(self) -> None:
        """mtime should be the first field in FileState for visibility."""
        field_names = list(FileState.__dataclass_fields__.keys())
        assert field_names[0] == "mtime", (
            f"Expected 'mtime' as first field, got: {field_names}"
        )

    def test_mtime_with_nanosecond_precision(self) -> None:
        """mtime should support nanosecond precision values."""
        # Value from st_mtime_ns converted to seconds
        mtime_ns_as_seconds = 1713765123456789012 / 1e9
        state = FileState(mtime=mtime_ns_as_seconds)
        assert state.mtime == mtime_ns_as_seconds

    def test_other_fields_preserved(self) -> None:
        """Other FileState fields should still work."""
        state = FileState(
            mtime=100.0,
            document_version=5,
            last_result_id="result-123",
            is_open=True,
            diagnostics=[{"message": "test"}],
            uri="file:///test.py",
        )
        assert state.document_version == 5
        assert state.last_result_id == "result-123"
        assert state.is_open is True
        assert len(state.diagnostics) == 1
        assert state.uri == "file:///test.py"
