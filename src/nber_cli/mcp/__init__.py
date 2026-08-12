#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam (谭淞)
# @Email  : sepinetam@gmail.com
# @File   : mcp/__init__.py

"""MCP server subpackage."""

from __future__ import annotations

from .mcp import (
    _parse_paper_id,
    create_mcp_server,
    download_paper,
    get_paper_info,
    nber_mcp,
    search_papers,
)

__all__ = [
    "_parse_paper_id",
    "create_mcp_server",
    "download_paper",
    "get_paper_info",
    "nber_mcp",
    "search_papers",
]
