"""Connection string discovery from keyring and AWS Secrets Manager."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

KEYRING_SERVICE = "gui4aws"

# Keys that must be present for a secret to be treated as a DB connection string.
_REQUIRED_KEYS = {"host", "username"}
_ENGINE_KEYS = {"engine", "dbEngine", "dbInstanceIdentifier", "dbClusterIdentifier"}


@dataclass(frozen=True)
class ConnectionInfo:
    """Parsed database connection parameters."""

    host: str
    port: int
    username: str
    password: str
    database: str
    engine: str  # "mysql" | "postgresql"
    source: str  # "keyring:<key>" or "aws_secret:<name>"

    @classmethod
    def from_dict(cls, data: dict[str, Any], source: str) -> ConnectionInfo:
        """Parse a connection-string dict into a ConnectionInfo."""
        host = str(data.get("host") or data.get("hostname") or "")
        username = str(data.get("username") or data.get("user") or "")
        password = str(data.get("password") or "")
        database = str(data.get("dbname") or data.get("database") or "")
        raw_engine = str(data.get("engine") or data.get("dbEngine") or data.get("db_engine") or "").lower()
        port_raw = data.get("port")
        if raw_engine in {"aurora-postgresql", "aurora-postgres", "postgresql", "postgres"}:
            engine = "postgresql"
            default_port = 5432
        else:
            engine = "mysql"
            default_port = 3306
        try:
            port = int(port_raw) if port_raw is not None else default_port
        except (ValueError, TypeError):
            port = default_port
        return cls(
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
            engine=engine,
            source=source,
        )


def _is_connection_dict(data: Any) -> bool:
    """Return True if *data* looks like a DB connection-string dict."""
    if not isinstance(data, dict):
        return False
    keys = set(data.keys())
    if not _REQUIRED_KEYS.issubset(keys):
        return False
    has_engine = bool(keys & _ENGINE_KEYS)
    has_host_like = "host" in keys or "hostname" in keys
    return has_engine or (has_host_like and ("password" in keys or "port" in keys))


def _try_parse_json(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


# ── keyring ──────────────────────────────────────────────────────────────────


def list_keyring_sources() -> list[str]:
    """Return keyring usernames stored under KEYRING_SERVICE that look like connection strings."""
    try:
        import keyring
    except ImportError:
        return []
    try:
        cred = keyring.get_credential(KEYRING_SERVICE, None)
    except Exception:  # pylint: disable=broad-exception-caught
        return []
    results: list[str] = []
    if cred is not None and cred.password:
        parsed = _try_parse_json(cred.password)
        if parsed and _is_connection_dict(parsed):
            results.append(cred.username)
    return results


def load_from_keyring(username: str) -> ConnectionInfo | None:
    """Load and parse a connection string stored in keyring."""
    try:
        import keyring
    except ImportError:
        return None
    pw = keyring.get_password(KEYRING_SERVICE, username)
    if pw is None:
        return None
    parsed = _try_parse_json(pw)
    if parsed is None or not _is_connection_dict(parsed):
        return None
    return ConnectionInfo.from_dict(parsed, source=f"keyring:{username}")


def save_to_keyring(username: str, conn_dict: dict[str, Any]) -> None:
    """Persist a connection-string dict to keyring."""
    try:
        import keyring
    except ImportError:
        logger.warning("keyring not installed; cannot save connection string")
        return
    keyring.set_password(KEYRING_SERVICE, username, json.dumps(conn_dict))
    logger.info("saved connection string to keyring service=%r username=%r", KEYRING_SERVICE, username)


# ── AWS Secrets Manager ───────────────────────────────────────────────────────


def list_aws_secret_sources(boto3_session: Any) -> list[str]:
    """Return secret names in Secrets Manager that look like DB connection strings."""
    try:
        client = boto3_session.client("secretsmanager")
        paginator = client.get_paginator("list_secrets")
        candidates: list[str] = []
        for page in paginator.paginate():
            for secret in page.get("SecretList", []):
                name = secret.get("Name", "")
                if not name:
                    continue
                try:
                    value_resp = client.get_secret_value(SecretId=name)
                    text = value_resp.get("SecretString", "")
                    if text:
                        parsed = _try_parse_json(text)
                        if parsed and _is_connection_dict(parsed):
                            candidates.append(name)
                except Exception:  # pylint: disable=broad-exception-caught  # nosec B112
                    # One secret we can't read (e.g. AccessDenied) must not abort the
                    # whole scan — skip it and keep discovering connection strings.
                    continue
        return candidates
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("failed to list AWS secrets for SQL runner")
        return []


def load_from_aws_secret(boto3_session: Any, secret_name: str) -> ConnectionInfo | None:
    """Fetch and parse a connection string from AWS Secrets Manager."""
    try:
        client = boto3_session.client("secretsmanager")
        resp = client.get_secret_value(SecretId=secret_name)
        text = resp.get("SecretString", "")
        parsed = _try_parse_json(text)
        if parsed is None or not _is_connection_dict(parsed):
            return None
        return ConnectionInfo.from_dict(parsed, source=f"aws_secret:{secret_name}")
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("failed to load secret %r", secret_name)
        return None


# ── execution ─────────────────────────────────────────────────────────────────


def execute_query(conn_info: ConnectionInfo, sql: str, limit: int = 500) -> tuple[list[str], list[tuple[Any, ...]]]:
    """Run *sql* and return (columns, rows).

    Tries pg8000 for PostgreSQL and pymysql for MySQL.  Raises ImportError with
    a helpful message if the required driver is not installed.
    """
    if conn_info.engine == "postgresql":
        return _exec_postgresql(conn_info, sql, limit)
    return _exec_mysql(conn_info, sql, limit)


def _exec_postgresql(conn_info: ConnectionInfo, sql: str, limit: int) -> tuple[list[str], list[tuple[Any, ...]]]:
    try:
        import pg8000  # type: ignore[import-not-found]
        import pg8000.native  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "pg8000 is required for PostgreSQL queries.\n" "Install it with:  uv add pg8000  (or  pip install pg8000)"
        ) from exc
    conn = pg8000.dbapi.connect(
        host=conn_info.host,
        port=conn_info.port,
        user=conn_info.username,
        password=conn_info.password,
        database=conn_info.database or "postgres",
        ssl_context=True,
    )
    try:
        cur = conn.cursor()
        cur.execute(sql)
        columns: list[str] = [str(d[0]) for d in (cur.description or [])]
        rows = cur.fetchmany(limit)
        return columns, [tuple(r) for r in rows]
    finally:
        conn.close()


def _exec_mysql(conn_info: ConnectionInfo, sql: str, limit: int) -> tuple[list[str], list[tuple[Any, ...]]]:
    try:
        import pymysql  # type: ignore[import-untyped]
        import pymysql.cursors  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "PyMySQL is required for MySQL/Aurora-MySQL queries.\n"
            "Install it with:  uv add pymysql  (or  pip install pymysql)"
        ) from exc
    conn = pymysql.connect(
        host=conn_info.host,
        port=conn_info.port,
        user=conn_info.username,
        password=conn_info.password,
        database=conn_info.database or None,
        ssl={"ssl": True},
        cursorclass=pymysql.cursors.Cursor,
    )
    try:
        cur = conn.cursor()
        cur.execute(sql)
        columns = [d[0] for d in (cur.description or [])]
        rows = cur.fetchmany(limit)
        return columns, [tuple(r) for r in rows]
    finally:
        conn.close()
