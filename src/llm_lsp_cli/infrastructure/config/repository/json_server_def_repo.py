"""JSON-based server definition repository.

This module handles LSP response data (dict[str, object]).
LSP responses are inherently dynamic, so object is used for dict value types.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import cast

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

    _config_file: Path
    _cache: dict[str, ServerDefinition] | None
    _lock: threading.Lock

    def __init__(self, config_file: Path) -> None:
        """Initialize repository.

        Args:
            config_file: Path to configuration JSON file
        """
        self._config_file = config_file
        self._cache = None
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

            # Update languages - need to handle nested dict structure
            languages_raw = data.get(LANGUAGES_KEY, {})
            if not isinstance(languages_raw, dict):
                languages_raw = {}
            # Create new languages dict with the updated entry
            new_languages: dict[str, object] = {}
            languages_dict = cast(dict[object, object], languages_raw)
            for k, v in languages_dict.items():
                if isinstance(k, str):
                    new_languages[k] = v
            new_languages[definition.language_id] = {
                "command": definition.command,
                "args": definition.args,
                "timeout_seconds": definition.timeout_seconds,
            }
            data[LANGUAGES_KEY] = new_languages

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

    def _load_data(self) -> dict[str, object]:
        """Load raw JSON data from file."""
        if not self._config_file.exists():
            return {LANGUAGES_KEY: {}}

        try:
            content = self._config_file.read_text()
            # json.loads returns Any, so we cast to object for type safety
            loaded = cast(object, json.loads(content))
            if isinstance(loaded, dict):
                return cast(dict[str, object], loaded)
            return {LANGUAGES_KEY: {}}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load config from %s: %s", self._config_file, e)
            return {LANGUAGES_KEY: {}}

    def _save_data(self, data: dict[str, object]) -> None:
        """Save raw JSON data to file.

        Raises:
            ConfigWriteError: If the file cannot be written.
        """
        try:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            content = json.dumps(data, indent=2)
            _ = self._config_file.write_text(content)
        except OSError as e:
            logger.error("Failed to save config to %s: %s", self._config_file, e)
            raise ConfigWriteError(
                str(self._config_file),
                f"Failed to save config: {e}"
            ) from e

    def _parse_definitions(
        self, data: dict[str, object]
    ) -> dict[str, ServerDefinition]:
        """Parse server definitions from raw data.

        Args:
            data: Raw JSON data

        Returns:
            Dictionary of language_id -> ServerDefinition
        """
        result: dict[str, ServerDefinition] = {}

        languages_raw = data.get(LANGUAGES_KEY, {})
        if not isinstance(languages_raw, dict):
            return result

        # Cast after isinstance check
        languages = cast(dict[object, object], languages_raw)

        for lang_id, config in languages.items():
            if not isinstance(lang_id, str) or not isinstance(config, dict):
                continue

            try:
                # Cast config to dict[str, object] after isinstance check
                config_dict = cast(dict[str, object], config)
                command_val = config_dict.get("command", "")
                args_val = config_dict.get("args", [])
                timeout_val = config_dict.get("timeout_seconds", 30)
                # Type-narrow args_val
                args_list: list[str] = []
                if isinstance(args_val, list):
                    args_typed = cast(list[object], args_val)
                    for arg in args_typed:
                        if isinstance(arg, str):
                            args_list.append(arg)
                result[lang_id] = ServerDefinition(
                    language_id=lang_id,
                    command=str(command_val) if command_val else "",
                    args=args_list,
                    timeout_seconds=int(timeout_val) if isinstance(timeout_val, (int, float)) else 30,
                )
            except (TypeError, ValueError) as e:
                logger.warning("Skipping invalid server definition for %s: %s", lang_id, e)
                continue

        return result
