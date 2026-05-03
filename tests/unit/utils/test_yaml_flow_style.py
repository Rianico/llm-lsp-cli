"""Unit tests for YAML flow-style dumper."""

import re

import yaml


class TestFlowStyleDumper:
    """Tests for FlowStyleDumper YAML output."""

    def test_flow_style_dumper_exists(self) -> None:
        """FlowStyleDumper class exists and is importable."""
        from llm_lsp_cli.utils.yaml_formatter import FlowStyleDumper

        assert FlowStyleDumper is not None

    def test_flow_style_dumper_inherits_safe_dumper(self) -> None:
        """FlowStyleDumper inherits from yaml.SafeDumper."""
        from llm_lsp_cli.utils.yaml_formatter import FlowStyleDumper

        assert issubclass(FlowStyleDumper, yaml.SafeDumper)

    def test_flow_style_dumper_renders_sequences_inline(self) -> None:
        """FlowStyleDumper renders sequences in flow style (inline)."""
        from llm_lsp_cli.utils.yaml_formatter import FlowStyleDumper

        data = {"args": ["--stdio", "--verbose"]}
        output = yaml.dump(data, Dumper=FlowStyleDumper, sort_keys=False)

        # Should use flow style: ["--stdio", "--verbose"]
        assert "[" in output
        assert "]" in output
        # Should NOT have block-style list items
        assert "\n  - " not in output

    def test_flow_style_dumper_single_item_list(self) -> None:
        """FlowStyleDumper renders single-item lists in flow style."""
        from llm_lsp_cli.utils.yaml_formatter import FlowStyleDumper

        data = {"args": ["--stdio"]}
        output = yaml.dump(data, Dumper=FlowStyleDumper, sort_keys=False)

        # Flow style uses brackets; YAML may or may not quote strings
        assert "args: [" in output
        assert "--stdio" in output
        assert "]" in output

    def test_flow_style_dumper_empty_list(self) -> None:
        """FlowStyleDumper renders empty lists as []."""
        from llm_lsp_cli.utils.yaml_formatter import FlowStyleDumper

        data = {"args": []}
        output = yaml.dump(data, Dumper=FlowStyleDumper, sort_keys=False)

        assert "[]" in output

    def test_flow_style_dumper_renders_mappings_block(self) -> None:
        """FlowStyleDumper keeps mappings in block style (not inline)."""
        from llm_lsp_cli.utils.yaml_formatter import FlowStyleDumper

        data = {
            "languages": {
                "python": {
                    "command": "pyright-langserver",
                    "args": ["--stdio"],
                }
            }
        }
        output = yaml.dump(data, Dumper=FlowStyleDumper, sort_keys=False)

        # Mappings should be in block style (separate lines with colons)
        assert "languages:" in output
        # Should NOT use inline mapping style like: languages: {python: {...}}
        assert "languages: {" not in output
        # But lists inside should still be flow style
        assert "[" in output

    def test_flow_style_dumper_nested_structure(self) -> None:
        """FlowStyleDumper handles nested structures correctly."""
        from llm_lsp_cli.utils.yaml_formatter import FlowStyleDumper

        data = {
            "languages": {
                "python": {
                    "command": "basedpyright-langserver",
                    "args": ["--stdio"],
                    "root_markers": ["pyproject.toml", ".git"],
                }
            }
        }
        output = yaml.dump(data, Dumper=FlowStyleDumper, sort_keys=False)

        # Lists should be flow style (brackets, not block-style with hyphens)
        assert "args: [" in output
        assert "--stdio" in output
        assert "pyproject.toml" in output
        # Mappings should be block style
        assert "languages:" in output
        assert "python:" in output


class TestFlowStyleOutput:
    """Tests for flow-style YAML output format verification."""

    def test_no_block_style_lists_in_output(self) -> None:
        """Config output should not contain block-style list items."""
        from llm_lsp_cli.utils.yaml_formatter import FlowStyleDumper

        data = {
            "args": ["--stdio"],
            "root_markers": ["pyproject.toml", "setup.py", ".git"],
        }
        output = yaml.dump(data, Dumper=FlowStyleDumper, sort_keys=False)

        # No block-style items (lines starting with - after indent)
        block_style_pattern = re.compile(r"^\s+-\s+", re.MULTILINE)
        assert block_style_pattern.search(output) is None

    def test_flow_style_preserves_strings_with_colons(self) -> None:
        """Flow style handles strings containing colons correctly."""
        from llm_lsp_cli.utils.yaml_formatter import FlowStyleDumper

        data = {"command": "some:command:with:colons"}
        output = yaml.dump(data, Dumper=FlowStyleDumper, sort_keys=False)

        assert "some:command:with:colons" in output


class TestFlowStyleRegression:
    """Backward compatibility tests for YAML parsing."""

    def test_parsing_old_block_style_configs(self) -> None:
        """Old block-style configs should still parse correctly."""
        # This test doesn't use FlowStyleDumper - tests that old configs still work
        block_style_yaml = """
languages:
  python:
    command: basedpyright-langserver
    args:
      - --stdio
    root_markers:
      - pyproject.toml
      - .git
trace_lsp: false
timeout_seconds: 30
"""
        parsed = yaml.safe_load(block_style_yaml)

        assert parsed["languages"]["python"]["args"] == ["--stdio"]
        assert parsed["languages"]["python"]["root_markers"] == ["pyproject.toml", ".git"]
        assert parsed["trace_lsp"] is False
        assert parsed["timeout_seconds"] == 30

    def test_flow_style_output_parses_correctly(self) -> None:
        """Flow-style YAML output parses back to original data."""
        from llm_lsp_cli.utils.yaml_formatter import FlowStyleDumper

        original_data = {
            "languages": {
                "python": {
                    "command": "basedpyright-langserver",
                    "args": ["--stdio"],
                    "root_markers": ["pyproject.toml", ".git"],
                }
            },
            "trace_lsp": False,
            "timeout_seconds": 30,
        }

        output = yaml.dump(original_data, Dumper=FlowStyleDumper, sort_keys=False)
        parsed = yaml.safe_load(output)

        assert parsed == original_data
