# pyright: reportExplicitAny=false
"""YAML formatting utilities for llm-lsp-cli.

This module handles LSP response data (dict[str, Any]).
LSP responses are inherently dynamic, so Any is used for dict value types.
"""

from typing import Any

import yaml


class FlowStyleDumper(yaml.SafeDumper):
    """Custom YAML dumper that outputs sequences in flow style.

    Sequences (lists) are rendered inline with brackets: ["item1", "item2"]
    Mappings (dicts) remain in block style for readability.
    """

    pass


def _represent_sequence(
    dumper: yaml.SafeDumper, data: list[Any]
) -> yaml.SequenceNode:
    """Represent sequences in flow style (inline with brackets)."""
    return dumper.represent_sequence(
        "tag:yaml.org,2002:seq", data, flow_style=True
    )


FlowStyleDumper.add_representer(list, _represent_sequence)


def dump_config(data: dict[str, Any]) -> str:
    """Dump configuration data with flow-style lists.

    Args:
        data: Configuration dictionary to dump

    Returns:
        YAML string with flow-style lists and block-style mappings
    """
    return yaml.dump(data, Dumper=FlowStyleDumper, sort_keys=False)
