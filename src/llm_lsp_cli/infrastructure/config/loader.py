# pyright: reportExplicitAny=false
# pyright: reportAny=false
# pyright: reportUnknownMemberType=false
# pyright: reportMissingTypeStubs=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""Configuration file loader with validation.

This module handles LSP response data (dict[str, Any]).
LSP responses are inherently dynamic, so Any is used for dict value types.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

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
    def load(cls, path: Path, defaults: dict[str, Any] | None = None) -> dict[str, Any]:
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
            if suffix in (".yaml", ".yml"):
                data = yaml.safe_load(content) or {}
            else:
                data = json.loads(content)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ConfigParseError(str(path), str(e)) from e

        # Expand environment variables
        data = cls._expand_env(data)

        # Apply defaults
        if defaults:
            data = cls._apply_defaults(data, defaults)

        # Validate schema
        cls._validate_schema(data, path)

        return data

    @classmethod
    def save(cls, path: Path, data: dict[str, Any]) -> None:
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
            path.write_text(content)
        except (json.JSONDecodeError, yaml.YAMLError, OSError) as e:
            raise ConfigParseError(str(path), str(e)) from e

    @classmethod
    def _expand_env(cls, data: Any) -> Any:
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
            return {k: cls._expand_env(v) for k, v in data.items()}
        if isinstance(data, list):
            return [cls._expand_env(item) for item in data]
        return data

    @classmethod
    def _apply_defaults(cls, data: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
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
    def _validate_schema(cls, data: dict[str, Any], path: Path) -> None:
        """Validate configuration schema.

        Args:
            data: Configuration to validate
            path: Source file path (for error messages)

        Raises:
            ConfigValidationError: If validation fails
        """
        errors = []

        # Required top-level keys
        if "languages" not in data:
            errors.append("Missing required key: 'languages'")

        # Validate languages structure
        if "languages" in data and not isinstance(data["languages"], dict):
            errors.append("'languages' must be a dictionary")

        # Validate language entries have required fields
        if "languages" in data and isinstance(data["languages"], dict):
            for lang_id, lang_config in data["languages"].items():
                if isinstance(lang_config, dict) and "command" not in lang_config:
                    errors.append(f"Language '{lang_id}' missing required key: 'command'")

        if errors:
            raise ConfigValidationError(str(path), errors)
