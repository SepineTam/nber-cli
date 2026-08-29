#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam (谭淞)
# @Email  : sepinetam@gmail.com
# @File   : utils/formatters.py

import textwrap

from ..core.models import NBER, NBERFeedFetchResult, NBERFeedItem, NBERSearchResults

_TEXT_WIDTH = 88


def paper_id_str(paper: NBER) -> str:
    return f"{paper.series}{paper.paper_id:04d}"


def info(paper: NBER) -> dict:
    result = {
        "id": paper_id_str(paper),
        "title": paper.title,
        "authors": paper.authors,
        "date": paper.date,
        "abstract": paper.abstract,
    }
    if paper.url:
        result["url"] = paper.url
    return result


def related(paper: NBER) -> dict[str, str | None]:
    return {
        "topic": paper.topic,
        "programs": paper.programs,
    }


def search_result(paper: NBER) -> dict:
    return {
        "id": paper_id_str(paper),
        "title": paper.title,
        "authors": paper.authors,
        "date": paper.date,
        "abstract": paper.abstract,
        "url": paper.url,
    }


def search_results(search: NBERSearchResults) -> dict:
    return {
        "query": search.query,
        "total_results": search.total_results,
        "page": search.page,
        "per_page": search.per_page,
        "start_date": search.start_date,
        "end_date": search.end_date,
        "results": [search_result(result) for result in search.results],
    }


def feed_item(item: NBERFeedItem) -> dict:
    return {
        "id": item.paper_id,
        "title": item.title,
        "authors": item.authors,
        "abstract": item.abstract,
        "url": item.url,
        "source_url": item.source_url,
        "guid": item.guid,
    }


def feed_results(result: NBERFeedFetchResult) -> dict:
    return {
        "source_url": result.source_url,
        "database_path": str(result.database_path),
        "total_fetched": result.total_fetched,
        "new_count": result.new_count,
        "display_all": result.display_all,
        "max_items": result.max_items,
        "displayed_count": len(result.items),
        "results": [feed_item(item) for item in result.items],
    }


def info_text(paper: NBER, include_all: bool = False) -> str:
    lines = [
        f"{paper_id_str(paper)} | {paper.title}",
        f"Date: {paper.date or 'Unknown'}",
        f"Authors: {_join_authors(paper.authors)}",
    ]
    if paper.url:
        lines.append(f"URL: {paper.url}")
    if include_all:
        if paper.topic:
            lines.append(f"Topic: {paper.topic}")
        if paper.programs:
            lines.append(f"Programs: {paper.programs}")
        if paper.published_version:
            lines.append(f"Published version: {paper.published_version}")
    if paper.abstract:
        lines.extend(["", "Abstract:", _wrap_text(paper.abstract)])
    return "\n".join(lines)


def search_results_text(search: NBERSearchResults) -> str:
    date_range = _format_date_range(search.start_date, search.end_date)
    lines = [
        f"Query: {search.query}",
        f"Total results: {search.total_results:,}",
        f"Page: {search.page} | Per page: {search.per_page}",
        f"Date range: {date_range}",
        "",
    ]

    if not search.results:
        lines.append("No results found.")
        return "\n".join(lines)

    lines.append("Results:")
    lines.extend(_search_result_line(result) for result in search.results)
    return "\n".join(lines)


def feed_results_text(result: NBERFeedFetchResult) -> str:
    lines = [
        f"Feed: {result.source_url}",
        f"Database: {result.database_path}",
        f"Fetched: {result.total_fetched}",
        f"New: {result.new_count}",
        f"Displayed: {len(result.items)}",
    ]
    if result.max_items is not None:
        lines.append(f"Max items: {result.max_items}")
    lines.append("")

    if not result.items:
        if result.display_all:
            lines.append("No feed items found.")
        else:
            lines.append("No new feed items.")
        return "\n".join(lines)

    lines.append("Items:")
    lines.append("")
    lines.append("\n\n".join(_feed_item_text(item) for item in result.items))
    return "\n".join(lines)


def _search_result_line(paper: NBER) -> str:
    parts = [
        paper_id_str(paper),
        paper.date or "Unknown date",
        paper.title,
        _join_authors(paper.authors),
    ]
    if paper.url:
        parts.append(paper.url)
    return " | ".join(parts)


def _feed_item_text(item: NBERFeedItem) -> str:
    lines = [
        f"{item.paper_id} | {item.title}",
        f"Authors: {_join_authors(item.authors)}",
        f"URL: {item.url}",
    ]
    if item.abstract:
        lines.extend(["", "Abstract:", _wrap_text(item.abstract)])
    return "\n".join(lines)


def _format_date_range(start_date: str | None, end_date: str | None) -> str:
    if start_date and end_date:
        return f"{start_date} to {end_date}"
    if start_date:
        return f"{start_date} to any time"
    if end_date:
        return f"any time to {end_date}"
    return "Any time"


def _join_authors(authors: list[str]) -> str:
    return ", ".join(authors) if authors else "Unknown"


def _wrap_text(text: str) -> str:
    return textwrap.fill(text, width=_TEXT_WIDTH)
