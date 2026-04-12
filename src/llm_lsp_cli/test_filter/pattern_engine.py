"""Pattern matching engine for glob-based test filtering."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from llm_lsp_cli.config.schema import LanguageTestFilterConfig


class PatternSource(Enum):
    """Source of a pattern (for tracking and debugging)."""

    DEFAULT = "default"
    LANGUAGE_CONFIG = "language_config"
    USER_OVERRIDE = "user_override"


class MatchResult(NamedTuple):
    """Result of pattern matching."""

    is_match: bool
    matched_pattern: str | None = None
    source: PatternSource | None = None
    pattern_type: str | None = None


@dataclass
class CompiledPattern:
    """A compiled glob pattern for efficient matching."""

    pattern: str
    pattern_lower: str
    source: PatternSource
    is_negation: bool = False

    def match_path(self, path_str: str) -> bool:
        """Match against a full path string.

        Args:
            path_str: Path string to match (e.g., '/project/tests/test.py')

        Returns:
            True if the pattern matches the path
        """
        if not path_str:
            return False

        path_lower = path_str.lower()

        if self.pattern_lower.startswith("**"):
            return self._match_globstar_path(path_lower)
        return self._fnmatch_path(path_lower, self.pattern_lower)

    def _match_globstar_path(self, path_lower: str) -> bool:
        """Match a ** (globstar) pattern against a path.

        ** matches any number of directory levels.
        """
        remaining = self.pattern_lower[2:]
        if remaining.startswith("/"):
            remaining = remaining[1:]

        parts = path_lower.split("/")
        return any(self._fnmatch_path("/".join(parts[i:]), remaining) for i in range(len(parts)))

    def _fnmatch_path(self, path: str, pattern: str) -> bool:
        """Use fnmatch to match a pattern against a path.

        Handles ** as matching any path segment.
        """
        pattern_parts = pattern.split("/")
        path_parts = path.split("/")
        return self._match_segments(path_parts, pattern_parts)

    def _match_segments(self, path_parts: list[str], pattern_parts: list[str]) -> bool:
        """Recursively match path segments against pattern segments."""
        if not pattern_parts:
            return not path_parts

        if not path_parts:
            return all(p == "**" for p in pattern_parts)

        pattern = pattern_parts[0]

        if pattern == "**":
            if self._match_segments(path_parts, pattern_parts[1:]):
                return True
            return self._match_segments(path_parts[1:], pattern_parts)

        if fnmatch.fnmatch(path_parts[0], pattern):
            return self._match_segments(path_parts[1:], pattern_parts[1:])
        return False

    def match_filename(self, filename: str) -> bool:
        """Match against a filename only (not full path).

        Args:
            filename: Filename to match (e.g., 'test_main.py')

        Returns:
            True if the pattern matches the filename
        """
        if not filename:
            return False

        return fnmatch.fnmatch(filename.lower(), self.pattern_lower)


@dataclass
class PatternSet:
    """A set of patterns for a single language."""

    _directory_patterns: list[CompiledPattern] = field(default_factory=list)
    _suffix_patterns: list[CompiledPattern] = field(default_factory=list)
    _prefix_patterns: list[CompiledPattern] = field(default_factory=list)
    _include_patterns: list[CompiledPattern] = field(default_factory=list)

    def add_directory_pattern(
        self, pattern: str, source: PatternSource = PatternSource.DEFAULT
    ) -> None:
        """Add a directory pattern.

        Args:
            pattern: Glob pattern string
            source: Source of the pattern
        """
        self._directory_patterns.append(
            CompiledPattern(pattern=pattern, pattern_lower=pattern.lower(), source=source)
        )

    def add_suffix_pattern(
        self, pattern: str, source: PatternSource = PatternSource.DEFAULT
    ) -> None:
        """Add a suffix pattern.

        Args:
            pattern: Glob pattern string (e.g., '_test.py')
            source: Source of the pattern
        """
        # Suffix patterns need to match the end of filename
        # Convert '_test.py' to '*_test.py' for fnmatch
        if not pattern.startswith("*"):
            pattern = "*" + pattern
        self._suffix_patterns.append(
            CompiledPattern(pattern=pattern, pattern_lower=pattern.lower(), source=source)
        )

    def add_prefix_pattern(
        self, pattern: str, source: PatternSource = PatternSource.DEFAULT
    ) -> None:
        """Add a prefix pattern.

        Args:
            pattern: Glob pattern string (e.g., 'test_')
            source: Source of the pattern
        """
        # Prefix patterns need to match the start of filename
        # Convert 'test_' to 'test_*' for fnmatch
        if not pattern.endswith("*"):
            pattern = pattern + "*"
        self._prefix_patterns.append(
            CompiledPattern(pattern=pattern, pattern_lower=pattern.lower(), source=source)
        )

    def add_include_pattern(
        self, pattern: str, source: PatternSource = PatternSource.DEFAULT
    ) -> None:
        """Add an include (negation) pattern.

        These patterns explicitly exclude files from test classification.

        Args:
            pattern: Glob pattern string
            source: Source of the pattern
        """
        self._include_patterns.append(
            CompiledPattern(
                pattern=pattern, pattern_lower=pattern.lower(), source=source, is_negation=True
            )
        )

    def match(self, uri: str) -> MatchResult:
        """Match a URI against all patterns.

        Matching priority:
        1. Include patterns (negation) - if matched, return NOT a test
        2. Directory patterns - if matched, return IS a test
        3. Suffix patterns - if matched, return IS a test
        4. Prefix patterns - if matched, return IS a test
        5. Default: NOT a test

        Args:
            uri: LSP URI string (e.g., 'file:///path/to/file.py')

        Returns:
            MatchResult with is_match and metadata
        """
        if not uri:
            return MatchResult(is_match=False)

        # Extract path component from URI
        path_str = uri[7:] if uri.startswith("file://") else uri
        path_lower = path_str.lower()

        # Extract filename
        try:
            from pathlib import Path

            filename = Path(path_str).name
        except (ValueError, OSError):
            filename = path_str.split("/")[-1] if "/" in path_str else path_str

        # Priority 1: Check include (negation) patterns first
        for pattern in self._include_patterns:
            if pattern.match_path(path_lower):
                return MatchResult(
                    is_match=False,
                    matched_pattern=pattern.pattern,
                    source=pattern.source,
                    pattern_type="include",
                )

        # Priority 2: Check directory patterns
        for pattern in self._directory_patterns:
            if pattern.match_path(path_lower):
                return MatchResult(
                    is_match=True,
                    matched_pattern=pattern.pattern,
                    source=pattern.source,
                    pattern_type="directory",
                )

        # Priority 3: Check suffix patterns
        for pattern in self._suffix_patterns:
            if pattern.match_filename(filename.lower()):
                return MatchResult(
                    is_match=True,
                    matched_pattern=pattern.pattern,
                    source=pattern.source,
                    pattern_type="suffix",
                )

        # Priority 4: Check prefix patterns
        for pattern in self._prefix_patterns:
            if pattern.match_filename(filename.lower()):
                return MatchResult(
                    is_match=True,
                    matched_pattern=pattern.pattern,
                    source=pattern.source,
                    pattern_type="prefix",
                )

        # Priority 5: Default - not a test
        return MatchResult(is_match=False)

    @classmethod
    def from_language_config(
        cls, config: LanguageTestFilterConfig, source: PatternSource = PatternSource.DEFAULT
    ) -> PatternSet:
        """Create a PatternSet from a language configuration.

        Args:
            config: LanguageTestFilterConfig with pattern lists
            source: PatternSource to attribute patterns to

        Returns:
            PatternSet with all patterns loaded
        """
        pattern_set = cls()

        for pattern in config.directory_patterns:
            pattern_set.add_directory_pattern(pattern, source)

        for pattern in config.suffix_patterns:
            pattern_set.add_suffix_pattern(pattern, source)

        for pattern in config.prefix_patterns:
            pattern_set.add_prefix_pattern(pattern, source)

        for pattern in config.include_patterns:
            pattern_set.add_include_pattern(pattern, source)

        return pattern_set
