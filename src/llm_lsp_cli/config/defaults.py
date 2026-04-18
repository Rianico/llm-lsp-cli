"""Default configuration values for llm-lsp-cli."""

from typing import Any

from .schema import LanguageTestFilterConfig, TestFilterConfig

DEFAULT_CONFIG: dict[str, Any] = {
    "languages": {
        "python": {
            "command": "pyright-langserver",
            "args": ["--stdio"],
        },
        "typescript": {"command": "typescript-language-server", "args": ["--stdio"]},
        "javascript": {"command": "typescript-language-server", "args": ["--stdio"]},
        "rust": {"command": "rust-analyzer"},
        "go": {"command": "gopls"},
        "java": {"command": "jdtls"},
        "cpp": {"command": "clangd"},
        "csharp": {"command": "OmniSharp"},
    },
    "trace_lsp": False,
    "timeout_seconds": 30,
}


# Default test filter patterns organized by language
DEFAULT_TEST_FILTER_CONFIG = TestFilterConfig(
    defaults=LanguageTestFilterConfig(
        # Default fallback patterns for unknown languages
        directory_patterns=["**/tests/**", "**/test/**", "**/__tests__/**", "**/spec/**"],
        suffix_patterns=[
            "_test.go",
            ".test.js",
            ".test.ts",
            ".test.jsx",
            ".test.tsx",
            ".spec.js",
            ".spec.ts",
            ".spec.jsx",
            ".spec.tsx",
            ".test.cs",
            ".tests.cs",
            ".spec.cs",
        ],
        prefix_patterns=["test_", "_test"],
        include_patterns=[],
        enabled=True,
    ),
    languages={
        "python": LanguageTestFilterConfig(
            directory_patterns=["**/tests/**", "**/test/**"],
            suffix_patterns=["_test.py", ".test.py", "test_*.py"],
            prefix_patterns=[],
            include_patterns=[
                "**/tests/fixtures/**",
                "**/tests/data/**",
                "**/tests/conftest.py",
            ],
            enabled=True,
        ),
        "typescript": LanguageTestFilterConfig(
            directory_patterns=["**/__tests__/**", "**/spec/**"],
            suffix_patterns=[],
            prefix_patterns=["test_"],
            include_patterns=[],
            enabled=True,
        ),
        "javascript": LanguageTestFilterConfig(
            directory_patterns=["**/__tests__/**", "**/spec/**"],
            suffix_patterns=[
                ".test.js",
                ".test.jsx",
                ".spec.js",
                ".spec.jsx",
            ],
            prefix_patterns=["test_"],
            include_patterns=[],
            enabled=True,
        ),
        "go": LanguageTestFilterConfig(
            directory_patterns=[],  # Go only uses suffix patterns
            suffix_patterns=["_test.go"],
            prefix_patterns=[],
            include_patterns=[],
            enabled=True,
        ),
        "rust": LanguageTestFilterConfig(
            directory_patterns=["**/tests/**"],
            suffix_patterns=[],
            prefix_patterns=[],
            include_patterns=["**/tests/common/**"],
            enabled=True,
        ),
        "java": LanguageTestFilterConfig(
            directory_patterns=["**/src/test/**", "**/src/tests/**"],
            suffix_patterns=[],
            prefix_patterns=[],
            include_patterns=[],
            enabled=True,
        ),
        "csharp": LanguageTestFilterConfig(
            directory_patterns=["**/Tests/**", "**/Test/**"],
            suffix_patterns=[".test.cs", ".tests.cs", ".spec.cs"],
            prefix_patterns=[],
            include_patterns=[],
            enabled=True,
        ),
        "cpp": LanguageTestFilterConfig(
            directory_patterns=["**/tests/**", "**/test/**", "**/unittests/**", "**/unittest/**"],
            suffix_patterns=["_test.cpp", ".test.cpp"],
            prefix_patterns=["test_", "_test"],
            include_patterns=[],
            enabled=True,
        ),
        "c": LanguageTestFilterConfig(
            directory_patterns=["**/tests/**", "**/test/**", "**/unittests/**", "**/unittest/**"],
            suffix_patterns=["_test.c", ".test.c"],
            prefix_patterns=["test_", "_test"],
            include_patterns=[],
            enabled=True,
        ),
        "ruby": LanguageTestFilterConfig(
            directory_patterns=["**/spec/**", "**/specs/**"],
            suffix_patterns=["_spec.rb", ".spec.rb"],
            prefix_patterns=["test_", "_test"],
            include_patterns=[],
            enabled=True,
        ),
    },
    fallback=None,
)
