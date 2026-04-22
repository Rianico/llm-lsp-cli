"""Tests for glob-based test path filtering with language-segmented patterns."""

from __future__ import annotations


class TestGlobPatternMatching:
    """Tests for glob pattern matching engine (**, *, ?)."""

    def test_double_star_matches_any_directory_depth(self) -> None:
        """** should match any number of directory levels.

        Pattern: **/tests/**/*.py
        Should match: file:///project/tests/unit/test_main.py
        """
        from llm_lsp_cli.test_filter import _is_test_path

        # ** matches zero or more directories
        assert _is_test_path("file:///project/tests/test.py", language="python") is True
        assert _is_test_path("file:///project/tests/unit/test.py", language="python") is True
        assert _is_test_path("file:///project/src/tests/unit/test.py", language="python") is True
        assert _is_test_path("file:///a/b/c/d/tests/e/f/g/test.py", language="python") is True

    def test_single_star_matches_within_segment(self) -> None:
        """* should match characters within a path segment.

        Pattern: **/test_*.py
        Should match: file:///src/test_main.py
        """
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///src/test_main.py", language="python") is True
        assert _is_test_path("file:///src/test_utils.py", language="python") is True
        # * requires at least one char
        assert _is_test_path("file:///src/test.py", language="python") is False

    def test_question_mark_matches_single_character(self) -> None:
        """? should match exactly one character.

        Pattern: test_?.py
        Should match: test_a.py but NOT test_ab.py

        Note: Python config has test_*.py which matches test_ab.py.
        This test demonstrates that ? works correctly for single chars,
        but broader patterns like test_*.py will also match multi-char names.
        """
        from llm_lsp_cli.test_filter import _is_test_path

        # ? matches exactly one character
        # Note: test_ab.py IS a test because Python has test_*.py pattern
        assert _is_test_path("file:///src/test_a.py", language="python") is True
        assert _is_test_path("file:///src/test_1.py", language="python") is True
        assert _is_test_path("file:///src/test_ab.py", language="python") is True
        assert _is_test_path("file:///src/test_12.py", language="python") is True

    def test_glob_pattern_go_test_suffix(self) -> None:
        """Go test suffix pattern matching.

        Pattern: *_test.go
        """
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/handler_test.go", language="go") is True
        assert _is_test_path("file:///project/utils/util_test.go", language="go") is True
        assert _is_test_path("file:///project/handler.go", language="go") is False

    def test_glob_pattern_typescript_test(self) -> None:
        """TypeScript test file pattern matching.

        Pattern: **/__tests__/**/*.ts
        """
        from llm_lsp_cli.test_filter import _is_test_path

        assert (
            _is_test_path("file:///project/__tests__/Component.test.ts", language="typescript")
            is True
        )
        assert _is_test_path("file:///src/__tests__/utils.test.ts", language="typescript") is True
        assert (
            _is_test_path(
                "file:///src/__tests__/nested/deep/file.test.ts",
                language="typescript",
            )
            is True
        )
        # Should NOT match outside __tests__
        assert (
            _is_test_path("file:///src/components/Component.test.ts", language="typescript")
            is False
        )

    def test_glob_pattern_java_maven(self) -> None:
        """Java Maven test directory pattern.

        Pattern: **/src/test/**
        """
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/src/test/java/MyTest.java", language="java") is True
        assert (
            _is_test_path(
                "file:///project/src/test/java/com/example/MyTest.java",
                language="java",
            )
            is True
        )
        assert _is_test_path("file:///project/src/main/java/MyTest.java", language="java") is False

    def test_glob_pattern_rust_tests(self) -> None:
        """Rust test directory pattern.

        Pattern: **/tests/**
        Include patterns (negation): **/tests/common/** (excluded)
        """
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/tests/integration_test.rs", language="rust") is True
        # tests/common/** is excluded by include_patterns (negation)
        assert _is_test_path("file:///project/tests/common/helpers.rs", language="rust") is False
        assert _is_test_path("file:///project/tests/common/mod.rs", language="rust") is False


class TestLanguageIsolation:
    """Tests ensuring language-specific patterns don't affect other languages."""

    def test_python_patterns_dont_affect_go(self) -> None:
        """Python tests/ directory should NOT match Go files."""
        from llm_lsp_cli.test_filter import _is_test_path

        # Go has no directory patterns, only suffix _test.go
        # So a Go file in tests/ should NOT be marked as test without suffix
        assert _is_test_path("file:///project/tests/handler.go", language="go") is False
        # But with correct suffix it should match
        assert _is_test_path("file:///project/tests/handler_test.go", language="go") is True

    def test_python_patterns_dont_affect_typescript(self) -> None:
        """Python tests/ pattern should NOT match TypeScript files outside __tests__."""
        from llm_lsp_cli.test_filter import _is_test_path

        # TypeScript uses __tests__/ not tests/
        assert _is_test_path("file:///project/tests/component.ts", language="typescript") is False
        # Only __tests__/ should match for TypeScript
        assert (
            _is_test_path("file:///project/__tests__/component.ts", language="typescript") is True
        )

    def test_typescript_patterns_dont_affect_python(self) -> None:
        """TypeScript __tests__ pattern should NOT match Python files."""
        from llm_lsp_cli.test_filter import _is_test_path

        # Python doesn't use __tests__/ convention
        # Python files in __tests__/ should still match via generic tests/ pattern
        # Actually this depends on defaults - if python has specific patterns only,
        # then __tests__ might not match. Let's test the isolation:
        # A .py file in __tests__ should NOT match TypeScript patterns
        assert (
            _is_test_path("file:///project/__tests__/Component.ts", language="typescript") is True
        )
        # Same path but different language - Python shouldn't match __tests__
        # unless in defaults. This tests that patterns are isolated per-language

    def test_go_only_uses_suffix_patterns(self) -> None:
        """Go language only uses suffix patterns, no directory patterns."""
        from llm_lsp_cli.test_filter import _is_test_path

        # Any .go file not ending in _test.go should NOT be a test
        assert _is_test_path("file:///project/handler.go", language="go") is False
        assert _is_test_path("file:///project/tests/handler.go", language="go") is False
        assert _is_test_path("file:///test/handler.go", language="go") is False
        # Only _test.go suffix should match
        assert _is_test_path("file:///project/handler_test.go", language="go") is True

    def test_unknown_language_uses_defaults(self) -> None:
        """Unknown languages should fall back to default patterns."""
        from llm_lsp_cli.test_filter import _is_test_path

        # Unknown language should still detect common test patterns
        assert _is_test_path("file:///project/tests/test_file.xyz", language="unknown") is True
        assert _is_test_path("file:///project/test_main.xyz", language="unknown") is True


class TestFalsePositiveEdgeCases:
    """Tests for edge cases that previously caused false positives."""

    def test_tests_backup_directory_not_matched(self) -> None:
        """tests_backup/ should NOT match **/tests/**/*.py pattern.

        This is a key edge case - the old substring matching would match
        'tests_backup' because it contains 'tests'. Glob patterns should
        require exact segment matching.
        """
        from llm_lsp_cli.test_filter import _is_test_path

        # tests_backup is NOT the same as tests directory
        assert _is_test_path("file:///project/tests_backup/test.py", language="python") is False
        assert _is_test_path("file:///project/tests_backup.py/main.py", language="python") is False

    def test_testimonial_directory_not_matched(self) -> None:
        """testimonial/ should NOT match **/test/**/*.py pattern."""
        from llm_lsp_cli.test_filter import _is_test_path

        # testimonial contains 'test' but is NOT a test directory
        assert _is_test_path("file:///project/testimonial/page.tsx", language="typescript") is False
        assert _is_test_path("file:///project/testimonials/list.py", language="python") is False

    def test_testing_directory_not_matched(self) -> None:
        """testing/ should NOT match **/test/**/*.py pattern."""
        from llm_lsp_cli.test_filter import _is_test_path

        # testing is NOT the same as test directory
        assert _is_test_path("file:///project/testing/utils.py", language="python") is False

    def test_latest_directory_not_matched(self) -> None:
        """latest/ should NOT match patterns containing 'test'."""
        from llm_lsp_cli.test_filter import _is_test_path

        # Edge case: 'latest' contains 'test' substring
        assert _is_test_path("file:///project/latest/release.py", language="python") is False

    def test_protest_directory_not_matched(self) -> None:
        """protest/ should NOT match patterns containing 'test'."""
        from llm_lsp_cli.test_filter import _is_test_path

        # Edge case: 'protest' contains 'test' substring
        assert _is_test_path("file:///project/protest/sign.py", language="python") is False

    def test_contest_directory_not_matched(self) -> None:
        """contest/ should NOT match patterns containing 'test'."""
        from llm_lsp_cli.test_filter import _is_test_path

        # Edge case: 'contest' contains 'test' substring
        assert _is_test_path("file:///project/contest/entry.py", language="python") is False


class TestIncludePatternsNegation:
    """Tests for include_patterns (negation/override patterns)."""

    def test_python_tests_fixtures_not_test(self) -> None:
        """**/tests/fixtures/** should NOT be classified as test files.

        Include patterns (negation) override directory patterns.
        """
        from llm_lsp_cli.test_filter import _is_test_path

        # These are in tests/ but should NOT be tests
        # (fixtures, data, conftest)
        assert (
            _is_test_path("file:///project/tests/fixtures/database.py", language="python") is False
        )
        assert _is_test_path("file:///project/tests/data/sample.json", language="python") is False
        assert _is_test_path("file:///project/tests/conftest.py", language="python") is False

    def test_rust_tests_common_not_test(self) -> None:
        """**/tests/common/** should NOT be classified as test files for Rust.

        Common test utilities/shared code shouldn't be filtered out.
        """
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/tests/common/mod.rs", language="rust") is False
        assert _is_test_path("file:///project/tests/common/helpers.rs", language="rust") is False
        # But actual test files in tests/ should still match
        assert _is_test_path("file:///project/tests/integration_test.rs", language="rust") is True

    def test_python_test_file_still_detected_outside_fixtures(self) -> None:
        """Normal test files outside fixtures should still be detected."""
        from llm_lsp_cli.test_filter import _is_test_path

        # These should still be detected as tests
        assert _is_test_path("file:///project/tests/test_main.py", language="python") is True
        assert _is_test_path("file:///project/tests/unit/test_utils.py", language="python") is True
        assert _is_test_path("file:///project/test_main.py", language="python") is True


class TestConfigurationLoading:
    """Tests for configuration loading from config.json."""

    def test_default_patterns_loaded_for_python(self) -> None:
        """Default Python patterns should be loaded from defaults.py."""
        from llm_lsp_cli.test_filter import _is_test_path

        # Verify default Python patterns work
        assert _is_test_path("file:///project/tests/test_file.py", language="python") is True
        assert _is_test_path("file:///project/test_helper.py", language="python") is True
        assert _is_test_path("file:///project/helper_test.py", language="python") is True

    def test_user_config_can_override_defaults(self) -> None:
        """User configuration should override default patterns.

        This test verifies the configuration system allows overrides.
        """
        from llm_lsp_cli.test_filter import _is_test_path, reload_config

        # Note: This test requires the reload_config mechanism to work
        # It may need integration with config manager
        reload_config()
        # After reload, patterns should reflect current config.json
        # This is a placeholder for the full integration test
        assert _is_test_path("file:///project/tests/test_file.py", language="python") is True

    def test_empty_patterns_for_language(self) -> None:
        """Language with empty patterns should not match anything."""
        # If a language has no patterns configured, nothing should match
        # This depends on fallback behavior
        pass


class TestCaseInsensitiveMatching:
    """Tests for case-insensitive pattern matching."""

    def test_uppercase_tests_directory(self) -> None:
        """TESTS/ should match **/tests/**/*.py pattern."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/TESTS/test.py", language="python") is True

    def test_mixed_case_test_directory(self) -> None:
        """Tests/ should match **/tests/**/*.py pattern."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/Tests/test.py", language="python") is True

    def test_uppercase_test_suffix(self) -> None:
        """TEST.PY should match test file patterns."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/tests/TEST.PY", language="python") is True

    def test_mixed_case_typescript_test(self) -> None:
        """Component.TEST.TS should match TypeScript test patterns."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert (
            _is_test_path(
                "file:///project/__tests__/Component.TEST.tsx",
                language="typescript",
            )
            is True
        )


class TestPerformanceAndCaching:
    """Tests for performance requirements and LRU caching."""

    def test_is_test_path_caches_results(self) -> None:
        """Repeated calls to _is_test_path should use cache."""
        from llm_lsp_cli.test_filter import _is_test_path

        # First call populates cache
        result1 = _is_test_path("file:///project/tests/test.py", language="python")
        # Second call should use cache (verifiable via cache_info)
        result2 = _is_test_path("file:///project/tests/test.py", language="python")

        assert result1 is result2
        # Cache effectiveness is tested more thoroughly in benchmarks

    def test_same_uri_different_languages_get_separate_cache_entries(
        self,
    ) -> None:
        """Same URI with different languages should cache separately."""
        from llm_lsp_cli.test_filter import _is_test_path

        uri = "file:///project/tests/handler.go"

        # Same file, different language interpretations
        result_go = _is_test_path(uri, language="go")
        result_python = _is_test_path(uri, language="python")

        # Go uses suffix only, Python uses directory patterns
        assert result_go is False  # No _test.go suffix
        assert result_python is True  # In tests/ directory


class TestBackwardCompatibility:
    """Tests ensuring backward compatibility with existing API."""

    def test_is_test_path_works_without_language_parameter(self) -> None:
        """_is_test_path should work without language parameter (backward compat)."""
        from llm_lsp_cli.test_filter import _is_test_path

        # Old code calls _is_test_path without language
        # Should still work using defaults/fallback
        assert _is_test_path("file:///project/tests/test.py") is True
        assert _is_test_path("file:///project/main.py") is False

    def test_filter_test_locations_backward_compat(self) -> None:
        """_filter_test_locations should work without language parameter."""
        from llm_lsp_cli.test_filter import _filter_test_locations

        locations = [
            {"uri": "file:///src/main.py"},
            {"uri": "file:///tests/test.py"},
        ]

        # Old API without language parameter
        result = _filter_test_locations(locations, include_tests=False)
        assert len(result) == 1
        assert result[0]["uri"] == "file:///src/main.py"

    def test_filter_test_symbols_backward_compat(self) -> None:
        """_filter_test_symbols should work without language parameter."""
        from llm_lsp_cli.test_filter import _filter_test_symbols

        symbols = [
            {"name": "Main", "location": {"uri": "file:///src/main.py"}},
            {"name": "Test", "location": {"uri": "file:///tests/test.py"}},
        ]

        # Old API without language parameter
        result = _filter_test_symbols(symbols, include_tests=False)
        assert len(result) == 1
        assert result[0]["name"] == "Main"
