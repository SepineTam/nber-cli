#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam (谭淞)
# @Email  : sepinetam@gmail.com
# @File   : mcp/test_mcp.py

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from nber_cli.mcp import (
    _parse_paper_id,
    create_mcp_server,
    download_paper,
    get_paper_info,
    search_papers,
)


class TestMcpServerTools:
    @pytest.mark.asyncio
    async def test_stdio_profile_includes_download(self):
        server = create_mcp_server(include_download=True)

        tools = await server.list_tools()

        assert {tool.name for tool in tools} == {
            "download_paper",
            "get_paper_info",
            "search_papers",
        }

    @pytest.mark.asyncio
    async def test_http_profile_excludes_download(self):
        server = create_mcp_server(include_download=False)

        tools = await server.list_tools()

        assert {tool.name for tool in tools} == {"get_paper_info", "search_papers"}


class TestParsePaperId:
    def test_with_w_prefix(self):
        assert _parse_paper_id("w1234") == 1234

    def test_without_prefix(self):
        assert _parse_paper_id("5678") == 5678

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _parse_paper_id("abc")


class TestGetPaperInfo:
    @pytest.mark.asyncio
    async def test_returns_paper_info(self):
        from nber_cli.core.models import NBER
        mock_paper = NBER(
            paper_id=1234,
            title="Test Title",
            authors=["Author A"],
            date="2024/01/01",
            abstract="Test abstract.",
        )
        with patch("nber_cli.mcp.mcp.get_paper_with_info_cache", new_callable=AsyncMock, return_value=mock_paper):
            with patch("nber_cli.mcp.mcp.db.record_info"):
                result = await get_paper_info("w1234", include_all=False)

        assert result["id"] == "w1234"
        assert result["title"] == "Test Title"
        assert "published_version" not in result

    @pytest.mark.asyncio
    async def test_include_all_adds_related(self):
        from nber_cli.core.models import NBER
        mock_paper = NBER(
            paper_id=1234,
            title="Test Title",
            authors=["Author A"],
            date="2024/01/01",
            abstract="Test abstract.",
            published_version="Published in Journal.",
        )
        with patch("nber_cli.mcp.mcp.get_paper_with_info_cache", new_callable=AsyncMock, return_value=mock_paper):
            with patch("nber_cli.mcp.mcp.db.record_info"):
                result = await get_paper_info("w1234", include_all=True)

        assert result["published_version"] == "Published in Journal."

    @pytest.mark.asyncio
    async def test_fetch_failure_returns_error_dict(self):
        with patch("nber_cli.mcp.mcp.get_paper_with_info_cache", new_callable=AsyncMock, side_effect=ConnectionError("network down")):
            result = await get_paper_info("w1234")

        assert "error" in result
        assert "Failed to fetch paper w1234" in result["error"]


class TestSearchPapers:
    @pytest.mark.asyncio
    async def test_returns_search_results(self):
        from nber_cli.core.models import NBERSearchResults, NBER
        mock_results = NBERSearchResults(
            query="inflation",
            total_results=1,
            results=[
                NBER(
                    paper_id=1234,
                    title="Inflation Paper",
                    authors=["Author A"],
                    date="2024/01/01",
                    abstract="Abstract.",
                )
            ],
            page=1,
            per_page=20,
        )
        with patch("nber_cli.mcp.mcp.search_nber", new_callable=AsyncMock, return_value=mock_results):
            result = await search_papers("inflation")

        assert result["query"] == "inflation"
        assert result["total_results"] == 1


class TestDownloadPaper:
    @pytest.mark.asyncio
    async def test_download_to_default_path(self):
        with patch("nber_cli.mcp.mcp.download_paper_to_dir", new_callable=AsyncMock) as mock_download:
            result = await download_paper("w1234")
            assert result == {"success": True}
            mock_download.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_to_explicit_path(self):
        target = Path.cwd() / "paper.pdf"
        with patch("nber_cli.mcp.mcp.download_paper_to_file", new_callable=AsyncMock) as mock_download:
            result = await download_paper("w1234", output_path=str(target))
            assert result == {"success": True}
            mock_download.assert_called_once_with("w1234", target, restrict_dir=True)

    @pytest.mark.asyncio
    async def test_rejects_path_outside_cwd(self):
        result = await download_paper("w1234", output_path="/tmp/paper.pdf")
        assert "error" in result
        assert "within the current directory" in result["error"]
