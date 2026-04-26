"""CLI entry point for llm-lsp-cli."""

import typer

from llm_lsp_cli.commands.shared import GlobalOptions
from llm_lsp_cli.utils import OutputFormat

app = typer.Typer(
    name="llm-lsp-cli",
    help="Interact with language servers to provide code intelligence features.",
    add_completion=True,
)


def global_options_callback(
    ctx: typer.Context,
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
    output_format: OutputFormat = typer.Option(  # noqa: B008
        OutputFormat.JSON,
        "--format",
        "-o",
        help="Output format (text, yaml, json, or csv)",
    ),
) -> None:
    """Callback to capture global options into context."""
    ctx.obj = GlobalOptions(
        workspace=workspace,
        language=language,
        output_format=output_format,
    )


app.callback()(global_options_callback)


@app.command()
def version() -> None:
    """Show the version of llm-lsp-cli."""
    from llm_lsp_cli import __version__

    typer.echo(f"llm-lsp-cli version {__version__}")


# Register command groups
from llm_lsp_cli.commands import config, daemon, lsp

app.add_typer(daemon.app, name="daemon")
app.add_typer(lsp.app, name="lsp")
app.add_typer(config.app, name="config")


if __name__ == "__main__":
    app()
