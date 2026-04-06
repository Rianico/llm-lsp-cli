"""Workspace language detection based on project files."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# File extension to language mapping (for per-file detection)
FILE_EXTENSION_MAP: dict[str, str] = {
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".rs": "rust",
    ".java": "java",
    ".py": "python",
    ".go": "go",
    ".cpp": "cpp",
    ".c": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
}


@dataclass
class LanguageMatch:
    """Represents a language detection match."""
    language: str
    confidence: float  # 1.0 = exact match, 0.5 = partial
    matched_files: list[str]


# Project file to language mapping
LANGUAGE_PATTERNS: dict[str, list[str]] = {
    "java": ["pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle"],
    "rust": ["Cargo.toml"],
    "typescript": ["tsconfig.json"],
    "javascript": ["package.json"],
    "go": ["go.mod"],
    "csharp": ["*.sln", "*.csproj"],
    "cpp": ["Makefile", "CMakeLists.txt", "compile_commands.json", "*.pro"],
    "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
}

# Priority order for disambiguation (higher = more preferred)
LANGUAGE_PRIORITY: dict[str, int] = {
    "rust": 10,      # Cargo.toml is very specific
    "go": 10,        # go.mod is very specific
    "java": 9,       # pom.xml is specific
    "csharp": 9,     # .sln is specific
    "typescript": 8, # tsconfig.json is TypeScript-specific
    "javascript": 7, # package.json could be JS or TS
    "cpp": 7,
    "python": 6,
}


def detect_language_from_file(file_path: str, default: str = "python") -> str:
    """Detect language from file extension.

    Args:
        file_path: Path to the file
        default: Fallback language if extension not recognized

    Returns:
        Language identifier (e.g., 'typescript', 'rust', 'java')
    """
    ext = Path(file_path).suffix.lower()
    return FILE_EXTENSION_MAP.get(ext, default)


@lru_cache(maxsize=128)
def _detect_language_from_workspace_cached(workspace_path: str) -> str | None:
    """Detect language by scanning workspace for project files (cached).

    Args:
        workspace_path: Path to workspace root

    Returns:
        Detected language identifier or None if not detected

    Scans for project files in priority order:
    1. Exact matches (Cargo.toml, go.mod, pom.xml)
    2. Configuration files (tsconfig.json, package.json)
    3. Build files (Makefile, CMakeLists.txt)
    4. Python-specific (pyproject.toml, setup.py)
    """
    workspace = Path(workspace_path).resolve()

    if not workspace.exists() or not workspace.is_dir():
        return None

    matches: list[LanguageMatch] = []

    for language, patterns in LANGUAGE_PATTERNS.items():
        matched_files: list[str] = []
        for pattern in patterns:
            try:
                # Handle glob patterns - use next() for efficiency (only need existence)
                if pattern.startswith("*."):
                    if next(workspace.glob(pattern), None) is not None:
                        matched_files.append(pattern)
                else:
                    # Exact file match
                    if (workspace / pattern).exists():
                        matched_files.append(pattern)
            except (OSError, PermissionError):
                # Skip patterns that can't be accessed due to permissions
                continue

        if matched_files:
            matches.append(LanguageMatch(
                language=language,
                confidence=1.0,
                matched_files=matched_files,
            ))

    if not matches:
        return None

    # Sort by priority and confidence
    matches.sort(
        key=lambda m: (m.confidence, LANGUAGE_PRIORITY.get(m.language, 0)),
        reverse=True
    )

    return matches[0].language


def detect_language_from_workspace(workspace_path: str) -> str | None:
    """Detect language by scanning workspace for project files.

    Wrapper around cached implementation.

    Args:
        workspace_path: Path to workspace root

    Returns:
        Detected language identifier or None if not detected
    """
    return _detect_language_from_workspace_cached(workspace_path)


def detect_language_with_fallback(
    workspace_path: str,
    explicit_language: str | None = None,
    default_language: str = "python",
) -> str:
    """Detect language with explicit override and fallback.

    Args:
        workspace_path: Path to workspace root
        explicit_language: User-specified language (overrides detection)
        default_language: Fallback if detection fails

    Returns:
        Language identifier to use

    Priority:
    1. Explicit language (if provided)
    2. Auto-detected language (if found)
    3. Default language
    """
    if explicit_language:
        return explicit_language

    detected = detect_language_from_workspace(workspace_path)
    if detected:
        return detected

    return default_language
