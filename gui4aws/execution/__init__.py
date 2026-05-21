"""Execution layer: how an ActionDefinition becomes an AWS call.

This package never imports tkinter. All AWS-call mechanics live here so the GUI layer can stay
focused on widgets and binding.
"""

from gui4aws.execution.action_history import ActionHistory, ActionHistoryEntry
from gui4aws.execution.endpoint_config import EndpointConfig, EndpointMode
from gui4aws.execution.execution_mode import ExecutionMode

__all__ = [
    "ActionHistory",
    "ActionHistoryEntry",
    "EndpointConfig",
    "EndpointMode",
    "ExecutionMode",
]
