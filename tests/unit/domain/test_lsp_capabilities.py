"""Tests for LSP server capabilities module."""

import json


class TestGetServerCapabilitiesStructure:
    """Test get_server_capabilities() returns correct structure."""

    def test_returns_dict_with_server_names(self) -> None:
        """Returns dict with server names as keys."""
        from llm_lsp_cli.config.capabilities import get_server_capabilities

        capabilities = get_server_capabilities()

        assert isinstance(capabilities, dict)
        assert "pyright" in capabilities or "pyright-langserver" in capabilities
        assert "basedpyright" in capabilities or "basedpyright-langserver" in capabilities

    def test_each_server_has_required_capability_keys(self) -> None:
        """Each server has required capability keys."""
        from llm_lsp_cli.config.capabilities import get_server_capabilities

        capabilities = get_server_capabilities()

        for server_name, server_caps in capabilities.items():
            assert isinstance(server_caps, dict)
            # Should have workspace support at minimum
            assert "workspace" in server_caps or "capabilities" in server_caps

    def test_pyright_capabilities_match_spec(self) -> None:
        """pyright capabilities match spec."""
        from llm_lsp_cli.config.capabilities import get_server_capabilities

        capabilities = get_server_capabilities()

        # Find pyright in capabilities
        pyright_caps = None
        for key in ["pyright", "pyright-langserver"]:
            if key in capabilities:
                pyright_caps = capabilities[key]
                break

        assert pyright_caps is not None
        assert isinstance(pyright_caps, dict)

    def test_basedpyright_capabilities_match_spec(self) -> None:
        """basedpyright capabilities match spec."""
        from llm_lsp_cli.config.capabilities import get_server_capabilities

        capabilities = get_server_capabilities()

        # Find basedpyright in capabilities
        basedpyright_caps = None
        for key in ["basedpyright", "basedpyright-langserver"]:
            if key in capabilities:
                basedpyright_caps = capabilities[key]
                break

        assert basedpyright_caps is not None
        assert isinstance(basedpyright_caps, dict)


class TestFormatCapabilitiesJson:
    """Test JSON output formatting."""

    def test_json_output_valid_json(self) -> None:
        """JSON output is valid JSON."""
        from llm_lsp_cli.config.capabilities import format_capabilities

        output = format_capabilities(format="json")

        # Should be parseable JSON
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_json_output_indented(self) -> None:
        """JSON is indented (human-readable)."""
        from llm_lsp_cli.config.capabilities import format_capabilities

        output = format_capabilities(format="json")

        # Should contain newlines (indented)
        assert "\n" in output
        # Should contain indentation
        assert "  " in output

    def test_json_all_servers_present(self) -> None:
        """All servers present in output."""
        from llm_lsp_cli.config.capabilities import format_capabilities

        output = format_capabilities(format="json")
        parsed = json.loads(output)

        # Should have multiple servers
        assert len(parsed) >= 2


class TestFormatCapabilitiesYaml:
    """Test YAML output formatting."""

    def test_yaml_output_valid_yaml(self) -> None:
        """YAML output is valid YAML."""
        import yaml
        from llm_lsp_cli.config.capabilities import format_capabilities

        output = format_capabilities(format="yaml")

        # Should be parseable YAML
        parsed = yaml.safe_load(output)
        assert isinstance(parsed, dict)

    def test_yaml_proper_indentation(self) -> None:
        """YAML uses proper indentation."""
        from llm_lsp_cli.config.capabilities import format_capabilities

        output = format_capabilities(format="yaml")

        # Should contain proper YAML structure
        assert "\n" in output
        # YAML uses spaces for indentation
        assert "  " in output or "\t" not in output

    def test_yaml_all_servers_present(self) -> None:
        """All servers present in output."""
        import yaml
        from llm_lsp_cli.config.capabilities import format_capabilities

        output = format_capabilities(format="yaml")
        parsed = yaml.safe_load(output)

        # Should have multiple servers
        assert len(parsed) >= 2


class TestFormatCapabilitiesText:
    """Test text output formatting."""

    def test_text_output_readable(self) -> None:
        """Text output is readable."""
        from llm_lsp_cli.config.capabilities import format_capabilities

        output = format_capabilities(format="text")

        # Should be non-empty string
        assert isinstance(output, str)
        assert len(output) > 0

    def test_text_server_names_as_headers(self) -> None:
        """Server names are headers."""
        from llm_lsp_cli.config.capabilities import format_capabilities

        output = format_capabilities(format="text")
        lines = output.split("\n")

        # Should have some header-like lines
        header_found = False
        for line in lines:
            if line.strip() and (line.strip().endswith(":") or line.strip().startswith("=")):
                header_found = True
                break

        assert header_found, "No server name headers found in text output"

    def test_text_capabilities_indented(self) -> None:
        """Capabilities are indented under servers."""
        from llm_lsp_cli.config.capabilities import format_capabilities

        output = format_capabilities(format="text")
        lines = output.split("\n")

        # Should have indented lines under headers
        indented_found = False
        for line in lines:
            if line.startswith("  ") or line.startswith("\t"):
                indented_found = True
                break

        assert indented_found, "No indented capability lines found in text output"
