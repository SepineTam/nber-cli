#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam (谭淞)
# @Email  : sepinetam@gmail.com
# @File   : cli.py

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from importlib import metadata
from importlib.metadata import version as get_version
from pathlib import Path
from collections.abc import Callable
from typing import Literal, TypedDict, cast

from aiohttp import ClientError, ClientResponseError
from packaging.version import InvalidVersion, parse as parse_version

from .config import config_store
from .db import db
from .core.models import DownloadBatchResult, NBERFeedCleanResult, NBERInfoCacheClearResult
from .fetch import download_multiple_papers, download_paper, download_paper_to_file
from .fetch import clean_feed_cache, fetch_feed
from .fetch import search_nber
from .utils import (
    feed_results,
    feed_results_text,
    info,
    info_text,
    related,
    search_results,
    search_results_text,
)
from .db import get_paper_with_info_cache_result
from .utils import configure_logging

logger = logging.getLogger(__name__)

_OUTPUT_FORMATS = ["list", "json"]
_PYPI_JSON_URL = "https://pypi.org/pypi/nber-cli/json"
_PYPI_REQUEST_HEADERS = {
    "User-Agent": "nber-cli doctor",
    "Accept": "application/json",
}
_UPGRADE_TIMEOUT_SECONDS = 120


class _FeedCleanOptions(TypedDict):
    days: int | None
    delete_all: bool
    start_date: str | None
    end_date: str | None


class _InfoCacheClearOptions(TypedDict):
    days: int | None
    delete_all: bool
    start_date: str | None
    end_date: str | None


def _get_version() -> str:
    try:
        return get_version("nber-cli")
    except Exception:
        return "0.10.0"


def _parse_database_location(value: str) -> Path | str:
    if value.startswith("sqlite:"):
        return value
    return Path(value)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nber-cli",
        description="Download NBER papers from the command line.",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"NBER CLI v{_get_version()}"
    )

    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging for debugging."
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        help="Path to a custom config file for this run only.",
    )

    subparsers = parser.add_subparsers(dest="command")

    download_parser = subparsers.add_parser("download", help="Download one or more NBER papers.")
    download_parser.add_argument("paper_id", nargs="?", help="Single paper ID, e.g. w1234.")
    download_parser.add_argument(
        "--file", "-f", dest="file_path", type=Path, help="Explicit target file path."
    )
    download_parser.add_argument(
        "--save-base",
        "-s",
        dest="save_base",
        type=Path,
        default=Path.cwd(),
        help="Target directory to save PDF files. Defaults to current working directory.",
    )
    download_parser.add_argument("--batch", "-b", nargs="+", dest="batch_ids", help="Batch paper IDs.")
    download_parser.add_argument(
        "--restrict",
        type=_parse_bool,
        default=True,
        dest="restrict",
        help="Restrict downloads to the current directory (default: true).",
    )
    download_parser.add_argument(
        "--concurrency",
        "-c",
        type=_parse_positive_int,
        default=None,
        dest="concurrency",
        help="Maximum concurrent downloads. Overrides config value.",
    )

    info_parser = subparsers.add_parser("info", help="Show information about an NBER paper.")
    info_parser.add_argument("paper_id", help="Paper ID, e.g. w1234, or 'cache' to manage cache.")
    info_parser.add_argument(
        "cache_action",
        nargs="?",
        choices=["clear", "clean", "status"],
        help=argparse.SUPPRESS,
    )
    info_parser.add_argument(
        "--all", "-a", action="store_true", dest="show_all", help="Show all fields including related."
    )
    info_parser.add_argument(
        "--refresh",
        action="store_true",
        dest="refresh",
        help="Refresh paper info from NBER and update the cache when enabled.",
    )
    info_parser.add_argument(
        "--format",
        "-f",
        choices=_OUTPUT_FORMATS,
        default="list",
        dest="output_format",
        help="Output format (default: list).",
    )
    info_cache_group = info_parser.add_mutually_exclusive_group()
    info_cache_group.add_argument(
        "--turn-on",
        action="store_true",
        dest="cache_turn_on",
        help="Enable the info cache globally.",
    )
    info_cache_group.add_argument(
        "--turn-off",
        action="store_true",
        dest="cache_turn_off",
        help="Disable the info cache globally.",
    )
    info_cache_group.add_argument(
        "--set-refresh",
        type=_parse_positive_int,
        default=None,
        dest="cache_ttl_days",
        help="Set the info cache refresh interval in days.",
    )
    info_parser.add_argument(
        "--days",
        type=_parse_positive_int,
        default=None,
        help="Clear cached info records fetched more than this many days ago.",
    )
    info_parser.add_argument(
        "--start-date",
        dest="start_date",
        help="Clear cached info records fetched on or after this date (YYYY-MM-DD).",
    )
    info_parser.add_argument(
        "--end-date",
        dest="end_date",
        help="Clear cached info records fetched on or before this date (YYYY-MM-DD).",
    )

    search_parser = subparsers.add_parser("search", help="Search NBER working papers.")
    search_parser.add_argument("query", help="Title, number, author, abstract, or keyword.")
    search_parser.add_argument(
        "--start-date",
        "--start",
        dest="start_date",
        help="Only include papers on or after this date (YYYY-MM-DD).",
    )
    search_parser.add_argument(
        "--end-date",
        "--end",
        dest="end_date",
        help="Only include papers on or before this date (YYYY-MM-DD).",
    )
    search_parser.add_argument("--page", type=int, default=1, help="Result page to fetch.")
    search_parser.add_argument(
        "--per-page",
        type=int,
        default=20,
        choices=[20, 50, 100],
        dest="per_page",
        help="Number of results per page.",
    )
    search_parser.add_argument(
        "--format",
        "-f",
        choices=_OUTPUT_FORMATS,
        default="list",
        dest="output_format",
        help="Output format (default: list).",
    )

    db_parser = subparsers.add_parser("db", help="Manage the local NBER database.")
    db_subparsers = db_parser.add_subparsers(dest="db_command", required=True)

    db_init_parser = db_subparsers.add_parser("init", help="Initialize the database.")
    db_init_parser.add_argument(
        "--db-path",
        type=_parse_database_location,
        default=None,
        help="SQLite database path or sqlite:/// URL. Defaults to ~/.nber-cli/nber.db.",
    )

    db_migrate_parser = db_subparsers.add_parser(
        "migrate",
        help="Move the database to a new path and update config.",
    )
    db_migrate_parser.add_argument(
        "new_db_path",
        type=_parse_database_location,
        help="New SQLite database path or sqlite:/// URL.",
    )

    feed_parser = subparsers.add_parser("feed", help="Manage the NBER working papers RSS feed.")
    feed_subparsers = feed_parser.add_subparsers(dest="feed_command", required=True)

    feed_clean_parser = feed_subparsers.add_parser(
        "clean",
        help="Clean cached feed database records.",
    )
    feed_clean_parser.add_argument(
        "--days",
        type=_parse_positive_int,
        default=None,
        help="Clean cached records not seen for this many days (default: 30).",
    )
    feed_clean_parser.add_argument(
        "--all",
        action="store_true",
        dest="delete_all",
        help="Clean all cached feed database records.",
    )
    feed_clean_parser.add_argument(
        "--start-date",
        dest="start_date",
        help="Clean cached records last seen on or after this date (YYYY-MM-DD).",
    )
    feed_clean_parser.add_argument(
        "--end-date",
        dest="end_date",
        help="Clean cached records last seen on or before this date (YYYY-MM-DD).",
    )

    feed_fetch_parser = feed_subparsers.add_parser(
        "fetch",
        help="Fetch the NBER RSS feed.",
        allow_abbrev=False,
    )
    feed_fetch_parser.add_argument(
        "--display-all",
        nargs="?",
        const="true",
        default=None,
        type=_parse_bool,
        help=(
            "Display all fetched items instead of only new items "
            "(true/false; defaults to true when --max-items is set, otherwise false)."
        ),
    )
    feed_fetch_parser.add_argument(
        "--format",
        "-f",
        choices=_OUTPUT_FORMATS,
        default="list",
        dest="output_format",
        help="Output format (default: list).",
    )
    feed_fetch_parser.add_argument(
        "--max-items",
        type=_parse_non_negative_int,
        default=None,
        dest="max_items",
        help="Maximum number of feed items to display.",
    )

    mcp_parser = subparsers.add_parser("mcp-server", help="Start the MCP server.")
    mcp_parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport mechanism (default: stdio).",
    )
    mcp_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP transports (default: 8000).",
    )
    mcp_parser.add_argument(
        "--yes",
        action="store_true",
        dest="confirm_port",
        help="Confirm use of a custom port.",
    )

    config_parser = subparsers.add_parser("config", help="Manage configuration.")
    config_subparsers = config_parser.add_subparsers(dest="config_command")

    config_subparsers.add_parser("show", help="Print current configuration.")

    config_get_parser = config_subparsers.add_parser("get", help="Get a configuration value.")
    config_get_parser.add_argument("key", help="Dot-separated key, e.g. download.restrict_dir")

    config_set_parser = config_subparsers.add_parser("set", help="Set a configuration value.")
    config_set_parser.add_argument("key", help="Dot-separated key, e.g. download.restrict_dir")
    config_set_parser.add_argument("value", help="Value to set.")

    config_subparsers.add_parser("verify", help="Validate configuration against schema.")

    doctor_parser = subparsers.add_parser("doctor", help="Show environment and configuration diagnostics.")
    doctor_parser.add_argument(
        "--fix-version",
        action="store_true",
        dest="fix_version",
        help="Upgrade nber-cli with the detected installer when PyPI has a newer version.",
    )

    return parser


def _resolve_paper_ids(single_id: str | None, batch_ids: list[str] | None) -> list[str]:
    if batch_ids:
        return batch_ids
    if single_id:
        return [single_id]
    return []


_PAPER_ID_RE = re.compile(r"^w?\d+$", re.IGNORECASE)


def _parse_paper_id(paper_id_str: str) -> int:
    if not _PAPER_ID_RE.fullmatch(paper_id_str):
        raise ValueError(f"invalid paper ID: {paper_id_str}")
    cleaned = paper_id_str.lower().removeprefix("w")
    return int(cleaned)


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def _parse_non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected a non-negative integer") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("expected a non-negative integer")
    return parsed


def _parse_positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected a positive integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return parsed


def _infer_config_value(value: str) -> bool | int | str:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(value)
    except ValueError:
        return value


def _print_download_success(paper_id: str, output_file: Path) -> None:
    print(f"Successfully downloaded {paper_id} to {output_file}")


def _format_download_error(paper_id: str, error: BaseException) -> str:
    if isinstance(error, ClientResponseError):
        if error.status == 403:
            return (
                f"Failed to download {paper_id}: no permission to access this paper "
                "(HTTP 403). It may still be in NBER's first-week access restriction."
            )
        if error.status == 404:
            return f"Failed to download {paper_id}: paper not found (HTTP 404)."

        error_message = error.message or "HTTP error"
        return f"Failed to download {paper_id}: HTTP {error.status} {error_message}."

    if isinstance(error, TimeoutError):
        return f"Failed to download {paper_id}: request timed out."

    if isinstance(error, (ClientError, ConnectionError)):
        return f"Failed to download {paper_id}: network error."

    if isinstance(error, asyncio.CancelledError):
        return f"Failed to download {paper_id}: download cancelled."

    return f"Failed to download {paper_id}: {error.__class__.__name__}."


def _run_single_download(paper_id: str, output_file: Path | None, save_base: Path, *, restrict_dir: bool = True) -> None:
    try:
        if output_file is not None:
            downloaded_file = asyncio.run(download_paper_to_file(paper_id, output_file, restrict_dir=restrict_dir))
        else:
            downloaded_file = asyncio.run(download_paper(paper_id, save_base, restrict_dir=restrict_dir))
    except (asyncio.CancelledError, Exception) as error:
        error_msg = _format_download_error(paper_id, error)
        db.record_download(None, paper_id, "failed", error=error_msg)
        print(error_msg, file=sys.stderr)
        raise SystemExit(1) from error

    db.record_download(None, paper_id, "success", saved_path=str(downloaded_file))
    _print_download_success(paper_id, downloaded_file)


def _handle_download_errors(batch_result: DownloadBatchResult, paper_ids: list[str]) -> None:
    for output_file in batch_result.paths:
        db.record_download(None, output_file.stem, "success", saved_path=str(output_file))
        _print_download_success(output_file.stem, output_file)

    for failure in batch_result.failures:
        error_msg = _format_download_error(failure.paper_id, failure.error)
        db.record_download(None, failure.paper_id, "failed", error=error_msg)
        print(error_msg, file=sys.stderr)

    if batch_result.failures:
        print(
            f"Downloaded {len(batch_result.paths)} of {len(paper_ids)} papers; "
            f"{len(batch_result.failures)} failed.",
            file=sys.stderr,
        )


def _run_mcp_server(transport: str, port: int) -> None:
    from .mcp import create_mcp_server

    mcp_server = create_mcp_server(include_download=transport == "stdio")
    mcp_server.settings.port = port
    mcp_server.run(transport=cast(Literal["stdio", "sse", "streamable-http"], transport))


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _get_latest_pypi_version() -> str | None:
    request = urllib.request.Request(_PYPI_JSON_URL, headers=_PYPI_REQUEST_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = getattr(response, "status", None)
            if status is None and hasattr(response, "getcode"):
                status = response.getcode()
            if status != 200:
                reason = getattr(response, "reason", "")
                logger.warning("failed to fetch PyPI version: HTTP %s %s", status, reason)
                return None
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        logger.warning("failed to fetch PyPI version: HTTP %s %s", error.code, error.reason)
        return None
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError) as error:
        logger.warning("failed to fetch PyPI version: %s", error)
        return None
    info_payload = payload.get("info") if isinstance(payload, dict) else None
    version = info_payload.get("version") if isinstance(info_payload, dict) else None
    return version if isinstance(version, str) and version else None


def _is_latest_version(current_version: str, latest_version: str | None) -> bool | None:
    if latest_version is None:
        return None
    try:
        return parse_version(current_version) >= parse_version(latest_version)
    except InvalidVersion as error:
        logger.warning("failed to compare versions: %s", error)
        return None


def _format_bytes(size: int | None) -> str:
    if size is None:
        return "unknown"
    units = ["B", "KiB", "MiB", "GiB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
        value /= 1024
    return f"{size} B"


def _read_db_last_run(db_path: Path) -> str | None:
    if not db_path.exists():
        return None
    queries = [
        "SELECT MAX(created_at) FROM query_log",
        "SELECT MAX(created_at) FROM download_log",
        "SELECT MAX(created_at) FROM info_log",
        "SELECT MAX(fetched_at) FROM feed_fetches",
    ]
    values: list[str] = []
    try:
        with sqlite3.connect(db_path) as connection:
            for query in queries:
                try:
                    row = connection.execute(query).fetchone()
                except sqlite3.DatabaseError:
                    continue
                if row and isinstance(row[0], str):
                    values.append(row[0])
    except sqlite3.DatabaseError as error:
        logger.warning("failed to inspect database activity: %s", error)
        return None
    return max(values) if values else None


def _safe_doctor_value(label: str, callback: Callable[[], object], fallback: object = "unknown") -> object:
    try:
        return callback()
    except Exception as error:
        logger.warning("doctor failed to read %s: %s", label, error)
        return fallback


def _doctor_payload() -> dict[str, object]:
    current_version = _get_version()
    latest_version = _get_latest_pypi_version()
    command_path = shutil.which("nber-cli")
    package_path = Path(__file__).resolve().parent
    config_path = config_store.default_config_path()
    config = _safe_doctor_value("config", config_store.read_config, {})
    db_path_value = _safe_doctor_value("database path", db.get_database_path, None)
    db_path = db_path_value if isinstance(db_path_value, Path) else None
    db_exists = _safe_doctor_value("database existence", lambda: db_path.exists() if db_path else False, False)
    db_size = _safe_doctor_value(
        "database size",
        lambda: db_path.stat().st_size if db_path and db_path.exists() else None,
    )
    supported_schema_version = db.SCHEMA_VERSION
    actual_schema_version = _safe_doctor_value("database schema version", db.get_schema_version, "unknown")
    last_run_at = _safe_doctor_value(
        "database activity",
        lambda: _read_db_last_run(db_path) if db_path else None,
    )
    is_latest = _is_latest_version(current_version, latest_version)
    return {
        "current_version": current_version,
        "latest_pypi_version": latest_version or "unknown",
        "is_latest": is_latest if is_latest is not None else "unknown",
        "command_path": command_path or "not found on PATH",
        "package_path": str(package_path),
        "python_executable": sys.executable,
        "config_path": str(config_path),
        "config": config,
        "database_path": str(db_path) if db_path else "unknown",
        "database_exists": db_exists,
        "supported_schema_version": supported_schema_version,
        "database_schema_version": actual_schema_version,
        "database_size": _format_bytes(db_size if isinstance(db_size, int) else None),
        "last_run_at": last_run_at or "unknown",
    }


def _print_doctor(payload: dict[str, object]) -> None:
    print("NBER CLI Doctor")
    print(f"Current version: {payload['current_version']}")
    print(f"Latest PyPI version: {payload['latest_pypi_version']}")
    print(f"Command path: {payload['command_path']}")
    print(f"Package path: {payload['package_path']}")
    print(f"Python executable: {payload['python_executable']}")
    print(f"Config path: {payload['config_path']}")
    print("Config:")
    print(json.dumps(payload["config"], ensure_ascii=False, indent=2))
    print(f"Database path: {payload['database_path']}")
    print(f"Database exists: {str(payload['database_exists']).lower()}")
    print(f"Supported schema version: {payload['supported_schema_version']}")
    print(f"Database schema version: {payload['database_schema_version']}")
    supported_schema_version = payload["supported_schema_version"]
    database_schema_version = payload["database_schema_version"]
    if (
        isinstance(supported_schema_version, int)
        and isinstance(database_schema_version, int)
        and database_schema_version > supported_schema_version
    ):
        print(
            "Warning: database schema "
            f"({database_schema_version}) is newer than supported by this version "
            f"({supported_schema_version})."
        )
    print(f"Database size: {payload['database_size']}")
    print(f"Last run at: {payload['last_run_at']}")


def _detect_upgrade_command() -> list[str]:
    if _is_running_under_uvx():
        return ["uvx", "--refresh", "nber-cli", "-v"]
    if _is_uv_tool_install():
        return ["uv", "tool", "upgrade", "nber-cli"]
    if _is_pipx_install():
        return ["pipx", "upgrade", "nber-cli"]
    if _is_pip_install():
        return [sys.executable, "-m", "pip", "install", "--upgrade", "nber-cli"]
    return []


def _read_pyvenv_cfg() -> str:
    pyvenv_cfg = Path(sys.prefix) / "pyvenv.cfg"
    try:
        return pyvenv_cfg.read_text(encoding="utf-8").lower()
    except OSError:
        return ""


def _distribution_direct_url() -> str:
    try:
        dist = metadata.distribution("nber-cli")
    except metadata.PackageNotFoundError:
        return ""
    try:
        direct_url = dist.read_text("direct_url.json")
    except OSError:
        return ""
    return direct_url.lower() if direct_url else ""


def _distribution_installer() -> str:
    try:
        dist = metadata.distribution("nber-cli")
    except metadata.PackageNotFoundError:
        return ""
    try:
        installer = dist.read_text("INSTALLER")
    except OSError:
        return ""
    return installer.strip().lower() if installer else ""


def _is_running_under_uvx() -> bool:
    if Path(sys.argv[0]).name.lower() == "uvx":
        return True
    if "UV_RUN_RECURSION" in os.environ or "UV_PROJECT_ENVIRONMENT" in os.environ:
        return "tool" not in _read_pyvenv_cfg()
    direct_url = _distribution_direct_url()
    return "uvx" in direct_url


def _is_uv_tool_install() -> bool:
    pyvenv_cfg = _read_pyvenv_cfg()
    direct_url = _distribution_direct_url()
    return "uv tool" in pyvenv_cfg or "uv-tool" in pyvenv_cfg or "uv tool" in direct_url


def _is_pipx_install() -> bool:
    if "PIPX_HOME" in os.environ or "PIPX_BIN_DIR" in os.environ:
        return True
    pyvenv_cfg = _read_pyvenv_cfg()
    direct_url = _distribution_direct_url()
    return "pipx" in pyvenv_cfg or "pipx" in direct_url


def _is_pip_install() -> bool:
    return _distribution_installer() == "pip"


def _manual_upgrade_message() -> str:
    return (
        "Could not determine how nber-cli was installed. Please upgrade manually with one of:\n"
        "  uvx --refresh nber-cli -v\n"
        "  uv tool upgrade nber-cli\n"
        "  pipx upgrade nber-cli\n"
        "  python -m pip install --upgrade nber-cli"
    )


def _get_subprocess_cli_version() -> str | None:
    executable = shutil.which("nber-cli")
    if executable is None:
        return None
    try:
        result = subprocess.run(
            [executable, "--version"],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        logger.warning("failed to check upgraded nber-cli version: %s", error)
        return None
    if result.returncode != 0:
        logger.warning("failed to check upgraded nber-cli version: %s", result.stderr)
        return None
    match = re.search(r"v?(\d+(?:\.\d+)*(?:[a-zA-Z0-9_.!+-]*)?)", result.stdout)
    return match.group(1) if match else None


def _fix_doctor_version() -> None:
    payload = _doctor_payload()
    _print_doctor(payload)
    if payload["latest_pypi_version"] == "unknown":
        print("Cannot check for upgrades because the latest PyPI version is unknown.", file=sys.stderr)
        raise SystemExit(1)
    if payload["is_latest"] is True:
        print("Version is already up to date.")
        return

    command = _detect_upgrade_command()
    if not command:
        print(_manual_upgrade_message(), file=sys.stderr)
        raise SystemExit(1)
    print(f"Running upgrade command: {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=_UPGRADE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        logger.error("upgrade command timed out after %s seconds", error.timeout)
        print(f"Upgrade timed out after {error.timeout} seconds. See the debug log for details.", file=sys.stderr)
        raise SystemExit(1) from error
    except OSError as error:
        logger.exception("failed to run upgrade command")
        print(f"Failed to run upgrade command: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        logger.error("upgrade command failed with exit code %s: %s", result.returncode, result.stderr)
        print(f"Upgrade failed with exit code {result.returncode}. See the debug log for details.", file=sys.stderr)
        raise SystemExit(1)

    refreshed_version = _get_subprocess_cli_version()
    latest_version = str(payload["latest_pypi_version"])
    refreshed_is_latest = _is_latest_version(refreshed_version or "", latest_version) if refreshed_version else None
    if refreshed_is_latest is not True:
        logger.error(
            "upgrade command finished but version check did not confirm latest: current=%s latest=%s",
            refreshed_version or "unknown",
            latest_version,
        )
        print(
            "Upgrade command finished, but the current shell did not confirm the latest version. "
            "Please rerun nber-cli to use the new version.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    print("nber-cli is up to date.")


def _info_payload(paper, include_all: bool) -> dict:
    result = info(paper)
    if include_all:
        result.update(related(paper))
        if paper.published_version:
            result["published_version"] = paper.published_version
    return result


def _feed_clean_options(args: argparse.Namespace) -> _FeedCleanOptions:
    return {
        "days": args.days,
        "delete_all": args.delete_all,
        "start_date": args.start_date,
        "end_date": args.end_date,
    }


def _info_cache_clear_options(
    args: argparse.Namespace,
    *,
    delete_all: bool,
) -> _InfoCacheClearOptions:
    return {
        "days": args.days,
        "delete_all": delete_all,
        "start_date": args.start_date,
        "end_date": args.end_date,
    }


def _print_feed_clean_preview(result: NBERFeedCleanResult) -> None:
    print(f"Database: {result.database_path}")
    print(f"Matched cached records: {result.matched_count}")
    print("")
    if result.matched_count == 0:
        print("No cached records matched.")
        return

    print("This operation is irreversible.")
    print("Deleted cache records may be fetched again as new items if they still appear in the RSS feed.")


def _print_info_cache_clear_preview(result: NBERInfoCacheClearResult) -> None:
    print(f"Database: {result.database_path}")
    print(f"Matched cached records: {result.matched_count}")
    print("")
    if result.matched_count == 0:
        print("No cached records matched.")
        return

    print("This operation is irreversible.")
    print("Deleted info cache records may be fetched again from NBER.")


def _print_info_cache_status() -> None:
    settings = config_store.get_info_cache_settings()
    cache_state = "on" if settings.cache_enabled else "off"
    print(f"Cache: {cache_state}")
    print(f"TTL: {settings.cache_ttl_days} days")
    print(f"Cached rows: {db.count_info_cache()}")


def _confirm_feed_clean() -> bool:
    print("Continue? [y/N]: ", end="")
    return input().strip() in {"y", "Y"}


def _has_info_cache_clear_filter(args: argparse.Namespace) -> bool:
    return (
        args.show_all
        or args.days is not None
        or args.start_date is not None
        or args.end_date is not None
    )


def _has_info_cache_only_option(args: argparse.Namespace) -> bool:
    return (
        args.cache_action is not None
        or args.cache_turn_on
        or args.cache_turn_off
        or args.cache_ttl_days is not None
        or args.days is not None
        or args.start_date is not None
        or args.end_date is not None
    )


def _run_info_cache_clear(
    parser: argparse.ArgumentParser,
    clear_options: _InfoCacheClearOptions,
) -> None:
    try:
        preview = db.clear_info_cache(**clear_options, dry_run=True)
    except ValueError as error:
        parser.error(str(error))

    _print_info_cache_clear_preview(preview)
    if preview.matched_count == 0:
        return
    if not _confirm_feed_clean():
        print("Aborted.")
        return

    try:
        result = db.clear_info_cache(**clear_options)
    except ValueError as error:
        parser.error(str(error))
    print(f"Deleted cached records: {result.deleted_count}")


def _handle_info_cache_command(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    if args.refresh:
        parser.error("--refresh is only supported for paper info")
    if args.output_format != "list":
        parser.error("--format is only supported for paper info")

    actions = [
        args.cache_turn_on,
        args.cache_turn_off,
        args.cache_ttl_days is not None,
        args.cache_action is not None,
    ]
    if sum(actions) > 1:
        parser.error("choose only one info cache action")

    if args.cache_action != "clear" and _has_info_cache_clear_filter(args):
        parser.error("clear filters require 'info cache clear'")

    if args.cache_turn_on:
        config_store.set_info_cache_enabled(True)
        print("Info cache enabled.")
        return

    if args.cache_turn_off:
        config_store.set_info_cache_enabled(False)
        print("Info cache disabled.")
        return

    if args.cache_ttl_days is not None:
        try:
            config_store.set_info_cache_ttl_days(args.cache_ttl_days)
        except ValueError as error:
            parser.error(str(error))
        print(f"Info cache refresh interval set to {args.cache_ttl_days} days.")
        return

    if args.cache_action == "clear":
        clear_options = _info_cache_clear_options(args, delete_all=args.show_all)
        _run_info_cache_clear(parser, clear_options)
        return

    if args.cache_action == "clean":
        clear_options = _info_cache_clear_options(args, delete_all=True)
        _run_info_cache_clear(parser, clear_options)
        return

    _print_info_cache_status()


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.config is not None:
        config_store.set_cli_config_path(args.config)

    configure_logging(verbose=args.verbose)

    if args.command is None:
        parser.print_help()
        raise SystemExit(0)

    if args.command == "doctor":
        try:
            if args.fix_version:
                _fix_doctor_version()
            else:
                _print_doctor(_doctor_payload())
        except SystemExit:
            raise
        except Exception as error:
            logger.exception("doctor command failed")
            print(f"Doctor failed: {error.__class__.__name__}. See the debug log for details.", file=sys.stderr)
            raise SystemExit(1) from error
        return

    if args.command == "download":
        if args.paper_id and args.batch_ids:
            parser.error("cannot mix positional paper ID with --batch")

        if args.batch_ids and args.file_path is not None:
            parser.error("--file/-f is not supported with --batch")

        paper_ids = _resolve_paper_ids(args.paper_id, args.batch_ids)
        if not paper_ids:
            parser.error("download requires one paper ID or --batch with one or more IDs.")

        for paper_id in paper_ids:
            if not _PAPER_ID_RE.fullmatch(paper_id):
                parser.error(f"invalid paper ID '{paper_id}'")

        if len(paper_ids) > 1 and args.file_path is not None:
            parser.error("--file/-f is only supported for single downloads, not for --batch or multiple IDs.")

        restrict_dir = args.restrict

        if args.file_path is not None:
            _run_single_download(paper_ids[0], args.file_path, args.save_base, restrict_dir=restrict_dir)
            return

        if args.batch_ids is not None:
            batch_result = asyncio.run(
                download_multiple_papers(
                    paper_ids,
                    args.save_base,
                    restrict_dir=restrict_dir,
                    concurrency=args.concurrency,
                )
            )
            _handle_download_errors(batch_result, paper_ids)
            if batch_result.failures:
                raise SystemExit(1)
            return

        _run_single_download(paper_ids[0], None, args.save_base, restrict_dir=restrict_dir)
        return

    if args.command == "info":
        if args.paper_id == "cache":
            _handle_info_cache_command(parser, args)
            return

        if _has_info_cache_only_option(args):
            parser.error("info cache options require 'nber-cli info cache'")

        try:
            nber_id = _parse_paper_id(args.paper_id)
        except ValueError:
            parser.error(f"invalid paper ID '{args.paper_id}'")

        try:
            info_cache_result = asyncio.run(
                get_paper_with_info_cache_result(nber_id, refresh=args.refresh)
            )
        except Exception as error:
            print(f"Failed to fetch paper w{nber_id}: {error.__class__.__name__}.", file=sys.stderr)
            raise SystemExit(1) from None

        paper = info_cache_result.paper
        db.record_info(None, nber_id)

        if args.output_format == "json":
            _print_json(_info_payload(paper, args.show_all))
        else:
            print(info_text(paper, include_all=args.show_all))
        return

    if args.command == "search":
        logger.debug(
            "search query=%s page=%s per_page=%s",
            args.query,
            args.page,
            args.per_page,
        )
        try:
            results = asyncio.run(
                search_nber(
                    args.query,
                    start_date=args.start_date,
                    end_date=args.end_date,
                    page=args.page,
                    per_page=args.per_page,
                )
            )
        except ValueError as error:
            parser.error(str(error))
        logger.debug("search results count=%s", len(results.results))
        db.record_query(
            None,
            keyword=args.query,
            conditions={
                "start_date": args.start_date,
                "end_date": args.end_date,
                "page": args.page,
                "per_page": args.per_page,
            },
            result_count=len(results.results),
        )
        if args.output_format == "json":
            _print_json(search_results(results))
        else:
            print(search_results_text(results))
        return

    if args.command == "db":
        if args.db_command == "init":
            try:
                db_path = db.init_database(args.db_path)
            except ValueError as error:
                parser.error(str(error))
            print(f"Database initialized at {db_path}")
            return

        if args.db_command == "migrate":
            try:
                old_db_path, new_db_path = db.migrate_database(args.new_db_path)
            except ValueError as error:
                parser.error(str(error))
            print(f"Database migrated from {old_db_path} to {new_db_path}")
            return

    if args.command == "feed":
        if args.feed_command == "clean":
            clean_options = _feed_clean_options(args)
            try:
                preview = clean_feed_cache(**clean_options, dry_run=True)
            except ValueError as error:
                parser.error(str(error))

            _print_feed_clean_preview(preview)
            if preview.matched_count == 0:
                return
            if not _confirm_feed_clean():
                print("Aborted.")
                return

            try:
                result = clean_feed_cache(**clean_options)
            except ValueError as error:
                parser.error(str(error))
            print(f"Deleted cached records: {result.deleted_count}")
            return

        if args.feed_command == "fetch":
            try:
                display_all = (
                    args.display_all
                    if args.display_all is not None
                    else args.max_items is not None
                )
                fetch_result = fetch_feed(display_all=display_all, max_items=args.max_items)
            except ValueError as error:
                print(f"nber-cli: error: {error}", file=sys.stderr)
                raise SystemExit(1)
            if args.output_format == "json":
                _print_json(feed_results(fetch_result))
            else:
                print(feed_results_text(fetch_result))
            return

    if args.command == "config":
        if args.config_command == "show" or args.config_command is None:
            config = config_store.read_config()
            print(json.dumps(config, ensure_ascii=False, indent=2))
            return
        if args.config_command == "get":
            config = config_store.read_config()
            value = config_store.get_config_value(config, args.key)
            if value is None:
                print("")
                return
            if isinstance(value, bool):
                print(str(value).lower())
            elif isinstance(value, (str, int)):
                print(value)
            else:
                print(json.dumps(value, ensure_ascii=False))
            return
        if args.config_command == "set":
            config = config_store.read_config()
            typed_value = _infer_config_value(args.value)
            config_store.set_config_value(config, args.key, typed_value)
            config_store.write_config(config)
            print(f"Set {args.key} = {typed_value}")
            return
        if args.config_command == "verify":
            try:
                config = config_store.read_config_for_validation()
            except ValueError as error:
                print(error, file=sys.stderr)
                raise SystemExit(1)
            errors = config_store.validate_config(config)
            if errors:
                for message in errors:
                    print(message, file=sys.stderr)
                raise SystemExit(1)
            print("Configuration is valid.")
            return

    if args.command == "mcp-server":
        if args.port != 8000 and not args.confirm_port:
            print(
                "Custom MCP server port requires explicit confirmation. "
                "Add --yes to proceed.",
                file=sys.stderr,
            )
            raise SystemExit(1)
        _run_mcp_server(args.transport, args.port)
        return
