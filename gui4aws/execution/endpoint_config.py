"""Endpoint configuration: where do we send AWS calls?"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = ["EndpointConfig", "EndpointMode"]


class EndpointMode(str, Enum):
    """Where AWS calls are routed."""

    AWS = "aws"
    MOTO = "moto"
    ROBOTOCORE = "robotocore"
    DOCKER = "docker"
    CUSTOM = "custom"


@dataclass(frozen=True)
class EndpointConfig:
    """Resolved endpoint settings.

    Attributes:
        mode: Which endpoint mode is selected.
        endpoint_url: Full URL when mode != AWS. For moto, defaults to http://127.0.0.1:5000.
                      For robotocore, defaults to http://localhost:4566.
                      Ignored when mode == AWS.
    """

    mode: EndpointMode = EndpointMode.AWS
    endpoint_url: str | None = None

    def resolved_url(self) -> str | None:
        """Return the URL boto3/aws-cli should use, or None for real AWS."""
        if self.mode is EndpointMode.AWS:
            return None
        if self.endpoint_url:
            return self.endpoint_url
        if self.mode is EndpointMode.MOTO:
            return "http://127.0.0.1:5000"
        if self.mode is EndpointMode.ROBOTOCORE:
            return "http://localhost:4566"
        return None

    @classmethod
    def for_mode(cls, mode: EndpointMode, endpoint_url: str | None = None) -> EndpointConfig:
        """Build an EndpointConfig, validating that a URL is present for custom mode."""
        if mode is EndpointMode.CUSTOM and not endpoint_url:
            raise ValueError("endpoint_url is required when mode == CUSTOM")
        return cls(mode=mode, endpoint_url=endpoint_url)
