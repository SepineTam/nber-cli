#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam (谭淞)
# @Email  : sepinetam@gmail.com
# @File   : db/test_info_cache_flow.py

import sqlite3
from unittest.mock import AsyncMock, patch

import pytest

from nber_cli import config_store, db
from nber_cli.core.models import NBER
from nber_cli.db import get_paper_with_info_cache, get_paper_with_info_cache_result


@pytest.fixture(autouse=True)
def mock_home_for_db(tmp_path):
    with patch("nber_cli.db.db.Path.home", return_value=tmp_path):
        yield



@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "nber.db"
    db.init_database(path)
    return path


def _make_paper(title: str = "Remote Paper") -> NBER:
    return NBER(
        paper_id=1234,
        title=title,
        authors=["Author A"],
        date="2024-01-15",
        abstract="An abstract.",
    )


@pytest.mark.asyncio
class TestGetPaperWithInfoCache:
    async def test_explicit_database_path_is_used_for_desktop_worker(self, tmp_path):
        custom_path = tmp_path / "custom" / "desktop.db"
        db.init_database(custom_path)

        with patch("nber_cli.db.info_cache.get_nber", new_callable=AsyncMock) as mock_get_nber:
            mock_get_nber.return_value = _make_paper()

            result = await get_paper_with_info_cache_result(1234, db_path=custom_path)

        assert result.from_cache is False
        assert db.count_info_cache(custom_path) == 1
        assert not (tmp_path / "nber.db").exists()

    async def test_cache_disabled_fetches_network_and_does_not_write(self, db_path):
        config_store.set_info_cache_enabled(False)

        with patch("nber_cli.db.info_cache.get_nber", new_callable=AsyncMock) as mock_get_nber:
            mock_get_nber.return_value = _make_paper()

            paper = await get_paper_with_info_cache(1234)

        assert paper.title == "Remote Paper"
        mock_get_nber.assert_called_once_with(1234)
        assert db.count_info_cache(db_path) == 0

    async def test_cache_hit_does_not_fetch_network_and_touches_row(self, db_path):
        db.write_info_cache(db_path, _make_paper("Cached Paper"))

        with patch("nber_cli.db.info_cache.get_nber", new_callable=AsyncMock) as mock_get_nber:
            paper = await get_paper_with_info_cache(1234)

        assert paper.title == "Cached Paper"
        mock_get_nber.assert_not_called()
        with sqlite3.connect(db_path) as connection:
            row = connection.execute(
                "SELECT fetch_count, last_fetched_at FROM info_cache WHERE paper_id = 'w1234'"
            ).fetchone()
        assert row[0] == 1
        assert row[1] is not None

    async def test_cache_hit_result_marks_source(self, db_path):
        db.write_info_cache(db_path, _make_paper("Cached Paper"))

        result = await get_paper_with_info_cache_result(1234)

        assert result.paper.title == "Cached Paper"
        assert result.from_cache is True

    async def test_refresh_fetches_network_and_updates_cache_when_enabled(self, db_path):
        db.write_info_cache(db_path, _make_paper("Cached Paper"))

        with patch("nber_cli.db.info_cache.get_nber", new_callable=AsyncMock) as mock_get_nber:
            mock_get_nber.return_value = _make_paper("Fresh Paper")

            result = await get_paper_with_info_cache_result(1234, refresh=True)

        paper = result.paper
        assert paper.title == "Fresh Paper"
        assert result.from_cache is False
        mock_get_nber.assert_called_once_with(1234)
        cached = db.read_info_cache(db_path, 1234)
        assert cached is not None
        assert cached.title == "Fresh Paper"

    async def test_refresh_does_not_write_when_cache_disabled(self, db_path):
        config_store.set_info_cache_enabled(False)

        with patch("nber_cli.db.info_cache.get_nber", new_callable=AsyncMock) as mock_get_nber:
            mock_get_nber.return_value = _make_paper("Fresh Paper")

            await get_paper_with_info_cache(1234, refresh=True)

        mock_get_nber.assert_called_once_with(1234)
        assert db.count_info_cache(db_path) == 0

    async def test_invalid_page_is_not_cached(self, db_path):
        with (
            patch(
                "nber_cli.fetch.fetcher._load_page_sync",
                return_value="<html><head></head><body></body></html>",
            ),
            patch("nber_cli.fetch.fetcher.time.sleep"),
        ):
            with pytest.raises(ValueError, match="missing citation title"):
                await get_paper_with_info_cache(1234)

        assert db.count_info_cache(db_path) == 0

    async def test_mismatched_page_is_not_cached(self, db_path):
        page = """
<meta name="citation_title" content="Another Paper">
<meta name="citation_technical_report_number" content="w5678">
"""
        with patch("nber_cli.fetch.fetcher._load_page_sync", return_value=page):
            with pytest.raises(ValueError, match="does not match"):
                await get_paper_with_info_cache(1234)

        assert db.count_info_cache(db_path) == 0
        assert db.read_info_cache(db_path, 5678) is None
