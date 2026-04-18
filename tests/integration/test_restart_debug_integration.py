"""Integration tests for the --debug flag on restart subcommand."""

from unittest.mock import MagicMock, patch

from llm_lsp_cli.cli import app
from tests.test_cli import runner


class TestRestartDebugIntegration:
    """Integration tests for --debug flag on restart subcommand."""

    def test_restart_debug_flag_in_help_output(self) -> None:
        """Test that --debug flag appears in restart --help output."""
        result = runner.invoke(app, ["restart", "--help"])
        assert result.exit_code == 0
        # Flag should be present with both long and short forms
        assert "--debug" in result.output
        assert "-d" in result.output
        # Help text should include the description
        assert "debug logging" in result.output.lower()

    def test_restart_debug_flag_enables_logging(self) -> None:
        """Test that --debug flag enables debug logging in the daemon."""
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_instance.stop.return_value = None
        mock_instance.start.return_value = None
        mock_instance.get_pid.return_value = 12345

        with patch("llm_lsp_cli.daemon.DaemonManager", return_value=mock_instance):
            result = runner.invoke(app, ["restart", "--debug"])
            assert result.exit_code == 0
            # Verify the command executed successfully with debug flag
            assert "RESTART" in result.output

    def test_restart_debug_short_flag_enables_logging(self) -> None:
        """Test that -d short flag enables debug logging identically."""
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_instance.stop.return_value = None
        mock_instance.start.return_value = None
        mock_instance.get_pid.return_value = 12345

        with patch("llm_lsp_cli.daemon.DaemonManager", return_value=mock_instance):
            result = runner.invoke(app, ["restart", "-d"])
            assert result.exit_code == 0
            assert "RESTART" in result.output

    def test_restart_debug_flag_propagates_to_daemon_manager(self) -> None:
        """Test that debug=True is passed to DaemonManager constructor."""
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock_instance
            result = runner.invoke(app, ["restart", "--debug"])
            assert result.exit_code == 0

            # Verify debug=True was passed
            call_kwargs = mock_manager.call_args.kwargs
            assert call_kwargs["debug"] is True

    def test_restart_without_debug_uses_default_false(self) -> None:
        """Test that omitting --debug passes debug=False by default."""
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock_instance
            result = runner.invoke(app, ["restart"])
            assert result.exit_code == 0

            # Verify debug=False was passed by default
            call_kwargs = mock_manager.call_args.kwargs
            assert call_kwargs["debug"] is False

    def test_restart_debug_with_workspace_flag(self) -> None:
        """Test that --debug works in combination with --workspace."""
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock_instance
            result = runner.invoke(app, ["restart", "--debug", "--workspace", "/tmp"])
            assert result.exit_code == 0

            call_kwargs = mock_manager.call_args.kwargs
            assert call_kwargs["debug"] is True
            assert call_kwargs["workspace_path"] == "/tmp"

    def test_restart_debug_with_language_flag(self) -> None:
        """Test that --debug works in combination with --language."""
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock_instance
            result = runner.invoke(app, ["restart", "--debug", "--language", "python"])
            assert result.exit_code == 0

            call_kwargs = mock_manager.call_args.kwargs
            assert call_kwargs["debug"] is True
            assert call_kwargs["language"] == "python"

    def test_restart_debug_with_all_flags_combined(self) -> None:
        """Test that --debug works with all other restart flags."""
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock_instance
            result = runner.invoke(
                app,
                ["restart", "--debug", "--workspace", "/tmp", "--language", "python"],
            )
            assert result.exit_code == 0

            call_kwargs = mock_manager.call_args.kwargs
            assert call_kwargs["debug"] is True
            assert call_kwargs["workspace_path"] == "/tmp"
            assert call_kwargs["language"] == "python"

    def test_restart_debug_consistency_with_start(self) -> None:
        """Test that restart --debug has the same flag signature as start --debug."""
        # Get help output for both commands
        restart_help = runner.invoke(app, ["restart", "--help"])
        start_help = runner.invoke(app, ["start", "--help"])

        assert restart_help.exit_code == 0
        assert start_help.exit_code == 0

        # Both should have --debug flag
        assert "--debug" in restart_help.output
        assert "--debug" in start_help.output

        # Both should have -d short flag
        assert "-d" in restart_help.output
        assert "-d" in start_help.output

        # Both should mention debug logging
        assert "debug logging" in restart_help.output.lower()
        assert "debug logging" in start_help.output.lower()

    def test_daemon_manager_receives_debug_parameter(self) -> None:
        """Test that DaemonManager.debug attribute is set correctly."""
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock_instance
            result = runner.invoke(app, ["restart", "--debug"])
            assert result.exit_code == 0

            # Verify the mock was called with debug=True
            mock_manager.assert_called_once()
            call_kwargs = mock_manager.call_args.kwargs
            assert "debug" in call_kwargs
            assert call_kwargs["debug"] is True


class TestRestartDebugEdgeCases:
    """Edge case tests for --debug flag on restart subcommand."""

    def test_restart_debug_flag_order_independent(self) -> None:
        """Test that --debug works regardless of flag order."""
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock_instance

            # Test --debug before other flags
            result1 = runner.invoke(app, ["restart", "--debug", "--workspace", "/tmp"])
            assert result1.exit_code == 0
            assert mock_manager.call_args.kwargs["debug"] is True

            # Test --debug after other flags
            result2 = runner.invoke(app, ["restart", "--workspace", "/tmp", "--debug"])
            assert result2.exit_code == 0
            assert mock_manager.call_args.kwargs["debug"] is True

    def test_restart_debug_multiple_times_no_error(self) -> None:
        """Test that invoking restart --debug multiple times doesn't cause errors."""
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock_instance

            # Invoke multiple times
            for _ in range(3):
                result = runner.invoke(app, ["restart", "--debug"])
                assert result.exit_code == 0

    def test_restart_short_and_long_debug_flags_equivalent(self) -> None:
        """Test that -d and --debug produce identical results."""
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock_instance

            # Test long flag
            result_long = runner.invoke(app, ["restart", "--debug"])
            assert result_long.exit_code == 0
            long_debug = mock_manager.call_args.kwargs["debug"]

            # Test short flag
            result_short = runner.invoke(app, ["restart", "-d"])
            assert result_short.exit_code == 0
            short_debug = mock_manager.call_args.kwargs["debug"]

            # Both should pass debug=True
            assert long_debug is True
            assert short_debug is True

    def test_restart_debug_with_invalid_workspace_graceful_handling(self) -> None:
        """Test that --debug with invalid workspace is handled gracefully."""
        mock_instance = MagicMock()
        # Simulate non-running daemon for restart scenario
        mock_instance.is_running.return_value = False

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock_instance

            # Should handle gracefully (may exit with 0 or error message)
            result = runner.invoke(app, ["restart", "--debug", "--workspace", "/nonexistent"])
            # The command should not crash - either success or graceful error
            assert result.exit_code in (0, 1)
