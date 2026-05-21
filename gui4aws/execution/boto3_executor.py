"""Run an ActionDefinition through boto3."""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from gui4aws.execution.endpoint_config import EndpointConfig
from gui4aws.models import ActionDefinition

__all__ = ["Boto3Executor", "Boto3Failure", "Boto3Result"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Boto3Result:
    """Successful boto3 call."""

    service: str
    operation: str
    region: str
    duration_seconds: float
    request_params: Mapping[str, Any]
    response: Mapping[str, Any]


@dataclass(frozen=True)
class Boto3Failure:
    """Failed boto3 call, normalized."""

    service: str
    operation: str
    region: str
    duration_seconds: float
    request_params: Mapping[str, Any]
    exception_class: str
    aws_error_code: str | None
    message: str


class Boto3Executor:
    """Execute actions via boto3.

    The executor builds a fresh `boto3.Session` per invocation so that profile, region, and
    endpoint changes take effect immediately without long-lived client caches.
    """

    def __init__(
        self,
        profile_name: str | None,
        region_name: str,
        endpoint_config: EndpointConfig,
    ) -> None:
        self.profile_name = profile_name
        self.region_name = region_name
        self.endpoint_config = endpoint_config

    def build_session(self) -> boto3.Session:
        """Construct a boto3 Session honoring the configured profile."""
        if self.profile_name:
            return boto3.Session(profile_name=self.profile_name, region_name=self.region_name)
        return boto3.Session(region_name=self.region_name)

    def build_client(self, service_name: str) -> Any:
        """Construct a boto3 client honoring the configured endpoint."""
        session = self.build_session()
        endpoint_url = self.endpoint_config.resolved_url()
        if endpoint_url is not None:
            logger.info(
                "connecting to %s via %s (%s)",
                service_name,
                endpoint_url,
                "moto" if self.endpoint_config.mode.value == "moto" else "custom endpoint",
            )
            return session.client(service_name, endpoint_url=endpoint_url)
        profile_hint = f"profile={self.profile_name}" if self.profile_name else "default credentials"
        logger.info("connecting to %s on real AWS (%s, region=%s)", service_name, profile_hint, self.region_name)
        return session.client(service_name)

    def render_params(
        self,
        action: ActionDefinition,
        inputs: Mapping[str, str],
    ) -> dict[str, Any]:
        """Translate {input_field_name: str_value} into boto3 PascalCase params."""
        params: dict[str, Any] = {}
        param_map = action.boto3_template.param_map
        for input_field in action.input_fields:
            value = inputs.get(input_field.name)
            if value is None or value == "":
                continue
            boto_name = param_map.get(input_field.name, input_field.name)
            params[boto_name] = coerce_value(value, input_field.kind)
        return params

    def execute(
        self,
        action: ActionDefinition,
        inputs: Mapping[str, str],
    ) -> Boto3Result | Boto3Failure:
        """Run the action. Never raises — failures return a Boto3Failure."""
        template = action.boto3_template
        params = self.render_params(action, inputs)
        logger.info(
            "boto3 %s.%s region=%s endpoint=%s params=%s",
            template.service,
            template.operation,
            self.region_name,
            self.endpoint_config.mode,
            params,
        )
        start = time.monotonic()
        try:
            client = self.build_client(template.service)
            operation = getattr(client, template.operation)
            response = operation(**params)
            duration = time.monotonic() - start
            return Boto3Result(
                service=template.service,
                operation=template.operation,
                region=self.region_name,
                duration_seconds=duration,
                request_params=params,
                response=response,
            )
        except ClientError as exc:
            duration = time.monotonic() - start
            err = exc.response.get("Error", {})
            return Boto3Failure(
                service=template.service,
                operation=template.operation,
                region=self.region_name,
                duration_seconds=duration,
                request_params=params,
                exception_class=type(exc).__name__,
                aws_error_code=err.get("Code"),
                message=err.get("Message", str(exc)),
            )
        except BotoCoreError as exc:
            duration = time.monotonic() - start
            return Boto3Failure(
                service=template.service,
                operation=template.operation,
                region=self.region_name,
                duration_seconds=duration,
                request_params=params,
                exception_class=type(exc).__name__,
                aws_error_code=None,
                message=str(exc),
            )


def coerce_value(raw: str, kind: str) -> Any:
    """Convert a string form value to the type implied by InputField.kind."""
    if kind == "int":
        return int(raw)
    if kind == "bool":
        return raw.strip().lower() in {"true", "yes", "1", "on"}
    return raw
