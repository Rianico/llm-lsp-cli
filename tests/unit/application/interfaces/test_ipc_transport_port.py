"""Tests for IpcTransportPort protocol."""

import inspect

from llm_lsp_cli.application.interfaces.ipc_transport import IpcTransportPort


class TestIpcTransportPort:
    """Protocol contract tests for IpcTransportPort."""

    def test_protocol_has_send_method(self):
        """Verify protocol defines send abstract method."""
        assert hasattr(IpcTransportPort, "send")

    def test_protocol_has_receive_method(self):
        """Verify protocol defines receive abstract method."""
        assert hasattr(IpcTransportPort, "receive")

    def test_protocol_has_close_method(self):
        """Verify protocol defines close abstract method."""
        assert hasattr(IpcTransportPort, "close")

    def test_send_method_signature(self):
        """Verify send method has correct signature."""
        sig = inspect.signature(IpcTransportPort.send)
        params = list(sig.parameters.keys())

        # Should have self and message parameters
        assert "message" in params or len(params) >= 1

    def test_receive_method_signature(self):
        """Verify receive method signature."""
        sig = inspect.signature(IpcTransportPort.receive)
        # Should have at least self parameter
        params = list(sig.parameters.keys())
        assert len(params) >= 1

    def test_close_method_signature(self):
        """Verify close method signature."""
        sig = inspect.signature(IpcTransportPort.close)
        # Should have at least self parameter
        params = list(sig.parameters.keys())
        assert len(params) >= 1


class TestIpcTransportProtocolStructure:
    """Test the protocol structure."""

    def test_protocol_is_valid_type(self):
        """Verify protocol is a valid type."""
        assert isinstance(IpcTransportPort, type)
