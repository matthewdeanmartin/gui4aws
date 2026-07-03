"""Smoke tests for the CLI entry point."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


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


def test_build_parser_has_upgrade_subcommands() -> None:
    """The CLI parser exposes integrated update-checking subcommands."""
    from gui4aws.cli import build_parser

    parser = build_parser()
    upgrade_args = parser.parse_args(["upgrade", "--check"])
    check_args = parser.parse_args(["check-updates", "--no-network"])

    assert upgrade_args.command == "upgrade"
    assert upgrade_args._diu_check is True
    assert check_args.command == "check-updates"
    assert check_args._diu_no_network is True


def test_doctor_runs(capsys: object) -> None:
    """``doctor`` prints diagnostics without raising."""
    from gui4aws.cli import main

    exit_code = main(["doctor"])
    assert exit_code == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "gui4aws version" in out


def test_upgrade_command_dispatches() -> None:
    """Integrated update commands should return the dispatcher exit code."""
    from gui4aws import cli

    with patch("gui4aws.cli.run_command", return_value=10) as dispatcher:
        exit_code = cli.main(["upgrade", "--check"])

    assert exit_code == 10
    dispatcher.assert_called_once()


def test_run_gui_emits_terminal_and_tk_notices(capsys: object) -> None:
    """GUI launch should print terminal notices and schedule a Tk notice."""
    from gui4aws import cli

    fake_window = MagicMock()
    fake_window.root = MagicMock()
    startup_marker = object()
    exit_marker = object()

    def fake_render_notice(report: object | None) -> str:
        if report is startup_marker:
            return "startup notice"
        if report is exit_marker:
            return "exit notice"
        return ""

    with (
        patch("gui4aws.config.load_config") as load_config,
        patch("gui4aws.config.network_config_from_app_config") as network_from_config,
        patch("gui4aws.cli.available_profiles", return_value=["default"]),
        patch("gui4aws.cli.available_regions", return_value=["us-east-1"]),
        patch("gui4aws.gui.main_window.create_main_window", return_value=fake_window),
        patch("gui4aws.cli.startup_report", return_value=startup_marker),
        patch("gui4aws.cli.exit_report", return_value=exit_marker),
        patch("gui4aws.cli.render_notice", side_effect=fake_render_notice),
        patch("gui4aws.cli.schedule_tk_notice") as schedule_tk_notice,
    ):
        load_config.return_value.default_profile = ""
        load_config.return_value.default_partition = "aws"
        load_config.return_value.default_region = "us-east-1"
        load_config.return_value.default_mode = "boto3"
        load_config.return_value.default_endpoint_mode = "aws"
        network_from_config.return_value = MagicMock()

        parser = cli.build_parser()
        args = parser.parse_args(["gui"])
        exit_code = cli.run_gui(args)

    assert exit_code == 0
    fake_window.run.assert_called_once()
    schedule_tk_notice.assert_called_once_with(fake_window.root, startup_marker)
    assert capsys.readouterr().err == "startup notice\nexit notice\n"  # type: ignore[attr-defined]
