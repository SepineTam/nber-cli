#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam (谭淞)
# @Email  : sepinetam@gmail.com
# @File   : mcp/mcp.py

import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ..db import db
from ..db.info_cache import get_paper_with_info_cache
from ..fetch.download import download_paper as download_paper_to_dir, download_paper_to_file
from ..fetch.fetcher import search_nber
from ..utils.formatters import info, related, search_results


_PAPER_ID_RE = re.compile(r"^w?\d+$", re.IGNORECASE)


def _parse_paper_id(paper_id_str: str) -> int:
    if not _PAPER_ID_RE.fullmatch(paper_id_str):
        raise ValueError(f"invalid paper ID: {paper_id_str}")
    cleaned = paper_id_str.lower().removeprefix("w")
    return int(cleaned)


async def get_paper_info(paper_id: str, include_all: bool = True) -> dict:
    """Fetch metadata and abstract for an NBER working paper by ID.

    Args:
        paper_id: Paper ID, e.g. 'w1234' or '1234'
        include_all: Whether to include related fields and published version

    Returns:
        Dictionary containing paper metadata.
    """
    nber_id = _parse_paper_id(paper_id)
    try:
        paper = await get_paper_with_info_cache(nber_id)
    except Exception as error:
        return {"error": f"Failed to fetch paper {paper_id}: {error}"}
    db.record_info(None, nber_id)

    result = info(paper)
    if include_all:
        result.update(related(paper))
        if paper.published_version:
            result["published_version"] = paper.published_version

    return result


async def search_papers(
    query: str,
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """Search NBER working papers by keyword with optional date constraints.

    Args:
        query: Title, number, author, abstract, or keyword.
        start_date: Optional earliest working paper date, formatted YYYY-MM-DD.
        end_date: Optional latest working paper date, formatted YYYY-MM-DD.
        page: Result page to fetch.
        per_page: Number of results per page.

    Returns:
        Dictionary containing result metadata and papers.
    """
    try:
        results = await search_nber(
            query,
            start_date=start_date,
            end_date=end_date,
            page=page,
            per_page=per_page,
        )
        return search_results(results)
    except Exception as error:
        return {"error": f"Search failed: {error.__class__.__name__}"}


async def download_paper(paper_id: str, output_path: str | None = None) -> dict:
    """Download an NBER working paper as a PDF.

    Args:
        paper_id: Paper ID, e.g. 'w1234' or '1234'
        output_path: Explicit output file path, must be within the current directory. If not provided, saves as <paper_id>.pdf in current directory.

    Returns:
        Dictionary with "success": True or "error": message.
    """
    try:
        nber_id = _parse_paper_id(paper_id)
        normalized_id = f"w{nber_id}"

        if output_path:
            target = Path(output_path)
            try:
                target.absolute().relative_to(Path.cwd().absolute())
            except ValueError:
                return {"error": "MCP download only allows paths within the current directory"}
            await download_paper_to_file(normalized_id, target, restrict_dir=True)
        else:
            await download_paper_to_dir(normalized_id, Path.cwd(), restrict_dir=True)

        return {"success": True}
    except Exception as error:
        return {"error": f"Download failed: {error.__class__.__name__}"}


def create_mcp_server(*, include_download: bool = True, host: str = "127.0.0.1") -> FastMCP:
    """Create an MCP server with the tools allowed for its transport."""
    server = FastMCP("nber_mcp", host=host)
    server.add_tool(get_paper_info)
    server.add_tool(search_papers)
    if include_download:
        server.add_tool(download_paper)
    return server


nber_mcp = create_mcp_server()
