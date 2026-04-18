"""JSON-based server definition repository."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from llm_lsp_cli.domain.entities import ServerDefinition
from ..exceptions import ConfigWriteError

logger = logging.getLogger(__name__)

# Constants
LANGUAGES_KEY = "languages"


class JsonServerDefinitionRepository:
    """JSON file-based server definition repository.

    Implements ServerDefinitionRepository protocol for persistent storage.
    Uses lazy loading and thread-safe access.

    Attributes:
        config_file: Path to configuration JSON file
    """

    def __init__(self, config_file: Path) -> None:
        """Initialize repository.

        Args:
            config_file: Path to configuration JSON file
        """
        self._config_file = config_file
        self._cache: dict[str, ServerDefinition] | None = None
        self._lock = threading.Lock()

    def get(self, language_id: str) -> ServerDefinition | None:
        """Retrieve a server definition by language ID.

        Args:
            language_id: Language identifier (e.g., 'python')

        Returns:
            ServerDefinition if found, None otherwise
        """
        self._ensure_loaded()

        with self._lock:
            if self._cache is None:
                return None
            return self._cache.get(language_id)

    def list_all(self) -> list[ServerDefinition]:
        """List all registered server definitions.

        Returns:
            List of all ServerDefinition instances
        """
        self._ensure_loaded()

        with self._lock:
            if self._cache is None:
                return []
            return list(self._cache.values())

    def register(self, definition: ServerDefinition) -> None:
        """Register a new server definition.

        Args:
            definition: ServerDefinition to register
        """
        with self._lock:
            # Load current state
            data = self._load_data()

            # Update languages
            if LANGUAGES_KEY not in data:
                data[LANGUAGES_KEY] = {}

            data[LANGUAGES_KEY][definition.language_id] = {
                "command": definition.command,
                "args": definition.args,
                "timeout_seconds": definition.timeout_seconds,
            }

            # Persist
            self._save_data(data)

            # Invalidate cache
            self._cache = None

    def _ensure_loaded(self) -> None:
        """Ensure data is loaded (lazy loading with thread safety)."""
        if self._cache is not None:
            return

        with self._lock:
            if self._cache is not None:
                return

            data = self._load_data()
            self._cache = self._parse_definitions(data)

    def _load_data(self) -> dict[str, Any]:
        """Load raw JSON data from file."""
        if not self._config_file.exists():
            return {LANGUAGES_KEY: {}}

        try:
            content = self._config_file.read_text()
            return json.loads(content)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load config from %s: %s", self._config_file, e)
            return {LANGUAGES_KEY: {}}

    def _save_data(self, data: dict[str, Any]) -> None:
        """Save raw JSON data to file.

        Raises:
            ConfigWriteError: If the file cannot be written.
        """
        try:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            content = json.dumps(data, indent=2)
            self._config_file.write_text(content)
        except OSError as e:
            logger.error("Failed to save config to %s: %s", self._config_file, e)
            raise ConfigWriteError(
                str(self._config_file),
                f"Failed to save config: {e}"
            ) from e

    def _parse_definitions(
        self, data: dict[str, Any]
    ) -> dict[str, ServerDefinition]:
        """Parse server definitions from raw data.

        Args:
            data: Raw JSON data

        Returns:
            Dictionary of language_id -> ServerDefinition
        """
        result: dict[str, ServerDefinition] = {}

        languages = data.get(LANGUAGES_KEY, {})
        if not isinstance(languages, dict):
            return result

        for lang_id, config in languages.items():
            if not isinstance(config, dict):
                continue

            try:
                result[lang_id] = ServerDefinition(
                    language_id=lang_id,
                    command=config.get("command", ""),
                    args=config.get("args", []),
                    timeout_seconds=config.get("timeout_seconds", 30),
                )
            except (TypeError, ValueError) as e:
                logger.warning("Skipping invalid server definition for %s: %s", lang_id, e)
                continue

        return result
