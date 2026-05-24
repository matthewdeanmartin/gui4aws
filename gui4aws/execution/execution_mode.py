"""Execution mode enum: AWS CLI vs boto3."""

from __future__ import annotations

from enum import Enum

__all__ = ["ExecutionMode"]


class ExecutionMode(str, Enum):
    """How the current action will be executed (and exported)."""

    AWS_CLI = "aws-cli"
    BOTO3 = "boto3"
