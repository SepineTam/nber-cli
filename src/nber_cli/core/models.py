#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam (谭淞)
# @Email  : sepinetam@gmail.com
# @File   : models.py

from dataclasses import dataclass
from pathlib import Path


def _validate_clear_counts(database_path: Path, matched_count: int, deleted_count: int) -> None:
    if not isinstance(database_path, Path):
        raise TypeError("database_path must be a Path instance")
    if not isinstance(matched_count, int) or matched_count < 0:
        raise ValueError("matched_count must be a non-negative integer")
    if not isinstance(deleted_count, int) or deleted_count < 0 or deleted_count > matched_count:
        raise ValueError("deleted_count must be a non-negative integer not exceeding matched_count")


@dataclass
class NBER:
    paper_id: int
    title: str
    authors: list[str]
    date: str
    abstract: str

    url: str | None = None
    published_version: str | None = None
    topic: str | None = None
    programs: str | None = None
    series: str = "w"

    def __post_init__(self) -> None:
        if not isinstance(self.paper_id, int) or self.paper_id < 0:
            raise ValueError(f"paper_id must be a non-negative integer, got {self.paper_id}")
        if not isinstance(self.title, str):
            raise TypeError(f"title must be a string, got {type(self.title).__name__}")
        if not isinstance(self.authors, list) or not all(isinstance(author, str) for author in self.authors):
            raise TypeError("authors must be a list of strings")
        if not isinstance(self.date, str):
            raise TypeError(f"date must be a string, got {type(self.date).__name__}")
        if not isinstance(self.abstract, str):
            raise TypeError(f"abstract must be a string, got {type(self.abstract).__name__}")
        if self.series not in {"w", "h"}:
            raise ValueError(f"series must be 'w' or 'h', got {self.series!r}")


@dataclass
class NBERSearchResults:
    query: str
    total_results: int
    results: list[NBER]
    page: int
    per_page: int
    start_date: str | None = None
    end_date: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.query, str):
            raise TypeError(f"query must be a string, got {type(self.query).__name__}")
        if not isinstance(self.total_results, int) or self.total_results < 0:
            raise ValueError(f"total_results must be a non-negative integer, got {self.total_results}")
        if not isinstance(self.page, int) or self.page <= 0:
            raise ValueError(f"page must be a positive integer, got {self.page}")
        if self.per_page not in {20, 50, 100}:
            raise ValueError(f"per_page must be one of 20, 50, 100, got {self.per_page}")
        if not isinstance(self.results, list) or not all(isinstance(result, NBER) for result in self.results):
            raise TypeError("results must be a list of NBER instances")


@dataclass
class NBERFeedItem:
    paper_id: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    source_url: str
    guid: str

    def __post_init__(self) -> None:
        string_fields = {
            "paper_id": self.paper_id,
            "title": self.title,
            "url": self.url,
            "source_url": self.source_url,
            "guid": self.guid,
        }
        for name, value in string_fields.items():
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.authors, list) or not all(isinstance(author, str) for author in self.authors):
            raise TypeError("authors must be a list of strings")
        if not isinstance(self.abstract, str):
            raise TypeError(f"abstract must be a string, got {type(self.abstract).__name__}")


@dataclass
class NBERFeedFetchResult:
    source_url: str
    database_path: Path
    total_fetched: int
    new_count: int
    display_all: bool
    items: list[NBERFeedItem]
    max_items: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_url, str) or not self.source_url:
            raise ValueError("source_url must be a non-empty string")
        if not isinstance(self.database_path, Path):
            raise TypeError("database_path must be a Path instance")
        if not isinstance(self.total_fetched, int) or self.total_fetched < 0:
            raise ValueError("total_fetched must be a non-negative integer")
        if not isinstance(self.new_count, int) or self.new_count < 0 or self.new_count > self.total_fetched:
            raise ValueError("new_count must be a non-negative integer not exceeding total_fetched")
        if not isinstance(self.display_all, bool):
            raise TypeError("display_all must be a boolean")
        if not isinstance(self.items, list) or not all(isinstance(item, NBERFeedItem) for item in self.items):
            raise TypeError("items must be a list of NBERFeedItem instances")
        if self.max_items is not None and (not isinstance(self.max_items, int) or self.max_items < 0):
            raise ValueError("max_items must be a non-negative integer or None")


@dataclass
class NBERFeedCleanResult:
    database_path: Path
    matched_count: int
    deleted_count: int
    mode: str
    days: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    dry_run: bool = False

    def __post_init__(self) -> None:
        _validate_clear_counts(self.database_path, self.matched_count, self.deleted_count)
        if self.mode not in {"days", "date-range", "all"}:
            raise ValueError(f"mode must be one of days, date-range, all, got {self.mode}")
        if self.days is not None and (not isinstance(self.days, int) or self.days <= 0):
            raise ValueError("days must be a positive integer or None")


@dataclass
class NBERInfoCacheClearResult:
    database_path: Path
    matched_count: int
    deleted_count: int
    mode: str
    days: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    dry_run: bool = False

    def __post_init__(self) -> None:
        _validate_clear_counts(self.database_path, self.matched_count, self.deleted_count)
        if self.mode not in {"days", "date-range", "all"}:
            raise ValueError(f"mode must be one of days, date-range, all, got {self.mode}")
        if self.days is not None and (not isinstance(self.days, int) or self.days <= 0):
            raise ValueError("days must be a positive integer or None")


@dataclass
class DownloadFailure:
    paper_id: str
    error: BaseException

    def __post_init__(self) -> None:
        if not isinstance(self.paper_id, str) or not self.paper_id:
            raise ValueError("paper_id must be a non-empty string")
        if not isinstance(self.error, BaseException):
            raise TypeError("error must be a BaseException instance")


@dataclass
class DownloadBatchResult:
    paths: list[Path]
    failures: list[DownloadFailure]

    def __post_init__(self) -> None:
        if not isinstance(self.paths, list) or not all(isinstance(path, Path) for path in self.paths):
            raise TypeError("paths must be a list of Path instances")
        if not isinstance(self.failures, list) or not all(isinstance(failure, DownloadFailure) for failure in self.failures):
            raise TypeError("failures must be a list of DownloadFailure instances")
