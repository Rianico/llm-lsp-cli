"""Language filter registry for managing per-language test filters."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from .pattern_engine import PatternSet, PatternSource

if TYPE_CHECKING:
    from llm_lsp_cli.config.schema import TestFilterConfig


class LanguageFilterRegistry:
    """Singleton registry for language-specific pattern sets.

    Provides lazy initialization and caching of PatternSet instances
    per language. Thread-safe for concurrent access.
    """

    _instance: LanguageFilterRegistry | None = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        """Initialize the registry."""
        self._filters: dict[str, PatternSet] = {}
        self._config: TestFilterConfig | None = None
        self._configured = False

    @classmethod
    def get_instance(cls) -> LanguageFilterRegistry:
        """Get the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def configure(self, config: TestFilterConfig) -> None:
        """Load configuration and clear cache.

        Args:
            config: TestFilterConfig with language-specific patterns
        """
        with self._lock:
            self._config = config
            self._filters.clear()
            self._configured = True

    def get_filter(self, language: str) -> PatternSet:
        """Get or create a filter for a language.

        Args:
            language: Language identifier (e.g., 'python', 'typescript')

        Returns:
            PatternSet for the language
        """
        with self._lock:
            if language in self._filters:
                return self._filters[language]

            pattern_set = self._create_filter_for_language(language)
            self._filters[language] = pattern_set
            return pattern_set

    def _create_filter_for_language(self, language: str) -> PatternSet:
        """Create a PatternSet for a language from configuration.

        Priority resolution:
        1. Language-specific config (if exists, use ONLY this - no merging)
        2. Defaults (if language has no specific config)
        3. Fallback (if no defaults)
        4. Empty PatternSet

        Args:
            language: Language identifier

        Returns:
            PatternSet with patterns for the language
        """
        if self._config is None:
            return PatternSet()

        # Priority 1: Language-specific config (exclusive - no merging)
        if language in self._config.languages:
            lang_config = self._config.languages[language]
            if lang_config.enabled:
                return PatternSet.from_language_config(lang_config, PatternSource.LANGUAGE_CONFIG)

        # Priority 2: Defaults
        if self._config.defaults and self._config.defaults.enabled:
            return PatternSet.from_language_config(self._config.defaults, PatternSource.DEFAULT)

        # Priority 3: Fallback
        if self._config.fallback:
            return PatternSet.from_language_config(self._config.fallback, PatternSource.DEFAULT)

        # Priority 4: Empty PatternSet
        return PatternSet()

    def reload_language(self, language: str) -> None:
        """Force reload of a single language's filter.

        Args:
            language: Language identifier to reload
        """
        with self._lock:
            self._filters.pop(language, None)

    def clear(self) -> None:
        """Clear all cached filters."""
        with self._lock:
            self._filters.clear()

    def list_languages(self) -> list[str]:
        """List all configured languages.

        Returns:
            List of language identifiers
        """
        with self._lock:
            if self._config is None:
                return []
            return list(self._config.languages.keys())


# Global registry instance accessor
def get_registry() -> LanguageFilterRegistry:
    """Get the global LanguageFilterRegistry instance."""
    return LanguageFilterRegistry.get_instance()
