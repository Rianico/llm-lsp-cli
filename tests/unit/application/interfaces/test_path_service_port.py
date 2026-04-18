"""Tests for PathServicePort protocol."""

import pytest
import inspect
from pathlib import Path

from llm_lsp_cli.application.interfaces.path_service import PathServicePort


class TestPathServicePort:
    """Protocol contract tests for PathServicePort."""

    def test_protocol_has_build_socket_path_method(self):
        """Verify protocol defines build_socket_path method."""
        assert hasattr(PathServicePort, "build_socket_path")

    def test_protocol_has_build_pid_file_method(self):
        """Verify protocol defines build_pid_file method."""
        assert hasattr(PathServicePort, "build_pid_file")

    def test_protocol_has_build_log_file_method(self):
        """Verify protocol defines build_log_file method."""
        assert hasattr(PathServicePort, "build_log_file")

    def test_path_methods_are_static(self):
        """Verify path methods are static methods."""
        # Check that methods exist and are callable
        assert callable(getattr(PathServicePort, "build_socket_path"))
        assert callable(getattr(PathServicePort, "build_pid_file"))
        assert callable(getattr(PathServicePort, "build_log_file"))

    def test_build_socket_path_signature(self):
        """Verify build_socket_path method signature."""
        sig = inspect.signature(PathServicePort.build_socket_path)
        params = list(sig.parameters.keys())

        # Should have workspace_path, language, and optional lsp_server_name
        assert "workspace_path" in params
        assert "language" in params

    def test_build_pid_file_signature(self):
        """Verify build_pid_file method signature."""
        sig = inspect.signature(PathServicePort.build_pid_file)
        params = list(sig.parameters.keys())

        assert "workspace_path" in params
        assert "language" in params

    def test_build_log_file_signature(self):
        """Verify build_log_file method signature."""
        sig = inspect.signature(PathServicePort.build_log_file)
        params = list(sig.parameters.keys())

        assert "workspace_path" in params
        assert "language" in params


class TestPathServiceProtocolStructure:
    """Test the protocol structure."""

    def test_protocol_is_valid_type(self):
        """Verify protocol is a valid type."""
        assert isinstance(PathServicePort, type)
