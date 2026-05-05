# pyright: reportExplicitAny=false
# pyright: reportAny=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""Root detection for workspace based on config-driven markers.

This module handles LSP response data (dict[str, Any]).
LSP responses are inherently dynamic, so Any is used for dict value types.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def find_root_by_markers(start_path: Path, markers: list[str]) -> Path | None:
    """Find workspace root by searching upward for marker files.

    Args:
        start_path: Directory to start searching from (or file path - uses parent)
        markers: List of marker file names or glob patterns to search for

    Returns:
        Path to the directory containing the first matching marker, or None if not found

    Priority:
        Markers are checked in list order. First match wins.
    """
    if not markers:
        return None

    # Handle file path - use its parent directory
    path = start_path if start_path.is_dir() else start_path.parent
    path = path.resolve()

    # Search upward through directory hierarchy
    while True:
        for marker in markers:
            if _matches_marker(path, marker):
                return path

        # Stop at filesystem root
        parent = path.parent
        if parent == path:
            return None
        path = parent


def _matches_marker(directory: Path, marker: str) -> bool:
    """Check if a marker matches in the given directory.

    Args:
        directory: Directory to check
        marker: Marker file name or glob pattern

    Returns:
        True if marker matches, False otherwise
    """
    try:
        if marker.startswith("*."):
            # Glob pattern - check if any files match
            return next(directory.glob(marker), None) is not None
        else:
            # Exact file match
            return (directory / marker).exists()
    except (OSError, PermissionError):
        return False


def detect_workspace_and_language(
    file_path: str | None,
    explicit_workspace: str | None,
    explicit_language: str | None,
    language_configs: dict[str, dict[str, Any]],
    extension_map: dict[str, str],
    cwd: str | None = None,
) -> tuple[Path, str | None]:
    """Detect workspace root and language from various inputs.

    Priority:
        1. Explicit workspace + language: use as-is
        2. Explicit language only: find root using that language's markers
        3. File extension detection: language from extension, workspace from explicit or markers
        4. Explicit workspace only: find language by markers in that workspace
        5. Search all languages from CWD: first match wins
        6. Fallback: CWD, no language

    Args:
        file_path: Optional file path to detect from
        explicit_workspace: User-specified workspace (overrides detection)
        explicit_language: User-specified language (overrides detection)
        language_configs: Dict mapping language name to config with root_markers
        extension_map: Dict mapping file extension to language name
        cwd: Current working directory (defaults to actual CWD)

    Returns:
        Tuple of (workspace_path, language_or_none)
    """
    effective_cwd = Path(cwd) if cwd else Path.cwd()

    # Priority 1: Explicit workspace + language
    if explicit_workspace and explicit_language:
        return Path(explicit_workspace), explicit_language

    # Priority 2: Explicit language only - find root using that language's markers
    if explicit_language:
        markers = _get_markers_for_language(explicit_language, language_configs)
        if markers:
            root = find_root_by_markers(effective_cwd, markers)
            if root:
                return root, explicit_language
        return effective_cwd, explicit_language

    # Priority 3: Auto-detect from file extension (before workspace marker search)
    if file_path:
        file_path_obj = Path(file_path)
        ext = file_path_obj.suffix.lower()
        detected_lang = extension_map.get(ext)

        if detected_lang is not None:
            # Use explicit workspace if provided, otherwise find from markers
            if explicit_workspace:
                return Path(explicit_workspace), detected_lang

            markers = _get_markers_for_language(detected_lang, language_configs)
            if markers:
                # Use file's directory for marker search if it exists
                search_path = file_path_obj if file_path_obj.exists() else effective_cwd
                root = find_root_by_markers(search_path, markers)
                if root:
                    return root, detected_lang
            return effective_cwd, detected_lang

        # Unsupported file type - return explicit workspace or file's parent directory
        if explicit_workspace:
            return Path(explicit_workspace), None
        if file_path_obj.exists():
            return file_path_obj.parent, None
        return effective_cwd, None

    # Priority 4: Explicit workspace only - find language by markers in that workspace
    if explicit_workspace:
        workspace_path = Path(explicit_workspace)
        for language, config in language_configs.items():
            markers = config.get("root_markers", [])
            if markers:
                root = find_root_by_markers(workspace_path, markers)
                if root:
                    return workspace_path, language
        # No language detected in explicit workspace
        return workspace_path, None

    # Priority 5: Search all languages from CWD
    for lang_name, lang_config in language_configs.items():
        markers = lang_config.get("root_markers", [])
        if markers:
            root = find_root_by_markers(effective_cwd, markers)
            if root:
                return root, lang_name

    # Priority 6: Fallback to CWD, no language
    return effective_cwd, None


def _get_markers_for_language(
    language: str, configs: dict[str, dict[str, Any]]
) -> list[str]:
    """Get root markers for a language from config.

    Args:
        language: Language name
        configs: Dict of language configs

    Returns:
        List of markers or empty list
    """
    config = configs.get(language, {})
    markers = config.get("root_markers", [])
    # Type guard: ensure we return a list of strings
    if isinstance(markers, list):
        return [str(m) for m in markers]
    return []


def format_unsupported_message(language: str | None, available: list[str]) -> str:
    """Format a helpful message for unsupported file types.

    Args:
        language: The detected language (or None if not recognized)
        available: List of configured language names

    Returns:
        Formatted message string
    """
    lang_str = f"'{language}'" if language else "unknown"
    available_str = ", ".join(available) if available else "none"
    return (
        f"Unsupported file type: {lang_str}. "
        f"Configured languages: {available_str}.\n"
        f"To add support, configure a language server in .llm-lsp-cli.yaml"
    )
