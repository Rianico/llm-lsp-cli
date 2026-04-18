"""Work Done Progress domain entities."""

from dataclasses import dataclass


@dataclass
class WorkDoneProgressState:
    """
    Tracks the state of a work done progress operation.

    Attributes:
        token: Unique progress token from the server
        title: Progress title (e.g., "Indexing workspace")
        message: Current progress message
        percentage: Progress percentage (0-100)
        cancellable: Whether the operation can be cancelled
        started: Whether progress has started
        completed: Whether progress has completed
    """

    token: str
    title: str = ""
    message: str = ""
    percentage: int = 0
    cancellable: bool = False
    started: bool = False
    completed: bool = False
