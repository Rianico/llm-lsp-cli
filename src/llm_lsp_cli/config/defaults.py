"""Default configuration values for llm-lsp-cli.

This module handles configuration data using fully-typed Pydantic models.
Configuration is validated at runtime by Pydantic models.
"""

from .schema import (
    ClientConfig,
    FileFilterConfig,
    LanguageFileFilterConfig,
    LanguageServerConfig,
)

# =============================================================================
# Language Server Defaults
# =============================================================================

DEFAULT_LANGUAGE_SERVERS: dict[str, LanguageServerConfig] = {
    # Python:
    #   - basedpyright-langserver (Recommended) - https://github.com/DetachHead/basedpyright
    #   - pyright-langserver (Alternative) - https://github.com/microsoft/pyright
    "python": LanguageServerConfig(
        command="basedpyright-langserver",
        args=["--stdio"],
        root_markers=["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", ".git"],
    ),
    # TypeScript:
    #   - typescript-language-server (Recommended) - https://github.com/typescript-language-server/typescript-language-server
    "typescript": LanguageServerConfig(
        command="typescript-language-server",
        args=["--stdio"],
        root_markers=["tsconfig.json", "package.json", ".git"],
    ),
    # JavaScript:
    #   - typescript-language-server (Recommended) - https://github.com/typescript-language-server/typescript-language-server
    "javascript": LanguageServerConfig(
        command="typescript-language-server",
        args=["--stdio"],
        root_markers=["package.json", ".git"],
    ),
    # Rust:
    #   - rust-analyzer (Recommended) - https://github.com/rust-lang/rust-analyzer
    "rust": LanguageServerConfig(
        command="rust-analyzer",
        root_markers=["Cargo.toml", ".git"],
    ),
    # Go:
    #   - gopls (Recommended) - https://github.com/golang/tools/tree/master/gopls
    "go": LanguageServerConfig(
        command="gopls",
        root_markers=["go.mod", "go.sum", ".git"],
    ),
    # Java:
    #   - jdtls (Recommended) - https://github.com/eclipse-jdtls/eclipse.jdt.ls
    "java": LanguageServerConfig(
        command="jdtls",
        root_markers=[
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "settings.gradle",
            ".git",
        ],
    ),
    # C/C++:
    #   - clangd (Recommended) - https://github.com/llvm/llvm-project/tree/main/clang-tools-extra/clangd
    #   - ccls (Alternative) - https://github.com/MaskRay/ccls
    "cpp": LanguageServerConfig(
        command="clangd",
        root_markers=["compile_commands.json", "CMakeLists.txt", "Makefile", ".git"],
    ),
    # C#:
    #   - OmniSharp (Recommended) - https://github.com/OmniSharp/omnisharp-roslyn
    #   - csharp-ls (Alternative) - https://github.com/razzmatazz/csharp-language-server
    "csharp": LanguageServerConfig(
        command="OmniSharp",
        root_markers=["*.sln", "*.csproj", ".git"],
    ),
}

# =============================================================================
# File Filter Defaults
# =============================================================================

DEFAULT_FILE_FILTER_CONFIG = FileFilterConfig(
    defaults=LanguageFileFilterConfig(
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
        "python": LanguageFileFilterConfig(
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
        "typescript": LanguageFileFilterConfig(
            directory_patterns=["**/__tests__/**", "**/spec/**"],
            suffix_patterns=[],
            prefix_patterns=["test_"],
            include_patterns=[],
            enabled=True,
        ),
        "javascript": LanguageFileFilterConfig(
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
        "go": LanguageFileFilterConfig(
            directory_patterns=[],  # Go only uses suffix patterns
            suffix_patterns=["_test.go"],
            prefix_patterns=[],
            include_patterns=[],
            enabled=True,
        ),
        "rust": LanguageFileFilterConfig(
            directory_patterns=["**/tests/**"],
            suffix_patterns=[],
            prefix_patterns=[],
            include_patterns=["**/tests/common/**"],
            enabled=True,
        ),
        "java": LanguageFileFilterConfig(
            directory_patterns=["**/src/test/**", "**/src/tests/**"],
            suffix_patterns=[],
            prefix_patterns=[],
            include_patterns=[],
            enabled=True,
        ),
        "csharp": LanguageFileFilterConfig(
            directory_patterns=["**/Tests/**", "**/Test/**"],
            suffix_patterns=[".test.cs", ".tests.cs", ".spec.cs"],
            prefix_patterns=[],
            include_patterns=[],
            enabled=True,
        ),
        "cpp": LanguageFileFilterConfig(
            directory_patterns=["**/tests/**", "**/test/**", "**/unittests/**", "**/unittest/**"],
            suffix_patterns=["_test.cpp", ".test.cpp"],
            prefix_patterns=["test_", "_test"],
            include_patterns=[],
            enabled=True,
        ),
        "c": LanguageFileFilterConfig(
            directory_patterns=["**/tests/**", "**/test/**", "**/unittests/**", "**/unittest/**"],
            suffix_patterns=["_test.c", ".test.c"],
            prefix_patterns=["test_", "_test"],
            include_patterns=[],
            enabled=True,
        ),
        "ruby": LanguageFileFilterConfig(
            directory_patterns=["**/spec/**", "**/specs/**"],
            suffix_patterns=["_spec.rb", ".spec.rb"],
            prefix_patterns=["test_", "_test"],
            include_patterns=[],
            enabled=True,
        ),
    },
    fallback=None,
)

# =============================================================================
# Main Client Config
# =============================================================================

DEFAULT_CLIENT_CONFIG = ClientConfig(
    languages=DEFAULT_LANGUAGE_SERVERS,
    file_filter=DEFAULT_FILE_FILTER_CONFIG,
    trace_lsp=False,
    timeout_seconds=30,
)

# Legacy dict export for backward compatibility
DEFAULT_CONFIG: dict[str, object] = DEFAULT_CLIENT_CONFIG.model_dump(mode="json")
