#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam (谭淞)
# @Email  : sepinetam@gmail.com
# @File   : utils/test_logs.py

import json
import sqlite3
from unittest.mock import patch

import pytest

from nber_cli import db


@pytest.fixture(autouse=True)
def mock_home_for_db(tmp_path):
    with patch("nber_cli.db.db.Path.home", return_value=tmp_path):
        yield



@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "nber.db"
    db.init_database(path)
    return path


def _fetch_all(db_path, table, order_by="id"):
    with sqlite3.connect(db_path) as connection:
        return connection.execute(
            f"SELECT * FROM {table} ORDER BY {order_by}"
        ).fetchall()


class TestRecordQuery:
    def test_inserts_row(self, db_path):
        db.record_query(
            db_path,
            keyword="labor",
            conditions={"start_date": "2024-01-01", "end_date": "2024-12-31", "page": 1, "per_page": 20},
            result_count=42,
        )

        rows = _fetch_all(db_path, "query_log")
        assert len(rows) == 1
        assert rows[0][2] == "labor"
        conditions = json.loads(rows[0][3])
        assert conditions["start_date"] == "2024-01-01"
        assert rows[0][4] == 42

    def test_unicode_keyword_preserved(self, db_path):
        db.record_query(db_path, keyword="劳动经济", conditions={}, result_count=0)

        rows = _fetch_all(db_path, "query_log")
        assert rows[0][2] == "劳动经济"

    def test_auto_initializes_schema_when_db_missing(self, tmp_path):
        path = tmp_path / "nber.db"
        db.record_query(path, keyword="x", conditions={}, result_count=0)

        assert path.exists()


class TestRecordDownload:
    def test_records_success(self, db_path):
        db.record_download(db_path, "w1234", "success", saved_path="/tmp/w1234.pdf")

        rows = _fetch_all(db_path, "download_log")
        assert len(rows) == 1
        assert rows[0][2] == "w1234"
        assert rows[0][3] == "success"
        assert rows[0][4] == "/tmp/w1234.pdf"
        assert rows[0][5] is None

    def test_records_failure(self, db_path):
        db.record_download(db_path, "w5678", "failed", error="HTTP 404")

        rows = _fetch_all(db_path, "download_log")
        assert rows[0][3] == "failed"
        assert rows[0][5] == "HTTP 404"
        assert rows[0][4] is None


class TestRecordInfo:
    def test_normalizes_paper_id_to_w_prefix(self, db_path):
        db.record_info(db_path, "1234")
        db.record_info(db_path, "w5678")

        rows = _fetch_all(db_path, "info_log", order_by="paper_id")
        assert rows[0][2] == "w1234"
        assert rows[1][2] == "w5678"

    def test_records_multiple_lookups(self, db_path):
        db.record_info(db_path, "w1234")
        db.record_info(db_path, "w1234")
        db.record_info(db_path, "w1234")

        rows = _fetch_all(db_path, "info_log")
        assert len(rows) == 3

    def test_preserves_historical_series_prefix(self, db_path):
        db.record_info(db_path, "h0065")

        rows = _fetch_all(db_path, "info_log")
        assert rows[0][2] == "h0065"


class TestFailureHandling:
    def test_record_query_swallows_errors(self, capsys, tmp_path):
        blocker = tmp_path / "blocker"
        blocker.write_text("not a directory")
        bad_path = blocker / "nber.db"

        with patch("nber_cli.db.db.get_database_path", return_value=bad_path):
            db.record_query(bad_path, keyword="x", conditions={}, result_count=0)

        captured = capsys.readouterr()
        assert "warning" in captured.err

    def test_record_download_swallows_errors(self, capsys, tmp_path):
        blocker = tmp_path / "blocker"
        blocker.write_text("not a directory")
        bad_path = blocker / "nber.db"

        with patch("nber_cli.db.db.get_database_path", return_value=bad_path):
            db.record_download(bad_path, "w1", "success")

        captured = capsys.readouterr()
        assert "warning" in captured.err

    @pytest.mark.parametrize(
        "operation",
        [
            lambda path: db.record_query(path, "x", {}, 0),
            lambda path: db.record_download(path, "w1", "success"),
            lambda path: db.record_info(path, "w1"),
        ],
    )
    def test_record_operations_warn_and_do_not_write_future_schema(
        self, db_path, capsys, operation
    ):
        with sqlite3.connect(db_path) as connection:
            connection.execute("PRAGMA user_version = 999")

        operation(db_path)

        assert "warning" in capsys.readouterr().err
        with sqlite3.connect(db_path) as connection:
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 999
            counts = [
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("query_log", "download_log", "info_log")
            ]
        assert counts == [0, 0, 0]
