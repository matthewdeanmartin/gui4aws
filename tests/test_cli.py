"""Smoke tests for the CLI entry point."""

from __future__ import annotations


def test_import() -> None:
    """Package can be imported."""
    import gui4aws  # noqa: F401  # pylint: disable=unused-import


def test_version() -> None:
    """Package exposes a version string."""
    from gui4aws.__about__ import __version__

    assert isinstance(__version__, str)
    assert __version__


def test_build_parser_has_subcommands() -> None:
    """The CLI parser exposes gui/doctor/list-profiles/list-regions."""
    from gui4aws.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["gui", "--region", "us-east-2", "--mode", "boto3"])
    assert args.command == "gui"
    assert args.region == "us-east-2"
    assert args.mode == "boto3"


def test_doctor_runs(capsys: object) -> None:
    """``doctor`` prints diagnostics without raising."""
    from gui4aws.cli import main

    exit_code = main(["doctor"])
    assert exit_code == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "gui4aws version" in out
