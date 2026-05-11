"""Configuration file loader with validation.

This module handles LSP response data (dict[str, object]).
LSP responses are inherently dynamic, so object is used for dict value types.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import cast

import yaml

from llm_lsp_cli.infrastructure.config.exceptions import (
    ConfigFileNotFoundError,
    ConfigParseError,
    ConfigValidationError,
)


class ConfigLoader:
    """Configuration file I/O with schema validation.

    Handles loading, saving, and validating JSON configuration files.
    Expands environment variables in configuration values.
    """

    @classmethod
    def load(cls, path: Path, defaults: dict[str, object] | None = None) -> dict[str, object]:
        """Load configuration from file.

        Supports both JSON and YAML formats based on file extension.

        Args:
            path: Path to configuration file
            defaults: Optional default values for missing keys

        Returns:
            dict: Loaded configuration

        Raises:
            ConfigFileNotFoundError: If file doesn't exist
            ConfigParseError: If JSON/YAML is invalid
            ConfigValidationError: If schema validation fails
        """
        if not path.exists():
            raise ConfigFileNotFoundError(str(path))

        try:
            content = path.read_text()
            # Detect format by extension
            suffix = path.suffix.lower()
            # yaml.safe_load and json.loads return Any, cast to object for type safety
            raw_data: object
            if suffix in (".yaml", ".yml"):
                raw_data = cast(object, yaml.safe_load(content)) or {}
            else:
                raw_data = cast(object, json.loads(content))
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ConfigParseError(str(path), str(e)) from e

        # Expand environment variables
        expanded = cls._expand_env(raw_data)
        if not isinstance(expanded, dict):
            expanded_dict: dict[str, object] = {}
        else:
            # Cast from dict[Unknown, Unknown] to dict[str, object]
            expanded_dict = cast(dict[str, object], expanded)

        # Apply defaults
        if defaults:
            expanded_dict = cls._apply_defaults(expanded_dict, defaults)

        # Validate schema
        cls._validate_schema(expanded_dict, path)

        return expanded_dict

    @classmethod
    def save(cls, path: Path, data: dict[str, object]) -> None:
        """Save configuration to file.

        Supports both JSON and YAML formats based on file extension.

        Args:
            path: Path to configuration file
            data: Configuration data to save

        Raises:
            ConfigParseError: If JSON/YAML serialization fails
        """
        try:
            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)

            # Detect format by extension
            suffix = path.suffix.lower()
            if suffix in (".yaml", ".yml"):
                content = yaml.safe_dump(data, default_flow_style=False, sort_keys=False)
            else:
                content = json.dumps(data, indent=2)
            _ = path.write_text(content)
        except (json.JSONDecodeError, yaml.YAMLError, OSError) as e:
            raise ConfigParseError(str(path), str(e)) from e

    @classmethod
    def _expand_env(cls, data: object) -> object:
        """Expand environment variables in string values.

        Handles $VAR and ${VAR} patterns.

        Args:
            data: Value to process (may be nested dict/list)

        Returns:
            Processed value with env vars expanded
        """
        if isinstance(data, str):

            def replace_env(match: re.Match[str]) -> str:
                var_name = match.group(1) or match.group(2)
                return os.environ.get(var_name) or match.group(0)

            return re.sub(r"\$\{([^}]+)\}|\$(\w+)", replace_env, data)
        if isinstance(data, dict):
            # Cast to dict[object, object] after isinstance narrowing
            data_dict = cast(dict[object, object], data)
            result: dict[object, object] = {}
            for k, v in data_dict.items():
                result[k] = cls._expand_env(v)
            return result
        if isinstance(data, list):
            # Cast to list[object] after isinstance narrowing
            data_list = cast(list[object], data)
            return [cls._expand_env(item) for item in data_list]
        return data

    @classmethod
    def _apply_defaults(
        cls, data: dict[str, object], defaults: dict[str, object]
    ) -> dict[str, object]:
        """Apply default values for missing keys.

        Args:
            data: Loaded configuration
            defaults: Default values

        Returns:
            Merged configuration
        """
        result = dict(defaults)
        result.update(data)
        return result

    @classmethod
    def _validate_schema(cls, data: dict[str, object], path: Path) -> None:
        """Validate configuration schema.

        Args:
            data: Configuration to validate
            path: Source file path (for error messages)

        Raises:
            ConfigValidationError: If validation fails
        """
        errors: list[str] = []

        # Required top-level keys
        if "languages" not in data:
            errors.append("Missing required key: 'languages'")

        # Validate languages structure
        languages_val: object = data.get("languages")
        if languages_val is not None and not isinstance(languages_val, dict):
            errors.append("'languages' must be a dictionary")

        # Validate language entries have required fields
        if languages_val is not None and isinstance(languages_val, dict):
            # Cast after isinstance narrowing
            languages = cast(dict[object, object], languages_val)
            for lang_id, lang_config in languages.items():
                if isinstance(lang_config, dict) and "command" not in lang_config:
                    errors.append(f"Language '{lang_id}' missing required key: 'command'")

        if errors:
            raise ConfigValidationError(str(path), errors)
