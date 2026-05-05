# pyright: reportExplicitAny=false
"""Default configuration values for llm-lsp-cli.

This module handles LSP response data (dict[str, Any]).
LSP responses are inherently dynamic, so Any is used for dict value types.
"""

from typing import Any

from .schema import LanguageTestFilterConfig, TestFilterConfig

DEFAULT_CONFIG: dict[str, Any] = {
    "languages": {
        # Python:
        #   - basedpyright-langserver (Recommended) - https://github.com/DetachHead/basedpyright
        #   - pyright-langserver (Alternative) - https://github.com/microsoft/pyright
        "python": {
            "command": "basedpyright-langserver",
            "args": ["--stdio"],
            "root_markers": ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", ".git"],
        },
        # TypeScript:
        #   - typescript-language-server (Recommended) - https://github.com/typescript-language-server/typescript-language-server
        "typescript": {
            "command": "typescript-language-server",
            "args": ["--stdio"],
            "root_markers": ["tsconfig.json", "package.json", ".git"],
        },
        # JavaScript:
        #   - typescript-language-server (Recommended) - https://github.com/typescript-language-server/typescript-language-server
        "javascript": {
            "command": "typescript-language-server",
            "args": ["--stdio"],
            "root_markers": ["package.json", ".git"],
        },
        # Rust:
        #   - rust-analyzer (Recommended) - https://github.com/rust-lang/rust-analyzer
        "rust": {
            "command": "rust-analyzer",
            "root_markers": ["Cargo.toml", ".git"],
        },
        # Go:
        #   - gopls (Recommended) - https://github.com/golang/tools/tree/master/gopls
        "go": {
            "command": "gopls",
            "root_markers": ["go.mod", "go.sum", ".git"],
        },
        # Java:
        #   - jdtls (Recommended) - https://github.com/eclipse-jdtls/eclipse.jdt.ls
        "java": {
            "command": "jdtls",
            "root_markers": [
                "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", ".git",
            ],
        },
        # C/C++:
        #   - clangd (Recommended) - https://github.com/llvm/llvm-project/tree/main/clang-tools-extra/clangd
        #   - ccls (Alternative) - https://github.com/MaskRay/ccls
        "cpp": {
            "command": "clangd",
            "root_markers": ["compile_commands.json", "CMakeLists.txt", "Makefile", ".git"],
        },
        # C#:
        #   - OmniSharp (Recommended) - https://github.com/OmniSharp/omnisharp-roslyn
        #   - csharp-ls (Alternative) - https://github.com/razzmatazz/csharp-language-server
        "csharp": {
            "command": "OmniSharp",
            "root_markers": ["*.sln", "*.csproj", ".git"],
        },
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
