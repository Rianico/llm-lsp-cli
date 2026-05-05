"""CLI entry point for llm-lsp-cli."""

from typing import Annotated

import typer

from llm_lsp_cli.commands import config, daemon, lsp
from llm_lsp_cli.commands.shared import GlobalOptions
from llm_lsp_cli.utils import OutputFormat

app = typer.Typer(
    name="llm-lsp-cli",
    help="Interact with language servers to provide code intelligence features.",
    add_completion=True,
)


def global_options_callback(
    ctx: typer.Context,
    workspace: Annotated[str | None, typer.Option(help="Workspace path")] = None,
    language: Annotated[
        str | None, typer.Option(help="Language (auto-detected if not specified)")
    ] = None,
    output_format: Annotated[
        OutputFormat, typer.Option(help="Output format (text, yaml, json, or csv)")
    ] = OutputFormat.JSON,
) -> None:
    """Callback to capture global options into context."""
    ctx.obj = GlobalOptions(
        workspace=workspace,
        language=language,
        output_format=output_format,
    )


_ = app.callback()(global_options_callback)


@app.command()
def version() -> None:
    """Show the version of llm-lsp-cli."""
    from llm_lsp_cli import __version__

    typer.echo(f"llm-lsp-cli version {__version__}")


app.add_typer(daemon.app, name="daemon")
app.add_typer(lsp.app, name="lsp")
app.add_typer(config.app, name="config")


if __name__ == "__main__":
    app()
