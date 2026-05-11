"""Type stubs for daemon RPC parameter models.

These stubs inform the type checker that both snake_case field names
and camelCase aliases are valid constructor arguments (Pydantic's
validate_by_name=True behavior).
"""

from typing import overload


class DaemonPositionParams:
    """Position-based params for LSP methods."""

    workspace_path: str
    file_path: str
    line: int
    column: int

    @overload
    def __init__(
        self,
        *,
        workspace_path: str,
        file_path: str,
        line: int = ...,
        column: int = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        workspacePath: str,
        filePath: str,
        line: int = ...,
        column: int = ...,
    ) -> None: ...

    def __init__(self, **data: object) -> None: ...


class DaemonFileParams:
    """File-based params for LSP methods."""

    workspace_path: str
    file_path: str

    @overload
    def __init__(
        self,
        *,
        workspace_path: str,
        file_path: str,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        workspacePath: str,
        filePath: str,
    ) -> None: ...

    def __init__(self, **data: object) -> None: ...


class DaemonWorkspaceParams:
    """Workspace-only params for LSP methods."""

    workspace_path: str

    @overload
    def __init__(
        self,
        *,
        workspace_path: str,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        workspacePath: str,
    ) -> None: ...

    def __init__(self, **data: object) -> None: ...


class DaemonRenameParams(DaemonPositionParams):
    """Rename params with new_name in addition to position."""

    new_name: str

    @overload
    def __init__(
        self,
        *,
        workspace_path: str,
        file_path: str,
        line: int = ...,
        column: int = ...,
        new_name: str,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        workspacePath: str,
        filePath: str,
        line: int = ...,
        column: int = ...,
        newName: str,
    ) -> None: ...

    def __init__(self, **data: object) -> None: ...


class DaemonSymbolQueryParams(DaemonWorkspaceParams):
    """Workspace symbol params with query string."""

    query: str

    @overload
    def __init__(
        self,
        *,
        workspace_path: str,
        query: str,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        workspacePath: str,
        query: str,
    ) -> None: ...

    def __init__(self, **data: object) -> None: ...
