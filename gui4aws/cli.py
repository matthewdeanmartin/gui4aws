"""Command-line entry point for gui4aws."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

import boto3
import botocore

from gui4aws.__about__ import __version__
from gui4aws.app import AppContext
from gui4aws.execution.endpoint_config import EndpointConfig, EndpointMode
from gui4aws.execution.execution_mode import ExecutionMode
from gui4aws.logging_config import configure_logging

__all__ = ["build_parser", "main"]

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser."""
    parser = argparse.ArgumentParser(prog="gui4aws", description="Tkinter GUI for AWS")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--log-level", default="INFO", help="DEBUG, INFO, WARNING, ERROR")
    parser.add_argument("--log-file", type=Path, default=None, help="optional file to also log to")

    subparsers = parser.add_subparsers(dest="command")

    gui_parser = subparsers.add_parser("gui", help="launch the GUI")
    add_common_runtime_options(gui_parser)

    doctor_parser = subparsers.add_parser("doctor", help="environment diagnostics")
    doctor_parser.add_argument("--check-aws-cli", action="store_true", help="report aws CLI presence")
    doctor_parser.add_argument("--check-boto3", action="store_true", help="report boto3 version")
    doctor_parser.add_argument("--check-docker", action="store_true", help="report docker presence")

    subparsers.add_parser("list-profiles", help="list available AWS profiles")
    list_regions_parser = subparsers.add_parser("list-regions", help="list known AWS regions")
    from gui4aws.app import AWS_PARTITIONS

    list_regions_parser.add_argument(
        "--partition",
        default="aws",
        choices=list(AWS_PARTITIONS.keys()),
        help="AWS partition to list regions for (default: aws)",
    )

    return parser


def add_common_runtime_options(parser: argparse.ArgumentParser) -> None:
    """Add the runtime-selection options shared by ``gui`` (and future subcommands)."""
    from gui4aws.app import AWS_PARTITIONS

    parser.add_argument("--profile", default=None, help="AWS profile name")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument(
        "--partition",
        default="aws",
        choices=list(AWS_PARTITIONS.keys()),
        help="AWS partition (aws, aws-us-gov, aws-cn, aws-iso, aws-iso-b)",
    )
    parser.add_argument(
        "--mode",
        default=ExecutionMode.BOTO3.value,
        choices=[m.value for m in ExecutionMode],
        help="execution mode",
    )
    parser.add_argument(
        "--endpoint-mode",
        default=EndpointMode.AWS.value,
        choices=[m.value for m in EndpointMode],
        help="endpoint mode",
    )
    parser.add_argument("--endpoint-url", default=None, help="endpoint URL (required for --endpoint-mode custom)")


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``gui4aws`` command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level, args.log_file)

    if args.command in (None, "gui"):
        return run_gui(args)
    if args.command == "doctor":
        return run_doctor(args)
    if args.command == "list-profiles":
        return run_list_profiles()
    if args.command == "list-regions":
        return run_list_regions(args)
    parser.error(f"unknown command: {args.command}")
    return 2


def run_gui(args: argparse.Namespace) -> int:
    """Launch the GUI window."""
    partition = getattr(args, "partition", "aws")
    context = AppContext(
        profile_name=getattr(args, "profile", None),
        region_name=getattr(args, "region", "us-east-1"),
        partition=partition,
        mode=ExecutionMode(getattr(args, "mode", ExecutionMode.BOTO3.value)),
        endpoint_config=EndpointConfig.for_mode(
            EndpointMode(getattr(args, "endpoint_mode", EndpointMode.AWS.value)),
            getattr(args, "endpoint_url", None),
        ),
    )
    from gui4aws.gui.main_window import create_main_window

    profiles = available_profiles()
    regions = available_regions(partition=partition)
    window = create_main_window(context, profiles=profiles, regions=regions)
    window.run()
    return 0


def run_doctor(args: argparse.Namespace) -> int:
    """Print environment diagnostics."""
    print(f"gui4aws version: {__version__}")
    print(f"python: {sys.version.split()[0]}")
    if args.check_boto3 or not any([args.check_aws_cli, args.check_docker]):
        print(f"boto3: {boto3.__version__}")
        print(f"botocore: {botocore.__version__}")
    if args.check_aws_cli or not any([args.check_boto3, args.check_docker]):
        aws_path = shutil.which("aws")
        print(f"aws CLI: {aws_path or 'not found on PATH'}")
    if args.check_docker:
        docker_path = shutil.which("docker")
        print(f"docker: {docker_path or 'not found on PATH'}")
    try:
        import moto  # pylint: disable=unused-import  # noqa: F401

        print("moto: importable")
    except ImportError:
        print("moto: not importable (install dev deps to use moto-backed tests)")
    profiles = available_profiles()
    print(f"profiles: {', '.join(profiles) if profiles else '(none configured)'}")
    return 0


def run_list_profiles() -> int:
    """Print available AWS profiles, one per line."""
    for profile in available_profiles():
        print(profile)
    return 0


def run_list_regions(args: argparse.Namespace | None = None) -> int:
    """Print known AWS regions, one per line."""
    partition = getattr(args, "partition", "aws") if args else "aws"
    for region in available_regions(partition=partition):
        print(region)
    return 0


def available_profiles() -> list[str]:
    """Best-effort profile list from boto3's session."""
    try:
        session = boto3.Session()
        return list(session.available_profiles)
    except Exception:  # pylint: disable=broad-exception-caught
        return []


def available_regions(service: str = "ec2", partition: str = "aws") -> list[str]:
    """Known regions for ``service`` in ``partition`` (EC2 is the most-supported default)."""
    try:
        session = boto3.Session()
        return sorted(session.get_available_regions(service, partition_name=partition))
    except Exception:  # pylint: disable=broad-exception-caught
        return []


if __name__ == "__main__":
    raise SystemExit(main())
