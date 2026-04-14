"""Verbosity level definitions for symbol filtering."""

from enum import IntEnum


class VerbosityLevel(IntEnum):
    """Verbosity levels for controlling symbol output.

    IntEnum allows natural ordering comparisons (>, >=).
    """

    NORMAL = 0
    VERBOSE = 1
    DEBUG = 2
