#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam (谭淞)
# @Email  : sepinetam@gmail.com
# @File   : cli/test_cli.py

import argparse
import json
import sqlite3
import subprocess
import sys
import urllib.error
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientResponseError

from nber_cli import db
from nber_cli.cli import (
    _build_parser,
    _detect_upgrade_command,
    _doctor_payload,
    _format_download_error,
    _format_bytes,
    _fix_doctor_version,
    _get_latest_pypi_version,
    _get_version,
    _is_latest_version,
    _parse_bool,
    _parse_non_negative_int,
    _parse_paper_id,
    _parse_positive_int,
    _print_doctor,
    _read_db_last_run,
    _resolve_paper_ids,
    _run_mcp_server,
    main,
)



class TestGetVersion:
    def test_returns_version_when_package_installed(self):
        with patch("nber_cli.cli.get_version", return_value="0.3.0"):
            assert _get_version() == "0.3.0"

    def test_returns_fallback_when_package_not_installed(self):
        with patch("nber_cli.cli.get_version", side_effect=Exception("not found")):
            assert _get_version() == "0.10.0"


class TestDoctorHelpers:
    def test_is_latest_version(self):
        assert _is_latest_version("1.2.0", "1.2.0") is True
        assert _is_latest_version("1.2.1", "1.2.0") is True
        assert _is_latest_version("1.2.0rc1", "1.2.0") is False
        assert _is_latest_version("1.2", "1.2.0") is True
        assert _is_latest_version("1.1.9", "1.2.0") is False
        assert _is_latest_version("1.1.9", None) is None

    def test_format_bytes(self):
        assert _format_bytes(None) == "unknown"
        assert _format_bytes(0) == "0 B"
        assert _format_bytes(512) == "512 B"
        assert _format_bytes(2048) == "2.0 KiB"
        assert _format_bytes(5 * 1024 * 1024) == "5.0 MiB"

    def test_detect_upgrade_command_defaults_to_current_python_pip(self):
        with (
            patch.object(sys, "argv", ["nber-cli"]),
            patch("nber_cli.cli._is_running_under_uvx", return_value=False),
            patch("nber_cli.cli._is_uv_tool_install", return_value=False),
            patch("nber_cli.cli._is_pipx_install", return_value=False),
            patch("nber_cli.cli._is_pip_install", return_value=True),
            patch("nber_cli.cli.sys.executable", "/tmp/venv/bin/python"),
        ):
            assert _detect_upgrade_command() == [
                "/tmp/venv/bin/python",
                "-m",
                "pip",
                "install",
                "--upgrade",
                "nber-cli",
            ]

    def test_detect_upgrade_command_for_pipx(self):
        with (
            patch("nber_cli.cli._is_running_under_uvx", return_value=False),
            patch("nber_cli.cli._is_uv_tool_install", return_value=False),
            patch("nber_cli.cli._is_pipx_install", return_value=True),
        ):
            assert _detect_upgrade_command() == ["pipx", "upgrade", "nber-cli"]

    def test_detect_upgrade_command_for_uv_tool(self):
        with (
            patch("nber_cli.cli._is_running_under_uvx", return_value=False),
            patch("nber_cli.cli._is_uv_tool_install", return_value=True),
        ):
            assert _detect_upgrade_command() == ["uv", "tool", "upgrade", "nber-cli"]

    def test_detect_upgrade_command_for_uvx(self):
        with patch("nber_cli.cli._is_running_under_uvx", return_value=True):
            assert _detect_upgrade_command() == ["uvx", "--refresh", "nber-cli", "-v"]

    def test_detect_upgrade_command_unknown(self):
        with (
            patch("nber_cli.cli._is_running_under_uvx", return_value=False),
            patch("nber_cli.cli._is_uv_tool_install", return_value=False),
            patch("nber_cli.cli._is_pipx_install", return_value=False),
            patch("nber_cli.cli._is_pip_install", return_value=False),
        ):
            assert _detect_upgrade_command() == []

    def test_get_latest_pypi_version_network_failure(self):
        with patch("nber_cli.cli.urllib.request.urlopen", side_effect=urllib.error.URLError("blocked")):
            assert _get_latest_pypi_version() is None

    def test_get_latest_pypi_version_non_200_status(self):
        response = MagicMock()
        response.__enter__.return_value = SimpleNamespace(status=503, reason="Service Unavailable")
        with patch("nber_cli.cli.urllib.request.urlopen", return_value=response):
            assert _get_latest_pypi_version() is None

    def test_get_latest_pypi_version_json_parse_failure(self):
        response = MagicMock()
        response.__enter__.return_value = SimpleNamespace(status=200, read=lambda: b"{")
        with patch("nber_cli.cli.urllib.request.urlopen", return_value=response):
            assert _get_latest_pypi_version() is None

    def test_get_latest_pypi_version_success(self):
        response = MagicMock()
        response.__enter__.return_value = SimpleNamespace(
            status=200,
            read=lambda: b'{"info": {"version": "1.2.3"}}',
        )
        with patch("nber_cli.cli.urllib.request.urlopen", return_value=response):
            assert _get_latest_pypi_version() == "1.2.3"

    def test_read_db_last_run_missing_tables(self, tmp_path):
        db_path = tmp_path / "nber.db"
        sqlite3.connect(db_path).close()
        assert _read_db_last_run(db_path) is None

    def test_read_db_last_run_returns_latest_activity(self, tmp_path):
        db_path = tmp_path / "nber.db"
        with sqlite3.connect(db_path) as connection:
            connection.execute("CREATE TABLE query_log (created_at TEXT)")
            connection.execute("CREATE TABLE download_log (created_at TEXT)")
            connection.execute("INSERT INTO query_log VALUES ('2026-01-01T00:00:00')")
            connection.execute("INSERT INTO download_log VALUES ('2026-01-02T00:00:00')")
        assert _read_db_last_run(db_path) == "2026-01-02T00:00:00"

    def test_doctor_payload_database_missing(self, tmp_path):
        db_path = tmp_path / "missing.db"
        with (
            patch("nber_cli.cli._get_latest_pypi_version", return_value="0.8.1"),
            patch("nber_cli.cli.shutil.which", return_value="/tmp/nber-cli"),
            patch("nber_cli.cli.config_store.default_config_path", return_value=tmp_path / "config.json"),
            patch("nber_cli.cli.config_store.read_config", return_value={"info": {}}),
            patch("nber_cli.cli.db.get_database_path", return_value=db_path),
            patch("nber_cli.cli.db.get_schema_version", return_value=0),
        ):
            payload = _doctor_payload()
        assert payload["database_exists"] is False
        assert payload["supported_schema_version"] == db.SCHEMA_VERSION
        assert payload["database_schema_version"] == 0
        assert payload["database_size"] == "unknown"
        assert payload["last_run_at"] == "unknown"

    def test_doctor_payload_schema_error(self, tmp_path):
        db_path = tmp_path / "nber.db"
        db_path.write_bytes(b"not sqlite")
        with (
            patch("nber_cli.cli._get_latest_pypi_version", return_value="0.8.1"),
            patch("nber_cli.cli.config_store.read_config", return_value={"info": {}}),
            patch("nber_cli.cli.db.get_database_path", return_value=db_path),
            patch("nber_cli.cli.db.get_schema_version", side_effect=ValueError("future schema")),
        ):
            payload = _doctor_payload()
        assert payload["supported_schema_version"] == db.SCHEMA_VERSION
        assert payload["database_schema_version"] == "unknown"
        assert payload["database_size"] == "10 B"
        assert payload["last_run_at"] == "unknown"

    def test_doctor_payload_normal_database(self, tmp_path):
        db_path = tmp_path / "nber.db"
        with sqlite3.connect(db_path) as connection:
            connection.execute("CREATE TABLE query_log (created_at TEXT)")
            connection.execute("INSERT INTO query_log VALUES ('2026-01-02T00:00:00')")
        with (
            patch("nber_cli.cli._get_latest_pypi_version", return_value="0.8.1"),
            patch("nber_cli.cli.config_store.read_config", return_value={"info": {}}),
            patch("nber_cli.cli.db.get_database_path", return_value=db_path),
            patch("nber_cli.cli.db.get_schema_version", return_value=2),
        ):
            payload = _doctor_payload()
        assert payload["database_exists"] is True
        assert payload["supported_schema_version"] == db.SCHEMA_VERSION
        assert payload["database_schema_version"] == 2
        assert payload["last_run_at"] == "2026-01-02T00:00:00"

    def test_doctor_payload_schema_newer_than_supported(self, tmp_path, capsys):
        db_path = tmp_path / "nber.db"
        db_path.touch()
        with (
            patch("nber_cli.cli._get_latest_pypi_version", return_value="0.8.1"),
            patch("nber_cli.cli.config_store.read_config", return_value={"info": {}}),
            patch("nber_cli.cli.db.get_database_path", return_value=db_path),
            patch("nber_cli.cli.db.SCHEMA_VERSION", 2),
            patch("nber_cli.cli.db.get_schema_version", return_value=3),
        ):
            payload = _doctor_payload()
        assert payload["supported_schema_version"] == 2
        assert payload["database_schema_version"] == 3
        _print_doctor(payload)
        captured = capsys.readouterr()
        assert "Warning: database schema (3) is newer than supported by this version (2)." in captured.out

    def test_print_doctor_warning_when_schema_newer(self, capsys):
        payload = {
            "current_version": "0.8.1",
            "latest_pypi_version": "0.8.1",
            "command_path": "/tmp/nber-cli",
            "package_path": "/tmp/nber_cli",
            "python_executable": sys.executable,
            "config_path": "/tmp/config.json",
            "config": {},
            "database_path": "/tmp/nber.db",
            "database_exists": True,
            "supported_schema_version": 2,
            "database_schema_version": 3,
            "database_size": "4.0 KiB",
            "last_run_at": "unknown",
        }
        _print_doctor(payload)
        captured = capsys.readouterr()
        assert "Supported schema version: 2" in captured.out
        assert "Database schema version: 3" in captured.out
        assert "Warning: database schema (3) is newer than supported by this version (2)." in captured.out

    def test_fix_doctor_version_success(self, capsys):
        with (
            patch("nber_cli.cli._doctor_payload", return_value={"latest_pypi_version": "1.0.0", "is_latest": False}),
            patch("nber_cli.cli._print_doctor"),
            patch("nber_cli.cli._detect_upgrade_command", return_value=["pipx", "upgrade", "nber-cli"]),
            patch("nber_cli.cli.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout="", stderr="")),
            patch("nber_cli.cli._get_subprocess_cli_version", return_value="1.0.0"),
        ):
            _fix_doctor_version()
        assert "nber-cli is up to date." in capsys.readouterr().out

    def test_fix_doctor_version_upgrade_failure(self):
        with (
            patch("nber_cli.cli._doctor_payload", return_value={"latest_pypi_version": "1.0.0", "is_latest": False}),
            patch("nber_cli.cli._print_doctor"),
            patch("nber_cli.cli._detect_upgrade_command", return_value=["pipx", "upgrade", "nber-cli"]),
            patch("nber_cli.cli.subprocess.run", return_value=SimpleNamespace(returncode=1, stdout="", stderr="boom")),
        ):
            with pytest.raises(SystemExit) as exc_info:
                _fix_doctor_version()
        assert exc_info.value.code == 1

    def test_fix_doctor_version_still_old_after_upgrade(self):
        with (
            patch("nber_cli.cli._doctor_payload", return_value={"latest_pypi_version": "1.0.0", "is_latest": False}),
            patch("nber_cli.cli._print_doctor"),
            patch("nber_cli.cli._detect_upgrade_command", return_value=["pipx", "upgrade", "nber-cli"]),
            patch("nber_cli.cli.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout="", stderr="")),
            patch("nber_cli.cli._get_subprocess_cli_version", return_value="0.9.0"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                _fix_doctor_version()
        assert exc_info.value.code == 1

    def test_fix_doctor_version_timeout(self):
        with (
            patch("nber_cli.cli._doctor_payload", return_value={"latest_pypi_version": "1.0.0", "is_latest": False}),
            patch("nber_cli.cli._print_doctor"),
            patch("nber_cli.cli._detect_upgrade_command", return_value=["pipx", "upgrade", "nber-cli"]),
            patch("nber_cli.cli.subprocess.run", side_effect=subprocess.TimeoutExpired("pipx", 120)),
        ):
            with pytest.raises(SystemExit) as exc_info:
                _fix_doctor_version()
        assert exc_info.value.code == 1


class TestBuildParser:
    def test_parser_creation(self):
        parser = _build_parser()
        assert parser.prog == "nber-cli"

    def test_version_flag(self, capsys):
        parser = _build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "NBER CLI v" in captured.out

    def test_config_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--config", "/tmp/custom.json", "feed", "fetch"])
        assert args.command == "feed"
        assert str(args.config) == "/tmp/custom.json"

    def test_config_short_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["-c", "/tmp/custom.json", "feed", "fetch"])
        assert args.command == "feed"
        assert str(args.config) == "/tmp/custom.json"

    def test_doctor_subcommand(self):
        parser = _build_parser()
        args = parser.parse_args(["doctor"])
        assert args.command == "doctor"
        assert args.fix_version is False

    def test_doctor_fix_version_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["doctor", "--fix-version"])
        assert args.command == "doctor"
        assert args.fix_version is True

    def test_download_subcommand_with_single_id(self):
        parser = _build_parser()
        args = parser.parse_args(["download", "w1234"])
        assert args.command == "download"
        assert args.paper_id == "w1234"
        assert args.save_base == Path.cwd()

    def test_download_subcommand_with_save_base(self):
        parser = _build_parser()
        args = parser.parse_args(["download", "w1234", "--save-base", "/tmp/papers"])
        assert args.save_base == Path("/tmp/papers")

    def test_download_subcommand_with_file_path(self):
        parser = _build_parser()
        args = parser.parse_args(["download", "w1234", "--file", "/tmp/paper.pdf"])
        assert args.file_path == Path("/tmp/paper.pdf")

    def test_download_subcommand_with_batch(self):
        parser = _build_parser()
        args = parser.parse_args(["download", "--batch", "w1234", "w5678"])
        assert args.batch_ids == ["w1234", "w5678"]
        assert args.paper_id is None

    def test_download_without_args(self):
        parser = _build_parser()
        args = parser.parse_args(["download"])
        assert args.paper_id is None
        assert args.batch_ids is None

    def test_info_subcommand_with_paper_id(self):
        parser = _build_parser()
        args = parser.parse_args(["info", "w1234"])
        assert args.command == "info"
        assert args.paper_id == "w1234"
        assert args.show_all is False
        assert args.output_format == "list"

    def test_info_subcommand_with_all_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["info", "w1234", "--all", "-f", "json"])
        assert args.command == "info"
        assert args.paper_id == "w1234"
        assert args.show_all is True
        assert args.output_format == "json"

    def test_info_subcommand_with_refresh_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["info", "w1234", "--refresh"])
        assert args.command == "info"
        assert args.paper_id == "w1234"
        assert args.refresh is True

    def test_info_cache_turn_on_command(self):
        parser = _build_parser()
        args = parser.parse_args(["info", "cache", "--turn-on"])
        assert args.command == "info"
        assert args.paper_id == "cache"
        assert args.cache_turn_on is True

    def test_info_cache_clear_command(self):
        parser = _build_parser()
        args = parser.parse_args(["info", "cache", "clear", "--days", "7"])
        assert args.command == "info"
        assert args.paper_id == "cache"
        assert args.cache_action == "clear"
        assert args.days == 7

    def test_info_subcommand_without_args(self):
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["info"])

    def test_search_subcommand_with_query(self):
        parser = _build_parser()
        args = parser.parse_args(["search", "inflation"])
        assert args.command == "search"
        assert args.query == "inflation"
        assert args.start_date is None
        assert args.end_date is None
        assert args.page == 1
        assert args.per_page == 20
        assert args.output_format == "list"

    def test_search_subcommand_with_date_args(self):
        parser = _build_parser()
        args = parser.parse_args(
            [
                "search",
                "inflation",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-12-31",
                "--page",
                "2",
                "--per-page",
                "50",
                "-f",
                "json",
            ]
        )
        assert args.start_date == "2024-01-01"
        assert args.end_date == "2024-12-31"
        assert args.page == 2
        assert args.per_page == 50
        assert args.output_format == "json"

    def test_search_subcommand_without_query(self):
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["search"])

    def test_db_init_subcommand_with_db_path(self):
        parser = _build_parser()
        args = parser.parse_args(["db", "init", "--db-path", "/tmp/nber.db"])
        assert args.command == "db"
        assert args.db_command == "init"
        assert args.db_path == Path("/tmp/nber.db")

    def test_db_init_subcommand_accepts_sqlite_url(self):
        parser = _build_parser()
        args = parser.parse_args(["db", "init", "--db-path", "sqlite:///tmp/nber.db"])
        assert args.command == "db"
        assert args.db_command == "init"
        assert args.db_path == "sqlite:///tmp/nber.db"

    def test_db_migrate_subcommand_with_new_db_path(self):
        parser = _build_parser()
        args = parser.parse_args(["db", "migrate", "/tmp/new-nber.db"])
        assert args.command == "db"
        assert args.db_command == "migrate"
        assert args.new_db_path == Path("/tmp/new-nber.db")

    def test_db_migrate_subcommand_accepts_sqlite_url(self):
        parser = _build_parser()
        args = parser.parse_args(["db", "migrate", "sqlite:///tmp/new-nber.db"])
        assert args.command == "db"
        assert args.db_command == "migrate"
        assert args.new_db_path == "sqlite:///tmp/new-nber.db"

    def test_feed_clean_subcommand_defaults(self):
        parser = _build_parser()
        args = parser.parse_args(["feed", "clean"])
        assert args.command == "feed"
        assert args.feed_command == "clean"
        assert args.days is None
        assert args.delete_all is False
        assert args.start_date is None
        assert args.end_date is None

    def test_feed_clean_subcommand_with_filters(self):
        parser = _build_parser()
        args = parser.parse_args(
            ["feed", "clean", "--start-date", "2026-05-01", "--end-date", "2026-05-31"]
        )
        assert args.feed_command == "clean"
        assert args.start_date == "2026-05-01"
        assert args.end_date == "2026-05-31"

    def test_feed_fetch_subcommand_defaults(self):
        parser = _build_parser()
        args = parser.parse_args(["feed", "fetch"])
        assert args.command == "feed"
        assert args.feed_command == "fetch"
        assert args.display_all is None
        assert args.output_format == "list"

    def test_feed_fetch_subcommand_with_display_all_false(self):
        parser = _build_parser()
        args = parser.parse_args(["feed", "fetch", "--display-all", "false", "-f", "json"])
        assert args.display_all is False
        assert args.output_format == "json"

    def test_feed_fetch_subcommand_with_max_items(self):
        parser = _build_parser()
        args = parser.parse_args(["feed", "fetch", "--max-items", "5"])
        assert args.display_all is None
        assert args.max_items == 5

    def test_feed_fetch_subcommand_rejects_max_abbreviation(self):
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["feed", "fetch", "--max", "5"])

    def test_feed_fetch_subcommand_with_display_all_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["feed", "fetch", "--display-all"])
        assert args.display_all is True


class TestResolvePaperIds:
    def test_batch_ids_take_priority(self):
        assert _resolve_paper_ids("w1234", ["w5678", "w9012"]) == ["w5678", "w9012"]

    def test_single_id_when_no_batch(self):
        assert _resolve_paper_ids("w1234", None) == ["w1234"]

    def test_empty_list_when_neither(self):
        assert _resolve_paper_ids(None, None) == []

    def test_empty_list_when_both_none(self):
        assert _resolve_paper_ids(None, None) == []


class TestParsePaperId:
    def test_with_w_prefix(self):
        assert _parse_paper_id("w1234") == 1234

    def test_without_prefix(self):
        assert _parse_paper_id("5678") == 5678

    def test_uppercase_w(self):
        assert _parse_paper_id("W9999") == 9999

    def test_invalid_raises_valueerror(self):
        with pytest.raises(ValueError):
            _parse_paper_id("abc")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            _parse_paper_id("")

    def test_w_without_number_raises(self):
        with pytest.raises(ValueError):
            _parse_paper_id("w")

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            _parse_paper_id("w-123")

    def test_mixed_chars_raises(self):
        with pytest.raises(ValueError):
            _parse_paper_id("w12a3")

    def test_whitespace_raises(self):
        with pytest.raises(ValueError):
            _parse_paper_id(" w123 ")


class TestParseBool:
    def test_true_values(self):
        assert _parse_bool("true") is True
        assert _parse_bool("1") is True
        assert _parse_bool("yes") is True

    def test_false_values(self):
        assert _parse_bool("false") is False
        assert _parse_bool("0") is False
        assert _parse_bool("no") is False

    def test_invalid_raises_argument_error(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_bool("maybe")


class TestParseNonNegativeInt:
    def test_valid_non_negative_int(self):
        assert _parse_non_negative_int("5") == 5
        assert _parse_non_negative_int("0") == 0

    def test_rejects_negative_number(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_non_negative_int("-1")

    def test_rejects_non_integer(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_non_negative_int("five")


class TestParsePositiveInt:
    def test_valid_positive_int(self):
        assert _parse_positive_int("5") == 5

    def test_rejects_zero(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_positive_int("0")

    def test_rejects_negative_number(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_positive_int("-1")


class TestFormatDownloadError:
    def test_formats_403_as_permission_error(self):
        error = ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=403,
            message="Forbidden",
        )

        message = _format_download_error("w1234", error)

        assert "Failed to download w1234" in message
        assert "no permission" in message
        assert "HTTP 403" in message
        assert "first-week" in message

    def test_formats_404_as_not_found(self):
        error = ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=404,
            message="Not Found",
        )

        message = _format_download_error("w1235456", error)

        assert message == "Failed to download w1235456: paper not found (HTTP 404)."

    def test_formats_timeout(self):
        message = _format_download_error("w1234", TimeoutError("timed out"))

        assert message == "Failed to download w1234: request timed out."

    def test_formats_network_error(self):
        message = _format_download_error("w1234", ConnectionError("broken pipe"))

        assert message == "Failed to download w1234: network error."

    def test_formats_unknown_error_as_class_name(self):
        message = _format_download_error("w1234", ValueError("sensitive details"))

        assert message == "Failed to download w1234: ValueError."

    def test_does_not_leak_error_details(self):
        message = _format_download_error("w1234", Exception("contains secret url"))

        assert "secret" not in message
        assert "url" not in message


class TestMainEntrypoint:
    def test_no_command_prints_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli"]):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "download" in captured.out

    def test_mix_paper_id_and_batch_raises_error(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "download", "w1234", "--batch", "w5678"]):
                main()
        assert exc_info.value.code == 2

    def test_batch_with_file_raises_error(self):
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "download", "--batch", "w1234", "--file", "/tmp/x.pdf"]):
                main()
        assert exc_info.value.code == 2

    def test_no_paper_id_raises_error(self):
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "download"]):
                main()
        assert exc_info.value.code == 2

    def test_multiple_ids_with_file_raises_error(self):
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "download", "--batch", "w1234", "w5678", "--file", "/tmp/x.pdf"]):
                main()
        assert exc_info.value.code == 2

    @patch("nber_cli.cli.download_multiple_papers", new_callable=AsyncMock)
    def test_batch_with_single_id_and_no_file_path(self, mock_download, capsys):
        mock_result = MagicMock()
        mock_result.paths = [Path("/tmp/w1234.pdf")]
        mock_result.failures = []
        mock_download.return_value = mock_result
        with patch.object(sys, "argv", ["nber-cli", "download", "--batch", "w1234", "--save-base", "/tmp"]):
            main()
        mock_download.assert_called_once_with(["w1234"], Path("/tmp"), restrict_dir=True, concurrency=None)
        captured = capsys.readouterr()
        assert "Successfully downloaded w1234 to /tmp/w1234.pdf" in captured.out

    @patch("nber_cli.cli.download_paper_to_file", new_callable=AsyncMock)
    def test_single_download_with_file_path(self, mock_download, capsys):
        mock_download.return_value = Path("/tmp/paper.pdf")
        with patch.object(sys, "argv", ["nber-cli", "download", "w1234", "--file", "/tmp/paper.pdf"]):
            main()
        mock_download.assert_called_once_with("w1234", Path("/tmp/paper.pdf"), restrict_dir=True)
        captured = capsys.readouterr()
        assert "Successfully downloaded w1234 to /tmp/paper.pdf" in captured.out

    @patch("nber_cli.cli.download_paper", new_callable=AsyncMock)
    def test_single_download_without_file_path(self, mock_download, capsys):
        mock_download.return_value = Path("/tmp/w1234.pdf")
        with patch.object(sys, "argv", ["nber-cli", "download", "w1234", "--save-base", "/tmp"]):
            main()
        mock_download.assert_called_once_with("w1234", Path("/tmp"), restrict_dir=True)
        captured = capsys.readouterr()
        assert "Successfully downloaded w1234 to /tmp/w1234.pdf" in captured.out

    @patch("nber_cli.cli.download_paper_to_file", new_callable=AsyncMock)
    def test_single_paper_with_file_path(self, mock_download, capsys):
        mock_download.return_value = Path("/tmp/custom.pdf")
        with patch.object(sys, "argv", ["nber-cli", "download", "w1234", "--file", "/tmp/custom.pdf"]):
            main()
        mock_download.assert_called_once_with("w1234", Path("/tmp/custom.pdf"), restrict_dir=True)
        captured = capsys.readouterr()
        assert "Successfully downloaded w1234 to /tmp/custom.pdf" in captured.out

    @patch("nber_cli.cli.download_multiple_papers", new_callable=AsyncMock)
    def test_batch_download_all_success(self, mock_download, capsys):
        mock_result = MagicMock()
        mock_result.paths = [Path("/tmp/w1234.pdf"), Path("/tmp/w5678.pdf")]
        mock_result.failures = []
        mock_download.return_value = mock_result
        with patch.object(sys, "argv", ["nber-cli", "download", "--batch", "w1234", "w5678", "--save-base", "/tmp"]):
            main()
        mock_download.assert_called_once_with(["w1234", "w5678"], Path("/tmp"), restrict_dir=True, concurrency=None)
        captured = capsys.readouterr()
        assert "Successfully downloaded w1234 to /tmp/w1234.pdf" in captured.out
        assert "Successfully downloaded w5678 to /tmp/w5678.pdf" in captured.out

    @patch("nber_cli.cli.download_paper", new_callable=AsyncMock)
    def test_single_paper_no_batch_no_file(self, mock_download, capsys):
        mock_download.return_value = Path("/tmp/w1234.pdf")
        with patch.object(sys, "argv", ["nber-cli", "download", "w1234", "--save-base", "/tmp"]):
            main()
        mock_download.assert_called_once_with("w1234", Path("/tmp"), restrict_dir=True)
        captured = capsys.readouterr()
        assert "Successfully downloaded w1234 to /tmp/w1234.pdf" in captured.out

    @patch("nber_cli.cli.download_multiple_papers", new_callable=AsyncMock)
    def test_batch_download_no_failures(self, mock_download, capsys):
        mock_result = MagicMock()
        mock_result.paths = [Path("/tmp/w1234.pdf")]
        mock_result.failures = []
        mock_download.return_value = mock_result
        with patch.object(sys, "argv", ["nber-cli", "download", "--batch", "w1234", "--save-base", "/tmp"]):
            main()
        mock_download.assert_called_once_with(["w1234"], Path("/tmp"), restrict_dir=True, concurrency=None)
        captured = capsys.readouterr()
        assert "Successfully downloaded w1234 to /tmp/w1234.pdf" in captured.out

    @patch("nber_cli.cli.download_paper", new_callable=AsyncMock)
    def test_single_download_404_exits_1_without_traceback(self, mock_download, capsys):
        mock_download.side_effect = ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=404,
            message="Not Found",
        )

        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "download", "w1235456", "--save-base", "/tmp"]):
                main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Failed to download w1235456: paper not found (HTTP 404)." in captured.err
        assert "Traceback" not in captured.err

    def test_single_download_invalid_id_exits_2_without_traceback(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "download", "../../bad"]):
                main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "invalid paper ID '../../bad'" in captured.err
        assert "Traceback" not in captured.err

    def test_batch_download_invalid_id_exits_2_without_traceback(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "download", "--batch", "w1234", "invalid"]):
                main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "invalid paper ID 'invalid'" in captured.err
        assert "Traceback" not in captured.err

    @patch("nber_cli.cli.download_multiple_papers", new_callable=AsyncMock)
    def test_batch_download_with_failures_exits_1(self, mock_download, capsys):
        from nber_cli.core.models import DownloadFailure
        mock_result = MagicMock()
        mock_result.paths = [Path("/tmp/w1234.pdf")]
        mock_result.failures = [
            DownloadFailure(paper_id="w5678", error=Exception("network error")),
        ]
        mock_download.return_value = mock_result
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "download", "--batch", "w1234", "w5678", "--save-base", "/tmp"]):
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Failed to download w5678" in captured.err
        assert "Downloaded 1 of 2 papers" in captured.err
        assert "Successfully downloaded w1234 to /tmp/w1234.pdf" in captured.out

    @patch("nber_cli.cli.download_multiple_papers", new_callable=AsyncMock)
    def test_batch_download_all_failures_exits_1(self, mock_download, capsys):
        from nber_cli.core.models import DownloadFailure
        mock_result = MagicMock()
        mock_result.paths = []
        mock_result.failures = [
            DownloadFailure(paper_id="w1234", error=Exception("timeout")),
            DownloadFailure(paper_id="w5678", error=Exception("404")),
        ]
        mock_download.return_value = mock_result
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "download", "--batch", "w1234", "w5678", "--save-base", "/tmp"]):
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Failed to download w1234" in captured.err
        assert "Failed to download w5678" in captured.err
        assert "Downloaded 0 of 2 papers" in captured.err

    @patch("nber_cli.cli.download_multiple_papers", new_callable=AsyncMock)
    def test_batch_download_error_with_empty_message(self, mock_download, capsys):
        from nber_cli.core.models import DownloadFailure
        class EmptyError(Exception):
            def __str__(self):
                return ""
        mock_result = MagicMock()
        mock_result.paths = []
        mock_result.failures = [
            DownloadFailure(paper_id="w1234", error=EmptyError()),
        ]
        mock_download.return_value = mock_result
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "download", "--batch", "w1234", "--save-base", "/tmp"]):
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "EmptyError" in captured.err


class TestMainEntrypointInfo:
    @patch("nber_cli.db.info_cache.get_nber", new_callable=AsyncMock)
    def test_info_basic_output(self, mock_get_nber, capsys):
        from nber_cli.core.models import NBER
        mock_get_nber.return_value = NBER(
            paper_id=1234,
            title="Test Title",
            authors=["Author A"],
            date="2024/01/01",
            abstract="Test abstract.",
        )
        with patch.object(sys, "argv", ["nber-cli", "info", "w1234"]):
            main()
        captured = capsys.readouterr()
        assert "w1234 | Test Title" in captured.out
        assert "Test Title" in captured.out
        assert "Author A" in captured.out
        assert "Test abstract." in captured.out

    @patch("nber_cli.db.info_cache.get_nber", new_callable=AsyncMock)
    def test_info_with_all_flag(self, mock_get_nber, capsys):
        from nber_cli.core.models import NBER
        mock_get_nber.return_value = NBER(
            paper_id=1234,
            title="Test Title",
            authors=["Author A"],
            date="2024/01/01",
            abstract="Test abstract.",
            published_version="Published in Journal.",
        )
        with patch.object(sys, "argv", ["nber-cli", "info", "w1234", "--all"]):
            main()
        captured = capsys.readouterr()
        assert "Test Title" in captured.out
        assert "Published in Journal." in captured.out

    @patch("nber_cli.db.info_cache.get_nber", new_callable=AsyncMock)
    def test_info_json_output(self, mock_get_nber, capsys):
        from nber_cli.core.models import NBER
        mock_get_nber.return_value = NBER(
            paper_id=1234,
            title="Test Title",
            authors=["Author A"],
            date="2024/01/01",
            abstract="Test abstract.",
        )
        with patch.object(sys, "argv", ["nber-cli", "info", "w1234", "--format", "json"]):
            main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["id"] == "w1234"
        assert payload["title"] == "Test Title"

    @patch("nber_cli.db.info_cache.get_nber", new_callable=AsyncMock)
    def test_info_without_w_prefix(self, mock_get_nber, capsys):
        from nber_cli.core.models import NBER
        mock_get_nber.return_value = NBER(
            paper_id=5678,
            title="No Prefix",
            authors=["Author B"],
            date="2024/02/01",
            abstract="Abstract text.",
        )
        with patch.object(sys, "argv", ["nber-cli", "info", "5678"]):
            main()
        mock_get_nber.assert_called_once_with(5678)
        captured = capsys.readouterr()
        assert "No Prefix" in captured.out

    @patch("nber_cli.db.info_cache.get_nber", new_callable=AsyncMock)
    def test_info_cache_hit_skips_network(self, mock_get_nber, tmp_path, capsys):
        from nber_cli import db
        from nber_cli.core.models import NBER

        db_path = tmp_path / "nber.db"
        db.init_database(db_path)
        db.write_info_cache(
            db_path,
            NBER(
                paper_id=1234,
                title="Cached Title",
                authors=["Author A"],
                date="2024/01/01",
                abstract="Cached abstract.",
            ),
        )

        with patch.object(sys, "argv", ["nber-cli", "info", "w1234"]):
            main()

        mock_get_nber.assert_not_called()
        captured = capsys.readouterr()
        assert "Cached Title" in captured.out
        with sqlite3.connect(db_path) as connection:
            count = connection.execute(
                "SELECT fetch_count FROM info_cache WHERE paper_id = 'w1234'"
            ).fetchone()[0]
        assert count == 1

    @patch("nber_cli.db.info_cache.get_nber", new_callable=AsyncMock)
    def test_info_json_cache_hit_keeps_stdout_json(self, mock_get_nber, tmp_path, capsys):
        from nber_cli import db
        from nber_cli.core.models import NBER

        db_path = tmp_path / "nber.db"
        db.init_database(db_path)
        db.write_info_cache(
            db_path,
            NBER(
                paper_id=1234,
                title="Cached Title",
                authors=["Author A"],
                date="2024/01/01",
                abstract="Cached abstract.",
            ),
        )

        with patch.object(sys, "argv", ["nber-cli", "info", "w1234", "--format", "json"]):
            main()

        mock_get_nber.assert_not_called()
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["title"] == "Cached Title"

    @patch("nber_cli.db.info_cache.get_nber", new_callable=AsyncMock)
    def test_info_refresh_fetches_network_and_updates_cache(self, mock_get_nber, tmp_path, capsys):
        from nber_cli import db
        from nber_cli.core.models import NBER

        db_path = tmp_path / "nber.db"
        db.init_database(db_path)
        db.write_info_cache(
            db_path,
            NBER(
                paper_id=1234,
                title="Cached Title",
                authors=["Author A"],
                date="2024/01/01",
                abstract="Cached abstract.",
            ),
        )
        mock_get_nber.return_value = NBER(
            paper_id=1234,
            title="Fresh Title",
            authors=["Author A"],
            date="2024/01/01",
            abstract="Fresh abstract.",
        )

        with patch.object(sys, "argv", ["nber-cli", "info", "w1234", "--refresh"]):
            main()

        mock_get_nber.assert_called_once_with(1234)
        captured = capsys.readouterr()
        assert "Fresh Title" in captured.out
        assert "Loaded from info cache." not in captured.err
        cached = db.read_info_cache(db_path, 1234)
        assert cached is not None
        assert cached.title == "Fresh Title"

    @patch("nber_cli.db.info_cache.get_nber", new_callable=AsyncMock)
    def test_info_cache_off_fetches_network_and_does_not_write(self, mock_get_nber, tmp_path, capsys):
        from nber_cli import config_store, db
        from nber_cli.core.models import NBER

        db_path = tmp_path / "nber.db"
        db.init_database(db_path)
        db.write_info_cache(
            db_path,
            NBER(
                paper_id=1234,
                title="Cached Title",
                authors=["Author A"],
                date="2024/01/01",
                abstract="Cached abstract.",
            ),
        )
        config_store.set_info_cache_enabled(False)
        mock_get_nber.return_value = NBER(
            paper_id=1234,
            title="Remote Title",
            authors=["Author A"],
            date="2024/01/01",
            abstract="Remote abstract.",
        )

        with patch.object(sys, "argv", ["nber-cli", "info", "w1234"]):
            main()

        mock_get_nber.assert_called_once_with(1234)
        captured = capsys.readouterr()
        assert "Remote Title" in captured.out
        assert "Loaded from info cache." not in captured.err
        with sqlite3.connect(db_path) as connection:
            row = connection.execute(
                "SELECT title, fetch_count FROM info_cache WHERE paper_id = 'w1234'"
            ).fetchone()
        assert row == ("Cached Title", 0)

    def test_info_invalid_paper_id(self):
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "info", "abc"]):
                main()
        assert exc_info.value.code == 2

    def test_info_cache_option_on_paper_command_exits_2(self):
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "info", "w1234", "--days", "7"]):
                main()
        assert exc_info.value.code == 2

    @patch("nber_cli.db.info_cache.get_nber", new_callable=AsyncMock)
    def test_info_network_failure_prints_error(self, mock_get_nber, capsys):
        from aiohttp import ClientResponseError
        mock_get_nber.side_effect = ClientResponseError(
            request_info=MagicMock(), history=(), status=404, message="Not Found"
        )
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "info", "w1234"]):
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Failed to fetch paper w1234" in captured.err


class TestMainEntrypointInfoCache:
    def test_info_cache_turn_on_writes_config(self, isolated_nber_home, capsys):
        with patch.object(sys, "argv", ["nber-cli", "info", "cache", "--turn-on"]):
            main()

        config_path = isolated_nber_home / ".nber-cli" / "config.json"
        config = json.loads(config_path.read_text())
        assert config["info"]["cache_enabled"] is True
        assert "Info cache enabled." in capsys.readouterr().out

    def test_info_cache_turn_off_writes_config(self, isolated_nber_home, capsys):
        with patch.object(sys, "argv", ["nber-cli", "info", "cache", "--turn-off"]):
            main()

        config_path = isolated_nber_home / ".nber-cli" / "config.json"
        config = json.loads(config_path.read_text())
        assert config["info"]["cache_enabled"] is False
        assert "Info cache disabled." in capsys.readouterr().out

    def test_info_cache_set_refresh_writes_config(self, isolated_nber_home, capsys):
        with patch.object(sys, "argv", ["nber-cli", "info", "cache", "--set-refresh", "30"]):
            main()

        config_path = isolated_nber_home / ".nber-cli" / "config.json"
        config = json.loads(config_path.read_text())
        assert config["info"]["cache_ttl_days"] == 30
        assert "30 days" in capsys.readouterr().out

    def test_info_cache_status_outputs_current_config(self, tmp_path, capsys):
        from nber_cli import config_store, db
        from nber_cli.core.models import NBER

        db_path = tmp_path / "nber.db"
        db.init_database(db_path)
        config_store.set_info_cache_enabled(True)
        config_store.set_info_cache_ttl_days(12)
        db.write_info_cache(
            db_path,
            NBER(
                paper_id=1234,
                title="Cached Title",
                authors=["Author A"],
                date="2024/01/01",
                abstract="Cached abstract.",
            ),
        )

        with patch.object(sys, "argv", ["nber-cli", "info", "cache", "status"]):
            main()

        captured = capsys.readouterr()
        assert "Cache: on" in captured.out
        assert "TTL: 12 days" in captured.out
        assert "Cached rows: 1" in captured.out

    def test_info_cache_clean_matches_clear_all(self, tmp_path, capsys):
        from nber_cli import db
        from nber_cli.core.models import NBER

        db_path = tmp_path / "nber.db"
        db.init_database(db_path)
        paper = NBER(
            paper_id=1234,
            title="Cached Title",
            authors=["Author A"],
            date="2024/01/01",
            abstract="Cached abstract.",
        )

        db.write_info_cache(db_path, paper)
        with (
            patch("builtins.input", return_value="y"),
            patch.object(sys, "argv", ["nber-cli", "info", "cache", "clear", "--all"]),
        ):
            main()
        clear_output = capsys.readouterr().out
        assert db.count_info_cache(db_path) == 0

        db.write_info_cache(db_path, paper)
        with (
            patch("builtins.input", return_value="y"),
            patch.object(sys, "argv", ["nber-cli", "info", "cache", "clean"]),
        ):
            main()
        clean_output = capsys.readouterr().out

        assert clean_output == clear_output
        assert db.count_info_cache(db_path) == 0

    def test_info_cache_clean_rejects_filters(self):
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "info", "cache", "clean", "--days", "7"]):
                main()
        assert exc_info.value.code == 2

    def test_info_cache_clear_aborts_on_no(self, tmp_path, capsys):
        from nber_cli import db
        from nber_cli.core.models import NBER

        db_path = tmp_path / "nber.db"
        db.init_database(db_path)
        db.write_info_cache(
            db_path,
            NBER(
                paper_id=1234,
                title="Cached Title",
                authors=["Author A"],
                date="2024/01/01",
                abstract="Cached abstract.",
            ),
        )

        with (
            patch("builtins.input", return_value="n"),
            patch.object(sys, "argv", ["nber-cli", "info", "cache", "clear", "--all"]),
        ):
            main()

        assert db.count_info_cache(db_path) == 1
        assert "Aborted." in capsys.readouterr().out

    def test_info_cache_clear_no_match_skips_confirm(self, tmp_path, capsys):
        from nber_cli import db

        db_path = tmp_path / "nber.db"
        db.init_database(db_path)

        with patch.object(sys, "argv", ["nber-cli", "info", "cache", "clear", "--all"]):
            main()

        assert db.count_info_cache(db_path) == 0
        captured = capsys.readouterr()
        assert "No cached records matched." in captured.out

    def test_info_cache_turn_on_and_off_mutually_exclusive(self):
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "info", "cache", "--turn-on", "--turn-off"]):
                main()
        assert exc_info.value.code == 2

    def test_info_cache_refresh_not_allowed_with_cache(self):
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "info", "cache", "status", "--refresh"]):
                main()
        assert exc_info.value.code == 2

    def test_info_cache_format_not_allowed_with_cache(self):
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "info", "cache", "status", "--format", "json"]):
                main()
        assert exc_info.value.code == 2


class TestMainEntrypointMcpServer:
    @pytest.mark.parametrize(
        ("transport", "include_download"),
        [
            ("stdio", True),
            ("sse", False),
            ("streamable-http", False),
        ],
    )
    @patch("nber_cli.mcp.create_mcp_server")
    def test_mcp_server_selects_tools_for_transport(
        self,
        mock_create_server,
        transport,
        include_download,
    ):
        _run_mcp_server(transport, "0.0.0.0", 9000)

        mock_create_server.assert_called_once_with(
            include_download=include_download,
            host="0.0.0.0",
        )
        mock_server = mock_create_server.return_value
        assert mock_server.settings.port == 9000
        mock_server.run.assert_called_once_with(transport=transport)

    @patch("nber_cli.cli._run_mcp_server")
    def test_mcp_server_starts_with_default_transport(self, mock_run, capsys):
        with patch.object(sys, "argv", ["nber-cli", "mcp-server"]):
            main()
        mock_run.assert_called_once_with("stdio", "127.0.0.1", 8000)

    @patch("nber_cli.cli._run_mcp_server")
    def test_mcp_server_uses_custom_port_with_yes(self, mock_run, capsys):
        with patch.object(sys, "argv", ["nber-cli", "mcp-server", "--port", "9000", "--yes"]):
            main()
        mock_run.assert_called_once_with("stdio", "127.0.0.1", 9000)

    @patch("nber_cli.cli._run_mcp_server")
    def test_mcp_server_rejects_custom_port_without_yes(self, mock_run, capsys):
        with patch.object(sys, "argv", ["nber-cli", "mcp-server", "--port", "9000"]):
            with pytest.raises(SystemExit):
                main()
        mock_run.assert_not_called()

    @patch("nber_cli.cli._run_mcp_server")
    def test_mcp_server_uses_streamable_http(self, mock_run, capsys):
        with patch.object(sys, "argv", ["nber-cli", "mcp-server", "--transport", "streamable-http"]):
            main()
        mock_run.assert_called_once_with("streamable-http", "127.0.0.1", 8000)

    @patch("nber_cli.cli._run_mcp_server")
    def test_mcp_server_uses_custom_host(self, mock_run, capsys):
        with patch.object(
            sys,
            "argv",
            [
                "nber-cli",
                "mcp-server",
                "--transport",
                "streamable-http",
                "--host",
                "0.0.0.0",
            ],
        ):
            main()

        mock_run.assert_called_once_with("streamable-http", "0.0.0.0", 8000)


class TestMainEntrypointDb:
    @patch("nber_cli.cli.db.init_database")
    def test_db_init_outputs_database_path(self, mock_init, capsys):
        mock_init.return_value = Path("/tmp/nber.db")

        with patch.object(sys, "argv", ["nber-cli", "db", "init", "--db-path", "/tmp/nber.db"]):
            main()

        mock_init.assert_called_once_with(Path("/tmp/nber.db"))
        captured = capsys.readouterr()
        assert "Database initialized at /tmp/nber.db" in captured.out

    @patch("nber_cli.cli.db.migrate_database")
    def test_db_migrate_outputs_database_paths(self, mock_migrate, capsys):
        mock_migrate.return_value = (Path("/tmp/old-nber.db"), Path("/tmp/new-nber.db"))

        with patch.object(sys, "argv", ["nber-cli", "db", "migrate", "/tmp/new-nber.db"]):
            main()

        mock_migrate.assert_called_once_with(Path("/tmp/new-nber.db"))
        captured = capsys.readouterr()
        assert "Database migrated from /tmp/old-nber.db to /tmp/new-nber.db" in captured.out

    @patch("nber_cli.cli.db.migrate_database")
    def test_db_migrate_validation_error_exits_2(self, mock_migrate):
        mock_migrate.side_effect = ValueError("target database file already exists")

        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "db", "migrate", "/tmp/new-nber.db"]):
                main()

        assert exc_info.value.code == 2

    @patch("builtins.input", return_value="y")
    @patch("nber_cli.cli.clean_feed_cache")
    def test_feed_clean_confirms_and_deletes_cache(self, mock_clean, mock_input, capsys):
        from nber_cli.core.models import NBERFeedCleanResult

        mock_clean.side_effect = [
            NBERFeedCleanResult(
                database_path=Path("/tmp/feed.db"),
                matched_count=2,
                deleted_count=0,
                mode="days",
                days=30,
                dry_run=True,
            ),
            NBERFeedCleanResult(
                database_path=Path("/tmp/feed.db"),
                matched_count=2,
                deleted_count=2,
                mode="days",
                days=30,
            ),
        ]

        with patch.object(sys, "argv", ["nber-cli", "feed", "clean", "--days", "30"]):
            main()

        mock_input.assert_called_once_with()
        assert mock_clean.call_count == 2
        mock_clean.assert_any_call(
            days=30,
            delete_all=False,
            start_date=None,
            end_date=None,
            dry_run=True,
        )
        mock_clean.assert_any_call(
            days=30,
            delete_all=False,
            start_date=None,
            end_date=None,
        )
        captured = capsys.readouterr()
        assert "Matched cached records: 2" in captured.out
        assert "This operation is irreversible." in captured.out
        assert "Deleted cached records: 2" in captured.out

    @patch("builtins.input", return_value="n")
    @patch("nber_cli.cli.clean_feed_cache")
    def test_feed_clean_aborts_without_deleting_cache(self, mock_clean, mock_input, capsys):
        from nber_cli.core.models import NBERFeedCleanResult

        mock_clean.return_value = NBERFeedCleanResult(
            database_path=Path("/tmp/feed.db"),
            matched_count=1,
            deleted_count=0,
            mode="all",
            dry_run=True,
        )

        with patch.object(sys, "argv", ["nber-cli", "feed", "clean", "--all"]):
            main()

        mock_input.assert_called_once_with()
        mock_clean.assert_called_once_with(
            days=None,
            delete_all=True,
            start_date=None,
            end_date=None,
            dry_run=True,
        )
        assert "Aborted." in capsys.readouterr().out

    @patch("builtins.input")
    @patch("nber_cli.cli.clean_feed_cache")
    def test_feed_clean_skips_prompt_when_no_cache_matches(self, mock_clean, mock_input, capsys):
        from nber_cli.core.models import NBERFeedCleanResult

        mock_clean.return_value = NBERFeedCleanResult(
            database_path=Path("/tmp/feed.db"),
            matched_count=0,
            deleted_count=0,
            mode="date-range",
            end_date="2026-05-31",
            dry_run=True,
        )

        with patch.object(sys, "argv", ["nber-cli", "feed", "clean", "--end-date", "2026-05-31"]):
            main()

        mock_input.assert_not_called()
        mock_clean.assert_called_once_with(
            days=None,
            delete_all=False,
            start_date=None,
            end_date="2026-05-31",
            dry_run=True,
        )
        captured = capsys.readouterr()
        assert "Matched cached records: 0" in captured.out
        assert "No cached records matched." in captured.out

    @patch("nber_cli.cli.clean_feed_cache")
    def test_feed_clean_validation_error_exits_2(self, mock_clean):
        mock_clean.side_effect = ValueError("end-date is required when start-date is provided")

        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "feed", "clean", "--start-date", "2026-05-01"]):
                main()

        assert exc_info.value.code == 2

    @patch("nber_cli.cli.fetch_feed")
    def test_feed_fetch_outputs_text(self, mock_fetch, capsys):
        from nber_cli.core.models import NBERFeedFetchResult, NBERFeedItem

        mock_fetch.return_value = NBERFeedFetchResult(
            source_url="https://www.nber.org/rss/new.xml",
            database_path=Path("/tmp/feed.db"),
            total_fetched=1,
            new_count=1,
            display_all=False,
            items=[
                NBERFeedItem(
                    paper_id="w35254",
                    title="Feed Paper",
                    authors=["Author A"],
                    abstract="Feed abstract.",
                    url="https://www.nber.org/papers/w35254",
                    source_url="https://www.nber.org/papers/w35254#fromrss",
                    guid="https://www.nber.org/papers/w35254#fromrss",
                )
            ],
        )

        with patch.object(sys, "argv", ["nber-cli", "feed", "fetch"]):
            main()

        mock_fetch.assert_called_once_with(display_all=False, max_items=None)
        captured = capsys.readouterr()
        assert "Fetched: 1" in captured.out
        assert "New: 1" in captured.out
        assert "w35254 | Feed Paper" in captured.out

    @patch("nber_cli.cli.fetch_feed")
    def test_feed_fetch_runtime_error_does_not_print_usage(self, mock_fetch, capsys):
        mock_fetch.side_effect = ValueError("invalid NBER RSS XML at line 3, column 4")

        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "feed", "fetch"]):
                main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == "nber-cli: error: invalid NBER RSS XML at line 3, column 4\n"
        assert "usage:" not in captured.err

    @patch("nber_cli.cli.fetch_feed")
    def test_feed_fetch_outputs_json(self, mock_fetch, capsys):
        from nber_cli.core.models import NBERFeedFetchResult, NBERFeedItem

        mock_fetch.return_value = NBERFeedFetchResult(
            source_url="https://www.nber.org/rss/new.xml",
            database_path=Path("/tmp/feed.db"),
            total_fetched=1,
            new_count=0,
            display_all=True,
            max_items=1,
            items=[
                NBERFeedItem(
                    paper_id="w35254",
                    title="Feed Paper",
                    authors=["Author A"],
                    abstract="Feed abstract.",
                    url="https://www.nber.org/papers/w35254",
                    source_url="https://www.nber.org/papers/w35254#fromrss",
                    guid="https://www.nber.org/papers/w35254#fromrss",
                )
            ],
        )

        with patch.object(
            sys,
            "argv",
            ["nber-cli", "feed", "fetch", "--display-all", "true", "--max-items", "1", "--format", "json"],
        ):
            main()

        mock_fetch.assert_called_once_with(display_all=True, max_items=1)
        payload = json.loads(capsys.readouterr().out)
        assert payload["total_fetched"] == 1
        assert payload["new_count"] == 0
        assert payload["display_all"] is True
        assert payload["max_items"] == 1
        assert payload["displayed_count"] == 1
        assert payload["results"][0]["id"] == "w35254"

    @patch("nber_cli.cli.fetch_feed")
    def test_feed_fetch_with_max_items_defaults_to_display_all(self, mock_fetch, capsys):
        from nber_cli.core.models import NBERFeedFetchResult

        mock_fetch.return_value = NBERFeedFetchResult(
            source_url="https://www.nber.org/rss/new.xml",
            database_path=Path("/tmp/feed.db"),
            total_fetched=1,
            new_count=0,
            display_all=True,
            max_items=5,
            items=[],
        )

        with patch.object(sys, "argv", ["nber-cli", "feed", "fetch", "--max-items", "5"]):
            main()

        mock_fetch.assert_called_once_with(display_all=True, max_items=5)
        captured = capsys.readouterr()
        assert "Max items: 5" in captured.out

    @patch("nber_cli.cli.fetch_feed")
    def test_feed_fetch_with_max_items_respects_explicit_display_all_false(self, mock_fetch, capsys):
        from nber_cli.core.models import NBERFeedFetchResult

        mock_fetch.return_value = NBERFeedFetchResult(
            source_url="https://www.nber.org/rss/new.xml",
            database_path=Path("/tmp/feed.db"),
            total_fetched=1,
            new_count=0,
            display_all=False,
            max_items=5,
            items=[],
        )

        with patch.object(
            sys,
            "argv",
            ["nber-cli", "feed", "fetch", "--max-items", "5", "--display-all", "false"],
        ):
            main()

        mock_fetch.assert_called_once_with(display_all=False, max_items=5)
        captured = capsys.readouterr()
        assert "Max items: 5" in captured.out


class TestMainEntrypointSearch:
    @patch("nber_cli.cli.search_nber", new_callable=AsyncMock)
    def test_search_outputs_results(self, mock_search, capsys):
        from nber_cli.core.models import NBER, NBERSearchResults

        mock_search.return_value = NBERSearchResults(
            query="inflation",
            total_results=1,
            results=[
                NBER(
                    paper_id=32000,
                    title="Inflation Paper",
                    authors=["Author A"],
                    date="January 2024",
                    abstract="Search abstract.",
                    url="https://www.nber.org/papers/w32000",
                )
            ],
            page=2,
            per_page=50,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        with patch.object(
            sys,
            "argv",
            [
                "nber-cli",
                "search",
                "inflation",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-12-31",
                "--page",
                "2",
                "--per-page",
                "50",
            ],
        ):
            main()

        mock_search.assert_called_once_with(
            "inflation",
            start_date="2024-01-01",
            end_date="2024-12-31",
            page=2,
            per_page=50,
        )
        captured = capsys.readouterr()
        assert "Query: inflation" in captured.out
        assert "Total results: 1" in captured.out
        assert "Inflation Paper" in captured.out
        assert "w32000" in captured.out

    @patch("nber_cli.cli.search_nber", new_callable=AsyncMock)
    def test_search_json_output(self, mock_search, capsys):
        from nber_cli.core.models import NBER, NBERSearchResults

        mock_search.return_value = NBERSearchResults(
            query="inflation",
            total_results=1,
            results=[
                NBER(
                    paper_id=32000,
                    title="Inflation Paper",
                    authors=["Author A"],
                    date="January 2024",
                    abstract="Search abstract.",
                    url="https://www.nber.org/papers/w32000",
                )
            ],
            page=1,
            per_page=20,
        )

        with patch.object(sys, "argv", ["nber-cli", "search", "inflation", "--format", "json"]):
            main()

        payload = json.loads(capsys.readouterr().out)
        assert payload["query"] == "inflation"
        assert payload["total_results"] == 1
        assert payload["results"][0]["id"] == "w32000"

    @patch("nber_cli.cli.search_nber", new_callable=AsyncMock)
    def test_search_validation_error_exits_2(self, mock_search):
        mock_search.side_effect = ValueError("invalid date 'x', expected YYYY-MM-DD")

        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "search", "inflation", "--start-date", "x"]):
                main()

        assert exc_info.value.code == 2


class TestConfigCommand:
    def test_config_show_prints_json(self, capsys):
        with patch.object(sys, "argv", ["nber-cli", "config", "show"]):
            main()
        output = capsys.readouterr().out
        config = json.loads(output)
        assert "info" in config
        assert "download" in config

    def test_config_get_returns_value(self, capsys):
        with patch.object(sys, "argv", ["nber-cli", "config", "get", "download.restrict_dir"]):
            main()
        assert capsys.readouterr().out.strip() == "true"

    def test_config_set_writes_to_file(self, isolated_nber_home, capsys):
        config_path = isolated_nber_home / ".nber-cli" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.object(sys, "argv", ["nber-cli", "config", "set", "download.restrict_dir", "false"]):
            main()

        assert "Set download.restrict_dir = False" in capsys.readouterr().out
        config = json.loads(config_path.read_text())
        assert config["download"]["restrict_dir"] is False

    def test_config_verify_passes(self, capsys):
        with patch.object(sys, "argv", ["nber-cli", "config", "verify"]):
            main()
        assert "Configuration is valid." in capsys.readouterr().out

    def test_config_verify_fails_on_bad_type(self, isolated_nber_home, capsys):
        config_path = isolated_nber_home / ".nber-cli" / "config.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(json.dumps({"info": {"cache_enabled": "bad"}}))

        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "config", "verify"]):
                main()

        assert exc_info.value.code == 1
        assert "expected boolean" in capsys.readouterr().err

    def test_config_verify_fails_on_non_positive_concurrency(
        self, isolated_nber_home, capsys
    ):
        config_path = isolated_nber_home / ".nber-cli" / "config.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(json.dumps({"download": {"concurrency": 0}}))

        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "config", "verify"]):
                main()

        assert exc_info.value.code == 1
        assert "must be greater than or equal to 1" in capsys.readouterr().err

    @pytest.mark.parametrize("raw_config", ["[]", "0", "null", '"text"', "true"])
    def test_config_verify_fails_on_non_object_root(
        self, isolated_nber_home, capsys, raw_config
    ):
        config_path = isolated_nber_home / ".nber-cli" / "config.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(raw_config)

        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "config", "verify"]):
                main()

        assert exc_info.value.code == 1
        assert "expected object" in capsys.readouterr().err

    def test_config_verify_fails_on_null_scalar(self, isolated_nber_home, capsys):
        config_path = isolated_nber_home / ".nber-cli" / "config.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(json.dumps({"schema_version": None}))

        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "config", "verify"]):
                main()

        assert exc_info.value.code == 1
        assert "expected integer" in capsys.readouterr().err

    def test_config_verify_fails_on_malformed_json(self, isolated_nber_home, capsys):
        config_path = isolated_nber_home / ".nber-cli" / "config.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text("{")

        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["nber-cli", "config", "verify"]):
                main()

        assert exc_info.value.code == 1
        assert "JSONDecodeError" in capsys.readouterr().err


class TestDownloadRestrict:
    @patch("nber_cli.cli.download_paper_to_file", new_callable=AsyncMock)
    def test_restrict_false_allows_outside_cwd(self, mock_download, capsys):
        mock_download.return_value = Path("/tmp/w1234.pdf")
        with patch.object(sys, "argv", ["nber-cli", "download", "w1234", "--file", "/tmp/w1234.pdf", "--restrict", "false"]):
            main()
        mock_download.assert_called_once_with("w1234", Path("/tmp/w1234.pdf"), restrict_dir=False)
