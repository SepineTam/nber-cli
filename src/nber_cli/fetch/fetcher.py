#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam (谭淞)
# @Email  : sepinetam@gmail.com
# @File   : fetch/fetcher.py

from __future__ import annotations

import asyncio
import html
import json
import logging
import re
import ssl
import time
from collections.abc import Awaitable, Callable
from datetime import date
from html.parser import HTMLParser
from typing import Any, TypeVar
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from aiohttp import ClientError, ClientResponseError, ClientSession

from ..config import NBER_CLI_CONFIG
from ..core.models import NBER, NBERSearchResults

logger = logging.getLogger(__name__)

T = TypeVar("T")
JsonDict = dict[str, Any]

_NBER_SEARCH_API = "https://www.nber.org/api/v1/working_page_listing/contentType/working_paper/_/_/search"
_NBER_BASE_URL = "https://www.nber.org"
_REQUEST_TIMEOUT_SECONDS = NBER_CLI_CONFIG.request_timeout_seconds
_SUPPORTED_SEARCH_PAGE_SIZES = NBER_CLI_CONFIG.search_page_sizes
_NBER_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "Priority": "u=0, i",
    "Sec-Ch-Ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


class NBERResponseError(RuntimeError):
    """Raised when NBER returns a successful HTTP response with invalid content."""


class InvalidNBERPageError(ValueError):
    """Raised when a response is not a parseable NBER paper page."""


class _CitationMetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        attributes = dict(attrs)
        name = (attributes.get("name") or "").lower()
        content = attributes.get("content") or ""
        if name.startswith("citation_"):
            self.values.setdefault(name, []).append(content)


class _RelatedInfoParser(HTMLParser):
    _SECTIONS = {"Topics", "Programs"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: dict[str, list[str]] = {section: [] for section in self._SECTIONS}
        self._div_depth = 0
        self._item_depth: int | None = None
        self._section: str | None = None
        self._heading_parts: list[str] | None = None
        self._link_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "div":
            self._div_depth += 1
            if self._item_depth is None and "info-grid__item" in classes:
                self._item_depth = self._div_depth
                self._section = None
            return
        if self._item_depth is None:
            return
        if tag == "h3" and "info-grid__item-title" in classes:
            self._heading_parts = []
        elif tag == "a" and self._section in self._SECTIONS:
            self._link_parts = []

    def handle_data(self, data: str) -> None:
        if self._heading_parts is not None:
            self._heading_parts.append(data)
        if self._link_parts is not None:
            self._link_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h3" and self._heading_parts is not None:
            heading = " ".join("".join(self._heading_parts).split())
            self._section = heading if heading in self._SECTIONS else None
            self._heading_parts = None
        elif tag == "a" and self._link_parts is not None:
            value = " ".join("".join(self._link_parts).split())
            if value and self._section is not None:
                self.values[self._section].append(value)
            self._link_parts = None
        elif tag == "div":
            if self._item_depth == self._div_depth:
                self._item_depth = None
                self._section = None
                self._heading_parts = None
                self._link_parts = None
            self._div_depth = max(0, self._div_depth - 1)


async def get_nber(
    nber_id: int,
    session: ClientSession | None = None,
    *,
    series: str = "w",
) -> NBER:
    normalized_series = series.lower()
    if normalized_series not in {"w", "h"}:
        raise ValueError(f"unsupported NBER paper series: {series}")
    _url = f"https://www.nber.org/papers/{normalized_series}{nber_id:04d}"
    if session is not None:
        paper = await _retry_async(
            lambda: _load_and_parse_page(_url, session)
        )
    else:
        paper = await asyncio.to_thread(_load_nber_sync, _url)
    if paper.paper_id != nber_id or paper.series != normalized_series:
        raise ValueError(
            f"requested paper ID {normalized_series}{nber_id:04d} does not match "
            f"response paper ID {paper.series}{paper.paper_id:04d}"
        )
    return paper


async def search_nber(
    query: str,
    *,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    page: int = 1,
    per_page: int = 20,
    session: ClientSession | None = None,
) -> NBERSearchResults:
    params = _build_search_params(
        query=query,
        start_date=start_date,
        end_date=end_date,
        page=page,
        per_page=per_page,
    )
    if session is not None:
        payload = await _load_json_with_retry(_NBER_SEARCH_API, session, params)
    else:
        payload = await asyncio.to_thread(_load_json_sync, _NBER_SEARCH_API, params)
    return _parse_search_payload(payload, params)


async def _load_page(url: str, session: ClientSession) -> str:
    logger.debug("request %s", url)
    async with session.get(url, headers=_NBER_REQUEST_HEADERS) as resp:
        resp.raise_for_status()
        logger.debug("response %s status=%s", url, resp.status)
        return await resp.text()


async def _load_json(url: str, session: ClientSession, params: JsonDict) -> JsonDict:
    logger.debug("request %s params=%s", url, params)
    async with session.get(url, headers=_NBER_REQUEST_HEADERS, params=params) as resp:
        resp.raise_for_status()
        logger.debug("response %s status=%s", url, resp.status)
        return _decode_json_payload(await resp.text())


async def _load_and_parse_page(url: str, session: ClientSession) -> NBER:
    return parse_page(await _load_page(url, session))


async def _load_page_with_retry(url: str, session: ClientSession) -> str:
    return await _retry_async(lambda: _load_page(url, session))


async def _load_json_with_retry(
    url: str, session: ClientSession, params: JsonDict
) -> JsonDict:
    return await _retry_async(lambda: _load_json(url, session, params))


def _load_page_sync(url: str) -> str:
    return _load_text_sync(url)


def _load_json_sync(url: str, params: JsonDict) -> JsonDict:
    query_string = urlencode(params)
    request_url = f"{url}?{query_string}"
    last_error: NBERResponseError | None = None

    for attempt in range(NBER_CLI_CONFIG.request_attempts):
        try:
            return _decode_json_payload(_load_text_sync(request_url))
        except NBERResponseError as error:
            last_error = error
            logger.warning(
                "request %s returned invalid JSON (attempt %s)",
                request_url,
                attempt + 1,
            )
            if attempt >= NBER_CLI_CONFIG.request_retry_count:
                raise
            time.sleep(min(2 ** attempt, 30))

    if last_error is not None:
        raise last_error
    raise RuntimeError("JSON request failed without an error")


def _load_nber_sync(url: str) -> NBER:
    last_error: InvalidNBERPageError | None = None

    for attempt in range(NBER_CLI_CONFIG.request_attempts):
        try:
            return parse_page(_load_page_sync(url))
        except InvalidNBERPageError as error:
            last_error = error
            logger.warning(
                "request %s returned an invalid paper page (attempt %s)",
                url,
                attempt + 1,
            )
            if attempt >= NBER_CLI_CONFIG.request_retry_count:
                raise
            time.sleep(min(2 ** attempt, 30))

    if last_error is not None:
        raise last_error
    raise RuntimeError("paper request failed without an error")


def _decode_json_payload(text: str) -> JsonDict:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise NBERResponseError("NBER search returned a non-JSON response") from error
    if not isinstance(payload, dict):
        raise NBERResponseError("NBER search returned an unexpected JSON structure")
    return payload


def _load_text_sync(url: str) -> str:
    logger.debug("request %s", url)
    request = Request(url, headers=_NBER_REQUEST_HEADERS)
    ssl_context = ssl.create_default_context()
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    last_error: BaseException | None = None

    for attempt in range(NBER_CLI_CONFIG.request_attempts):
        try:
            with urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS, context=ssl_context) as response:
                encoding = response.headers.get_content_charset("utf-8")
                text: str = response.read().decode(encoding)
                logger.debug("response %s status=%s", url, response.status)
                return text
        except HTTPError as error:
            logger.warning("request %s failed: HTTP %s (attempt %s)", url, error.code, attempt + 1)
            if not _should_retry_http_error(error) or attempt >= NBER_CLI_CONFIG.request_retry_count:
                raise
            last_error = error
        except (URLError, TimeoutError, OSError) as error:
            logger.warning("request %s failed: %s (attempt %s)", url, error.__class__.__name__, attempt + 1)
            if attempt >= NBER_CLI_CONFIG.request_retry_count:
                raise
            last_error = error

        time.sleep(min(2 ** attempt, 30))

    if last_error is not None:
        raise last_error

    raise RuntimeError(f"request failed after {NBER_CLI_CONFIG.request_attempts} attempts")


async def _retry_async(loader: Callable[[], Awaitable[T]]) -> T:
    last_error: BaseException | None = None

    for attempt in range(NBER_CLI_CONFIG.request_attempts):
        try:
            return await loader()
        except ClientResponseError as error:
            if not _should_retry_aiohttp_error(error) or attempt >= NBER_CLI_CONFIG.request_retry_count:
                raise
            last_error = error
        except (NBERResponseError, InvalidNBERPageError) as error:
            if attempt >= NBER_CLI_CONFIG.request_retry_count:
                raise
            last_error = error
        except (ClientError, asyncio.TimeoutError, TimeoutError, OSError) as error:
            if attempt >= NBER_CLI_CONFIG.request_retry_count:
                raise
            last_error = error

        await asyncio.sleep(min(2 ** attempt, 30))

    if last_error is not None:
        raise last_error

    raise RuntimeError(f"request failed after {NBER_CLI_CONFIG.request_attempts} attempts")


def parse_page(page: str) -> NBER:
    parser = _CitationMetaParser()
    parser.feed(page)
    citation_values = parser.values

    title_values = citation_values.get("citation_title", [])
    title = title_values[0].strip() if title_values else ""
    if not title:
        raise InvalidNBERPageError("invalid NBER paper page: missing citation title")

    authors = [author.strip() for author in citation_values.get("citation_author", [])]

    date_values = citation_values.get("citation_publication_date", [])
    publication_date = date_values[0].strip() if date_values else ""

    paper_id_values = citation_values.get("citation_technical_report_number", [])
    paper_id_str = paper_id_values[0].strip() if paper_id_values else ""
    normalized_id_match = re.fullmatch(r"([wh]?)0*(\d+)", paper_id_str, re.IGNORECASE)
    if normalized_id_match is None:
        raise InvalidNBERPageError(
            "invalid NBER paper page: missing or invalid citation ID"
        )
    series = normalized_id_match.group(1).lower() or "w"
    paper_id = int(normalized_id_match.group(2))
    if paper_id <= 0:
        raise InvalidNBERPageError(
            "invalid NBER paper page: citation ID must be positive"
        )

    abstract = _extract_abstract(page)
    published_version = _extract_published_version(page)
    topic, programs = _extract_related_info(page)

    return NBER(
        paper_id=paper_id,
        title=title,
        authors=authors,
        date=publication_date,
        abstract=abstract,
        series=series,
        published_version=published_version,
        topic=topic,
        programs=programs,
    )


def _extract_abstract(page: str) -> str:
    intro_match = re.search(
        r'<div class="page-header__intro-inner">\s*<p>(.*?)</p>',
        page,
        re.DOTALL,
    )
    if intro_match:
        return _clean_html_text(intro_match.group(1))
    return ""


def _extract_published_version(page: str) -> str | None:
    pub_match = re.search(
        r'Published Versions</h2>\s*<p>(.*?)</p>',
        page,
        re.DOTALL,
    )
    if pub_match:
        return _clean_html_text(pub_match.group(1))
    return None


def _extract_related_info(page: str) -> tuple[str | None, str | None]:
    parser = _RelatedInfoParser()
    parser.feed(page)
    topic = "; ".join(parser.values["Topics"]) or None
    programs = "; ".join(parser.values["Programs"]) or None
    return topic, programs


def _build_search_params(
    query: str,
    *,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    page: int = 1,
    per_page: int = 20,
    today: date | None = None,
) -> JsonDict:
    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("query must not be empty")
    if page < 1:
        raise ValueError("page must be greater than 0")
    if per_page not in _SUPPORTED_SEARCH_PAGE_SIZES:
        raise ValueError("per_page must be one of 20, 50, or 100")

    start_date_value = _normalize_date(start_date)
    end_date_value = _normalize_date(end_date)
    if start_date_value is not None and end_date_value is None:
        end_date_value = (today or date.today()).isoformat()
    if start_date_value is not None and end_date_value is not None and start_date_value > end_date_value:
        raise ValueError("start_date must be on or before end_date")

    params: JsonDict = {
        "page": page,
        "perPage": per_page,
        "q": cleaned_query,
    }
    if start_date_value is not None:
        params["startDate"] = start_date_value
    if end_date_value is not None:
        params["endDate"] = end_date_value
    return params


def _normalize_date(value: date | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()

    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise ValueError(f"invalid date '{value}', expected YYYY-MM-DD") from error


def _parse_search_payload(
    payload: JsonDict, params: JsonDict
) -> NBERSearchResults:
    raw_results = payload.get("results", [])
    if not isinstance(raw_results, list):
        raw_results = []

    results = [_parse_search_result(result) for result in raw_results]
    return NBERSearchResults(
        query=str(params["q"]),
        total_results=int(payload.get("totalResults", 0) or 0),
        results=results,
        page=int(params["page"]),
        per_page=int(params["perPage"]),
        start_date=params.get("startDate"),
        end_date=params.get("endDate"),
    )


def _parse_search_result(raw_result: JsonDict) -> NBER:
    url = str(raw_result.get("url") or "")
    paper_id_match = re.search(r"/papers/([wh])(\d+)", url, re.IGNORECASE)
    series = paper_id_match.group(1).lower() if paper_id_match else "w"
    paper_id = int(paper_id_match.group(2)) if paper_id_match else 0
    full_url = f"{_NBER_BASE_URL}{url}" if url.startswith("/") else url
    authors_raw = raw_result.get("authors", []) or []
    authors = [_clean_html_text(author) for author in authors_raw]

    return NBER(
        paper_id=paper_id,
        title=_clean_html_text(raw_result.get("title")),
        authors=[author for author in authors if author],
        date=_clean_html_text(raw_result.get("displaydate")),
        abstract=_clean_html_text(raw_result.get("abstract")),
        series=series,
        url=full_url,
    )


def _clean_html_text(value: Any) -> str:
    if value is None:
        return ""
    text = re.sub(r"<[^>]+>", "", str(value))
    return " ".join(html.unescape(text).split())


def _should_retry_http_error(error: HTTPError) -> bool:
    return 500 <= error.code < 600 or error.code in {408, 429}


def _should_retry_aiohttp_error(error: ClientResponseError) -> bool:
    return 500 <= error.status < 600 or error.status in {408, 429}
