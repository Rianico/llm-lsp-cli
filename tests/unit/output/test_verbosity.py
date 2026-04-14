"""Unit tests for VerbosityLevel enum."""

from llm_lsp_cli.output.verbosity import VerbosityLevel


class TestVerbosityLevel:
    """Tests for VerbosityLevel IntEnum."""

    def test_normal_equals_zero(self) -> None:
        """Verify NORMAL level equals 0."""
        assert VerbosityLevel.NORMAL == 0

    def test_verbose_equals_one(self) -> None:
        """Verify VERBOSE level equals 1."""
        assert VerbosityLevel.VERBOSE == 1

    def test_debug_equals_two(self) -> None:
        """Verify DEBUG level equals 2."""
        assert VerbosityLevel.DEBUG == 2

    def test_verbose_greater_than_normal(self) -> None:
        """Verify VERBOSE > NORMAL using IntEnum ordering."""
        assert VerbosityLevel.VERBOSE > VerbosityLevel.NORMAL

    def test_debug_greater_than_verbose(self) -> None:
        """Verify DEBUG > VERBOSE using IntEnum ordering."""
        assert VerbosityLevel.DEBUG > VerbosityLevel.VERBOSE

    def test_from_int_zero(self) -> None:
        """Verify VerbosityLevel(0) returns NORMAL."""
        assert VerbosityLevel(0) == VerbosityLevel.NORMAL

    def test_from_int_one(self) -> None:
        """Verify VerbosityLevel(1) returns VERBOSE."""
        assert VerbosityLevel(1) == VerbosityLevel.VERBOSE

    def test_from_int_two(self) -> None:
        """Verify VerbosityLevel(2) returns DEBUG."""
        assert VerbosityLevel(2) == VerbosityLevel.DEBUG

    def test_int_enum_allows_comparison(self) -> None:
        """Verify IntEnum allows >= comparisons."""
        assert VerbosityLevel.VERBOSE >= VerbosityLevel.NORMAL
        assert VerbosityLevel.VERBOSE >= VerbosityLevel.VERBOSE
        assert VerbosityLevel.DEBUG >= VerbosityLevel.VERBOSE
