"""Logging configuration for gui4aws."""

from __future__ import annotations

import logging
from pathlib import Path

__all__ = ["configure_logging"]


class Formatter(logging.Formatter):
    """Like the standard Formatter but adds %(shortname)s — the last two logger name segments."""

    def format(self, record: logging.LogRecord) -> str:
        parts = record.name.split(".")
        record.shortname = ".".join(parts[-2:]) if len(parts) >= 2 else record.name
        return super().format(record)


def configure_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    """Configure root logging for the application.

    Idempotent: calling twice does not duplicate handlers.

    Args:
        level: Standard logging level name ("DEBUG", "INFO", "WARNING", "ERROR").
        log_file: If given, also write to this file (in addition to stderr).
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(numeric_level)

    # botocore emits credential-resolution chatter at INFO that floods the console.
    # Push it to WARNING unless the user explicitly asked for DEBUG.
    if numeric_level > logging.DEBUG:
        logging.getLogger("botocore").setLevel(logging.WARNING)
        logging.getLogger("boto3").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    fmt = "%(asctime)s %(levelname)-5s %(shortname)s: %(message)s"
    formatter = Formatter(fmt, datefmt="%H:%M:%S")

    has_stream = any(isinstance(handler, logging.StreamHandler) for handler in root.handlers)
    if not has_stream:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        already_attached = any(
            isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == log_file.resolve()
            for handler in root.handlers
        )
        if not already_attached:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
