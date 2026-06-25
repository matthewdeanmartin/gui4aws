"""Render ActionDefinition + inputs as standalone AWS CLI or Python scripts.

Generated scripts must be paste-into-a-real-project ready:

- No imports from gui4aws.
- No clever runtime dispatch.
- Profile, region, endpoint URL all inlined.
"""

from __future__ import annotations

from collections.abc import Mapping

from gui4aws.execution.aws_cli_executor import quote_for_shell
from gui4aws.execution.boto3_executor import coerce_value
from gui4aws.execution.endpoint_config import EndpointConfig
from gui4aws.execution.network_config import NetworkConfig
from gui4aws.models import ActionDefinition

__all__ = ["generate_cli_script", "generate_python_script"]


def _env_var_name(field_name: str) -> str:
    """Shell/env-var name for a secret field, e.g. 'master_user_password' -> 'MASTER_USER_PASSWORD'."""
    return field_name.upper()


def _redact_inputs_for_cli(action: ActionDefinition, inputs: Mapping[str, str]) -> dict[str, str]:
    """Replace secret values with an unquoted shell env-var reference (``$NAME``).

    The placeholder is emitted unquoted so it expands at runtime; the real secret
    never appears in the generated script.
    """
    secret = action.secret_field_names()
    return {name: (f"${_env_var_name(name)}" if name in secret and value else value) for name, value in inputs.items()}


def _redact_inputs_for_python(action: ActionDefinition, inputs: Mapping[str, str]) -> dict[str, str]:
    """Replace secret values with a sentinel that renders as ``os.environ[...]`` (not a string literal)."""
    secret = action.secret_field_names()
    return {
        name: (f"\x00ENV\x00{_env_var_name(name)}" if name in secret and value else value)
        for name, value in inputs.items()
    }


# Sentinel prefix marking a value that should render as os.environ[...] rather than a quoted literal.
_ENV_SENTINEL = "\x00ENV\x00"


def _render_python_value(val: object) -> str:
    """Render a boto3 param value as Python source.

    A redacted-secret sentinel becomes an ``os.environ[...]`` lookup; everything
    else is rendered with ``repr``.
    """
    if isinstance(val, str) and val.startswith(_ENV_SENTINEL):
        env_name = val[len(_ENV_SENTINEL) :]
        return f'os.environ["{env_name}"]'
    return repr(val)


def _cli_proxy_preamble(network_config: NetworkConfig) -> list[str]:
    """Bash ``export`` lines so the generated CLI script reaches a proxy/CA bundle."""
    lines: list[str] = []
    http = network_config.http_proxy.strip()
    https = network_config.https_proxy.strip()
    no_proxy = network_config.no_proxy.strip()
    if http:
        lines.append(f'export HTTP_PROXY={quote_for_shell([http])}')
    if https:
        lines.append(f'export HTTPS_PROXY={quote_for_shell([https])}')
    if no_proxy:
        lines.append(f'export NO_PROXY={quote_for_shell([no_proxy])}')
    if network_config.ca_bundle_path.strip():
        lines.append(f'export AWS_CA_BUNDLE={quote_for_shell([network_config.ca_bundle_path.strip()])}')
    if lines:
        lines.insert(0, "# Proxy / TLS-trust settings (configured in gui4aws)")
    return lines


def generate_cli_script(
    action: ActionDefinition,
    inputs: Mapping[str, str],
    *,
    profile_name: str | None,
    region_name: str,
    endpoint_config: EndpointConfig,
    network_config: NetworkConfig | None = None,
) -> str:
    """Render the action as a bash script using the AWS CLI.

    Secret-marked inputs are emitted as ``$ENV_VAR`` references, never as the
    literal value, so the script is safe to save or paste.
    """
    network_config = network_config or NetworkConfig()
    inputs = _redact_inputs_for_cli(action, inputs)
    template = action.cli_template
    argv: list[str] = ["aws", template.service, template.command]
    argv.extend(["--region", region_name])
    if profile_name:
        argv.extend(["--profile", profile_name])
    endpoint_url = endpoint_config.resolved_url()
    if endpoint_url is not None:
        argv.extend(["--endpoint-url", endpoint_url])
    if not network_config.verify_ssl:
        argv.append("--no-verify-ssl")
    elif network_config.ca_bundle_path.strip():
        argv.extend(["--ca-bundle", network_config.ca_bundle_path.strip()])

    if action.cli_args_builder is not None:
        argv.extend(action.cli_args_builder(inputs))
    else:
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
            elif input_field.kind == "list":
                items = [item.strip() for item in value.split(",") if item.strip()]
                if items:
                    argv.append(f"--{flag}")
                    argv.extend(items)
            else:
                argv.extend([f"--{flag}", value])

    # Render as multi-line with one flag per line so no horizontal scrolling is needed.
    # "aws rds create-db-cluster-snapshot \" on line 1, then "  --flag value \" per flag.
    cmd_parts: list[str] = []
    i = 0
    while i < len(argv):
        part = argv[i]
        if part.startswith("--") and i + 1 < len(argv) and not argv[i + 1].startswith("--"):
            cmd_parts.append(f"  {quote_for_shell([part, argv[i + 1]])}")
            i += 2
        else:
            cmd_parts.append(f"  {quote_for_shell([part])}" if part.startswith("--") else quote_for_shell([part]))
            i += 1

    # First element is "aws service command" (3 tokens), rest are flags.
    base = " ".join(cmd_parts[:3])
    flag_lines = cmd_parts[3:]

    lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
    proxy_lines = _cli_proxy_preamble(network_config)
    if proxy_lines:
        lines.extend(proxy_lines)
        lines.append("")
    lines.append("# " + action.display_name)
    if flag_lines:
        lines.append(base + " \\")
        for j, fl in enumerate(flag_lines):
            suffix = " \\" if j < len(flag_lines) - 1 else ""
            lines.append(fl + suffix)
    else:
        lines.append(base)
    lines.append("")
    return "\n".join(lines)


def generate_python_script(
    action: ActionDefinition,
    inputs: Mapping[str, str],
    *,
    profile_name: str | None,
    region_name: str,
    endpoint_config: EndpointConfig,
    network_config: NetworkConfig | None = None,
) -> str:
    """Render the action as a standalone boto3 Python script.

    Secret-marked inputs render as ``os.environ["ENV_VAR"]`` lookups, never as the
    literal value, so the script is safe to save or paste.
    """
    network_config = network_config or NetworkConfig()
    inputs = _redact_inputs_for_python(action, inputs)
    template = action.boto3_template
    if action.boto3_params_builder is not None:
        params = action.boto3_params_builder(inputs)
    else:
        params = {}
        for input_field in action.input_fields:
            value = inputs.get(input_field.name)
            if value is None or value == "":
                continue
            boto_name = template.param_map.get(input_field.name, input_field.name)
            params[boto_name] = coerce_value(value, input_field.kind)

    profile_repr = repr(profile_name) if profile_name else "None"
    region_repr = repr(region_name)
    endpoint_url = endpoint_config.resolved_url()
    endpoint_repr = repr(endpoint_url) if endpoint_url else None

    uses_env = any(isinstance(val, str) and val.startswith(_ENV_SENTINEL) for val in params.values())

    proxies = network_config.explicit_proxies()
    verify = network_config.botocore_verify()
    uses_config = bool(proxies)

    lines = [
        '"""Generated by gui4aws. Safe to paste into a real project."""',
        "from __future__ import annotations",
        "",
    ]
    if uses_env:
        lines.append("import os")
    lines.append("import boto3")
    if uses_config:
        lines.append("from botocore.config import Config")
    lines += [
        "",
        "",
        "def main() -> None:",
        f"    session = boto3.Session(profile_name={profile_repr}, region_name={region_repr})",
    ]
    if uses_config:
        lines.append(f"    config = Config(proxies={proxies!r})")

    # Assemble the client(...) kwargs from endpoint / proxy / TLS-trust settings.
    client_kwargs: list[str] = []
    if endpoint_repr is not None:
        client_kwargs.append(f"endpoint_url={endpoint_repr}")
    if uses_config:
        client_kwargs.append("config=config")
    if verify is not None:
        client_kwargs.append(f"verify={verify!r}")
    kwargs_suffix = ("".join(f", {kw}" for kw in client_kwargs)) if client_kwargs else ""
    lines.append(f'    client = session.client("{template.service}"{kwargs_suffix})')

    if params:
        lines.append(f"    response = client.{template.operation}(")
        for key, val in params.items():
            lines.append(f"        {key}={_render_python_value(val)},")
        lines.append("    )")
    else:
        lines.append(f"    response = client.{template.operation}()")
    lines.extend(
        [
            "    print(response)",
            "",
            "",
            'if __name__ == "__main__":',
            "    main()",
            "",
        ]
    )
    return "\n".join(lines)
