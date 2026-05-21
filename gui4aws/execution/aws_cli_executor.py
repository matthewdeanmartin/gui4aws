"""Run an ActionDefinition by shelling out to the `aws` CLI."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess  # nosec B404 - launching aws CLI is the whole point
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from gui4aws.execution.endpoint_config import EndpointConfig
from gui4aws.models import ActionDefinition

__all__ = ["AwsCliExecutor", "AwsCliFailure", "AwsCliResult"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AwsCliResult:
    """Successful `aws` CLI invocation."""

    argv: tuple[str, ...]
    region: str
    duration_seconds: float
    stdout: str
    stderr: str
    exit_code: int
    parsed_json: Any


@dataclass(frozen=True)
class AwsCliFailure:
    """Failed `aws` CLI invocation."""

    argv: tuple[str, ...]
    region: str
    duration_seconds: float
    stdout: str
    stderr: str
    exit_code: int
    reason: str


class AwsCliExecutor:
    """Execute actions by spawning the `aws` CLI."""

    def __init__(
        self,
        profile_name: str | None,
        region_name: str,
        endpoint_config: EndpointConfig,
        aws_binary: str | None = None,
    ) -> None:
        self.profile_name = profile_name
        self.region_name = region_name
        self.endpoint_config = endpoint_config
        self.aws_binary = aws_binary or shutil.which("aws") or "aws"

    def build_argv(
        self,
        action: ActionDefinition,
        inputs: Mapping[str, str],
    ) -> tuple[str, ...]:
        """Build the argv list for the action."""
        template = action.cli_template
        argv: list[str] = [self.aws_binary, template.service, template.command]
        argv.extend(["--region", self.region_name])
        if self.profile_name:
            argv.extend(["--profile", self.profile_name])
        endpoint_url = self.endpoint_config.resolved_url()
        if endpoint_url is not None:
            argv.extend(["--endpoint-url", endpoint_url])
        argv.extend(["--output", "json"])

        arg_map = template.arg_map
        for input_field in action.input_fields:
            value = inputs.get(input_field.name)
            if value is None or value == "":
                continue
            flag = arg_map.get(input_field.name)
            if flag is None:
                continue
            if input_field.kind == "bool":
                if value.strip().lower() in {"true", "yes", "1", "on"}:
                    argv.append(f"--{flag}")
                else:
                    argv.append(f"--no-{flag}")
            else:
                argv.extend([f"--{flag}", value])
        return tuple(argv)

    def execute(
        self,
        action: ActionDefinition,
        inputs: Mapping[str, str],
    ) -> AwsCliResult | AwsCliFailure:
        """Run the CLI. Never raises — failures return an AwsCliFailure."""
        argv = self.build_argv(action, inputs)
        logger.info("aws-cli argv=%s", argv)
        start = time.monotonic()
        try:
            completed = subprocess.run(  # nosec B603 - argv list, no shell
                list(argv),
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
        except FileNotFoundError as exc:
            duration = time.monotonic() - start
            return AwsCliFailure(
                argv=argv,
                region=self.region_name,
                duration_seconds=duration,
                stdout="",
                stderr=str(exc),
                exit_code=-1,
                reason="aws CLI not found on PATH",
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - start
            return AwsCliFailure(
                argv=argv,
                region=self.region_name,
                duration_seconds=duration,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                exit_code=-1,
                reason=f"timeout after {exc.timeout}s",
            )
        duration = time.monotonic() - start
        if completed.returncode != 0:
            return AwsCliFailure(
                argv=argv,
                region=self.region_name,
                duration_seconds=duration,
                stdout=completed.stdout,
                stderr=completed.stderr,
                exit_code=completed.returncode,
                reason=parse_aws_cli_error(completed.stderr),
            )
        parsed: Any = None
        if completed.stdout.strip():
            try:
                parsed = json.loads(completed.stdout)
            except json.JSONDecodeError:
                parsed = None
        return AwsCliResult(
            argv=argv,
            region=self.region_name,
            duration_seconds=duration,
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
            parsed_json=parsed,
        )


def parse_aws_cli_error(stderr: str) -> str:
    """Best-effort one-line summary of an aws-cli error."""
    for line in stderr.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return "aws CLI exited non-zero"


def quote_for_shell(parts: Sequence[str]) -> str:
    """Shell-quote a sequence of argv parts for display in the script viewer."""
    quoted: list[str] = []
    for part in parts:
        if not part or any(ch in part for ch in ' \t"\'$`\\!*?[](){}<>|;&'):
            escaped = part.replace("'", "'\\''")
            quoted.append(f"'{escaped}'")
        else:
            quoted.append(part)
    return " ".join(quoted)
