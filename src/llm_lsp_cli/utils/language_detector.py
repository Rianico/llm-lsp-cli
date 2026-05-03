"""Workspace language detection based on file extensions."""

from __future__ import annotations

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
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
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
